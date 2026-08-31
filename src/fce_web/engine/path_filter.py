"""Per-event and per-cache filtering, and the observable/cache proxies they use.

Vendored from the reference repo's ``engine/path_filter.py`` (kskovpen/fce), 643 lines,
with one deliberate deviation (task B-007): the reference polls a module-level global
flag ("stop") at two call sites to let a student cancel a long-running analysis.
``.claude/shared/CLAUDE.md`` §6 forbids module-level mutable state, and a global flag
would also mean two concurrent students' runs could cancel each other. Both sites now
take an explicit ``cancel: Optional[threading.Event]`` parameter instead:

- :func:`fill_histogram_from_cache` polls it once per ``max(1, n // 100)`` events inside
  its **per-event fallback** loop (the reference's line 406) and returns early, leaving
  the histogram partially filled. The **vectorized fast path has no cancellation poll at
  all** (faithful to the reference's own vectorized path, which has none either), so for
  an observable that vectorizes, this function is effectively uncancellable -- it returns
  once the single numpy call finishes, which is milliseconds. The effective cancellation
  granularity this module offers is therefore **one basket in** :func:`filter_raw_event_data`,
  not one event -- B-009's ``RunContext`` and B-011's headless driver should reason about
  cancellation at that grain, not assume per-event responsiveness.
- :func:`filter_raw_event_data` checks it once as an entry guard before processing its
  basket (the reference's line 453) and returns ``([], [], True)`` unfilled.

``cancel=None`` (the default) means "never cancel" -- unchanged behaviour for a caller
that does not care about cancellation. This is the seam B-009's ``RunContext`` and B-011's
headless driver plug into; neither is built by this task.

**B-008: every student-typed expression in this file now routes through
``fce_web.safe_eval``.** The reference's pattern of running a student expression through the
builtin functions named "eval" and "compile" with a merely restricted ``__builtins__`` does
not stop attribute-traversal escapes (see ``.claude/backend/CLAUDE.md`` §3.2) and is remote
code execution on a shared classroom host. Every selection and observable in this module is
now validated once by ``fce_web.safe_eval.compile_expr`` -- outside any per-event or per-basket
try/except, so a rejected expression's ``fce_web.safe_eval.UnsafeExpression`` is never
swallowed by this module's ``except Exception`` handlers -- and evaluated with
``fce_web.safe_eval.evaluate`` against the same compiled code object for both the vectorized
fast path and the per-event fallback. This file contains no direct call of either builtin by
name anymore; ``tests/test_path_filter.py::test_docstring_eval_compile_line_numbers_match_this_file``
is retired by this change -- see B-008's PR for why its exact regex format cannot survive a
file with zero such calls.

**Not done here, on purpose:**

- ``sumw2`` (``bh.storage.Weight()``) is deliberately absent. ``bh.Histogram(ax)`` keeps
  the reference's default ``Double()`` storage everywhere in this file, per the user's
  ruling that ``weightsSquared`` stays contract-nullable in ``docs/api.md``.
- ``engine/analytical_loop.py:290`` still builds a code object from a student-typed
  selection expression using the same two builtins by name, outside this file's scope --
  reported to the orchestrator in B-008's PR rather than edited here.
"""
import math
import re
import threading
from typing import List, Optional, Tuple

import numpy as np
import vector

# Kept as an attribute lookup on the module (``systematics.SYST_SOURCES``, not a
# ``from ... import SYST_SOURCES`` bound name) deliberately: this is what lets tests
# monkeypatch ``fce_web.engine.systematics.SYST_SOURCES`` and have the per-event and
# vectorized loops below actually pick up the change, proving the ``h_{src}_up`` keys
# are driven by that module rather than a literal list here.
from fce_web.engine import systematics
from fce_web.safe_eval import CompiledExpr, compile_expr, evaluate as safe_evaluate


def preprocess_hep_expr(expr: str) -> str:
    """Translate HEP-style boolean operators to Python syntax."""
    expr = re.sub(r'&&', ' and ', expr)
    expr = re.sub(r'\|\|', ' or ', expr)
    # Replace ! only when not followed by = (to preserve !=)
    expr = re.sub(r'!(?!=)', 'not ', expr)
    return expr


def _compile_all(exprs) -> List[CompiledExpr]:
    """Validate and compile every non-empty expression in *exprs*, eagerly.

    Every caller of this helper calls it before touching a single event or a single array
    index -- see each call site's comment. A rejected expression's ``UnsafeExpression``
    therefore always escapes to the caller of the public function it was called from: it is
    raised here, outside every ``try/except Exception`` block in this module, so none of
    them can catch it.
    """
    return [compile_expr(e) for e in exprs if e]


class _P:
    """Physics object supporting attribute access; unset attr → -999."""
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, _):
        return -999.0


def _delta_r(a, b):
    deta = a.eta - b.eta
    dphi = a.phi - b.phi
    while dphi > math.pi:
        dphi -= 2 * math.pi
    while dphi < -math.pi:
        dphi += 2 * math.pi
    return math.sqrt(deta * deta + dphi * dphi)


# ---------------------------------------------------------------------------
# Vectorized proxies — evaluate an observable against all cached events at once
# ---------------------------------------------------------------------------

class _P4Proxy:
    """Numpy-backed 4-vector supporting vectorized arithmetic and .mass/.pt/.eta/.phi."""

    def __init__(self, e, px, py, pz):
        self._e = e
        self._px = px
        self._py = py
        self._pz = pz

    def __add__(self, other):
        return _P4Proxy(self._e + other._e, self._px + other._px,
                        self._py + other._py, self._pz + other._pz)

    @property
    def mass(self):
        m2 = self._e**2 - self._px**2 - self._py**2 - self._pz**2
        return np.sqrt(np.maximum(m2, 0.0))

    @property
    def pt(self):
        return np.sqrt(self._px**2 + self._py**2)

    @property
    def phi(self):
        return np.arctan2(self._py, self._px)

    @property
    def eta(self):
        p  = np.sqrt(self._px**2 + self._py**2 + self._pz**2)
        ct = np.where(p > 1e-10, self._pz / p, 0.0)
        ct = np.clip(ct, -1.0 + 1e-10, 1.0 - 1e-10)
        return -0.5 * np.log((1.0 - ct) / (1.0 + ct))

    def deltaR(self, other):
        deta = self.eta - other.eta
        dphi = np.arctan2(np.sin(self.phi - other.phi), np.cos(self.phi - other.phi))
        return np.sqrt(deta**2 + dphi**2)


class _ArrayProxy:
    """Physics object backed by numpy arrays — one entry per cached event."""

    def __init__(self, prefix, data):
        self.__dict__.update({"_prefix": prefix, "_data": data, "_p4": None})

    def __getattr__(self, name):
        key = f"{self._prefix}_{name}"
        if key in self._data:
            return self._data[key].astype(np.float64)
        return np.full(len(self._data["weight"]), -999.0, dtype=np.float64)

    @property
    def p4(self):
        if self._p4 is None:
            d, pfx = self._data, self._prefix
            pt  = d[f"{pfx}_pt"].astype(np.float64)
            eta = d[f"{pfx}_eta"].astype(np.float64)
            phi = d[f"{pfx}_phi"].astype(np.float64)
            e   = d[f"{pfx}_e"].astype(np.float64)
            self.__dict__["_p4"] = _P4Proxy(
                e, pt * np.cos(phi), pt * np.sin(phi), pt * np.sinh(eta)
            )
        return self._p4


def _delta_r_vec(a, b):
    deta = a.eta - b.eta
    dphi = np.arctan2(np.sin(a.phi - b.phi), np.cos(a.phi - b.phi))
    return np.sqrt(deta**2 + dphi**2)


def _mT(a, b):
    """Transverse mass: sqrt(2 * a.pt * b.pt * (1 - cos(dphi)))."""
    dphi = a.phi - b.phi
    while dphi > math.pi:
        dphi -= 2 * math.pi
    while dphi < -math.pi:
        dphi += 2 * math.pi
    return math.sqrt(max(0.0, 2 * a.pt * b.pt * (1.0 - math.cos(dphi))))


def _mT_vec(a, b):
    """Vectorized transverse mass for numpy-backed proxies."""
    dphi = np.arctan2(np.sin(a.phi - b.phi), np.cos(a.phi - b.phi))
    return np.sqrt(np.maximum(0.0, 2 * a.pt * b.pt * (1.0 - np.cos(dphi))))


def _make_lepton(lep: dict) -> _P:
    p4 = vector.obj(pt=lep["pt"], eta=lep["eta"], phi=lep["phi"], e=lep["e"])
    return _P(pt=lep["pt"], eta=lep["eta"], phi=lep["phi"], e=lep["e"],
              d0=lep.get("d0", 0.0), z0=lep.get("z0", 0.0),
              charge=lep.get("charge", 0.0), flavour=lep.get("flavour", 0.0), p4=p4)


def _make_jet(j: dict) -> _P:
    p4 = vector.obj(pt=j["pt"], eta=j["eta"], phi=j["phi"], e=j["e"])
    return _P(pt=j["pt"], eta=j["eta"], phi=j["phi"], e=j["e"], btag=j["btag"], p4=p4)


def _make_photon(ph: dict) -> _P:
    p4 = vector.obj(pt=ph["pt"], eta=ph["eta"], phi=ph["phi"], e=ph["e"])
    return _P(pt=ph["pt"], eta=ph["eta"], phi=ph["phi"], e=ph["e"], p4=p4)


def _make_met(pt, phi) -> _P:
    """Build a MET proxy with only physically defined attributes (pt, phi)."""
    return _P(pt=pt, phi=phi)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

_CACHE_KEYS = [
    "nlep", "nel", "nmu", "njets", "nphot", "nbjets", "weight",
    "l1_pt", "l1_eta", "l1_phi", "l1_e", "l1_d0", "l1_z0", "l1_charge", "l1_flavour",
    "l2_pt", "l2_eta", "l2_phi", "l2_e", "l2_d0", "l2_z0", "l2_charge", "l2_flavour",
    "j1_pt", "j1_eta", "j1_phi", "j1_e", "j1_btag",
    "j2_pt", "j2_eta", "j2_phi", "j2_e", "j2_btag",
    "ph1_pt", "ph1_eta", "ph1_phi", "ph1_e",
    "ph2_pt", "ph2_eta", "ph2_phi", "ph2_e",
    "met_pt", "met_phi",
]

_INIT_CAP = 4096


def make_cache_acc() -> dict:
    # OPT-4: pre-allocated numpy arrays with exponential growth instead of Python lists.
    # Eliminates ~1 GB of CPython float-object overhead per million passing events.
    return {"_n": 0, "_cap": _INIT_CAP,
            **{k: np.empty(_INIT_CAP, dtype=np.float32) for k in _CACHE_KEYS}}


def _grow_acc(acc: dict):
    old_cap = acc["_cap"]
    new_cap = old_cap * 2
    for k in _CACHE_KEYS:
        new_arr = np.empty(new_cap, dtype=np.float32)
        new_arr[:old_cap] = acc[k]
        acc[k] = new_arr
    acc["_cap"] = new_cap


def _append_event(acc, nlep, nel, nmu, njets, nphot, nbjets,
                  l1, l2, j1, j2, ph1, ph2, met, w):
    i = acc["_n"]
    if i == acc["_cap"]:
        _grow_acc(acc)
    acc["nlep"][i] = nlep
    acc["nel"][i] = nel
    acc["nmu"][i] = nmu
    acc["njets"][i] = njets
    acc["nphot"][i] = nphot
    acc["nbjets"][i] = nbjets
    acc["weight"][i] = w
    acc["l1_pt"][i] = l1.pt
    acc["l1_eta"][i] = l1.eta
    acc["l1_phi"][i] = l1.phi
    acc["l1_e"][i] = l1.e
    acc["l1_d0"][i] = l1.d0
    acc["l1_z0"][i] = l1.z0
    acc["l1_charge"][i] = l1.charge
    acc["l1_flavour"][i] = l1.flavour
    acc["l2_pt"][i] = l2.pt
    acc["l2_eta"][i] = l2.eta
    acc["l2_phi"][i] = l2.phi
    acc["l2_e"][i] = l2.e
    acc["l2_d0"][i] = l2.d0
    acc["l2_z0"][i] = l2.z0
    acc["l2_charge"][i] = l2.charge
    acc["l2_flavour"][i] = l2.flavour
    acc["j1_pt"][i] = j1.pt
    acc["j1_eta"][i] = j1.eta
    acc["j1_phi"][i] = j1.phi
    acc["j1_e"][i] = j1.e
    acc["j1_btag"][i] = j1.btag
    acc["j2_pt"][i] = j2.pt
    acc["j2_eta"][i] = j2.eta
    acc["j2_phi"][i] = j2.phi
    acc["j2_e"][i] = j2.e
    acc["j2_btag"][i] = j2.btag
    acc["ph1_pt"][i] = ph1.pt
    acc["ph1_eta"][i] = ph1.eta
    acc["ph1_phi"][i] = ph1.phi
    acc["ph1_e"][i] = ph1.e
    acc["ph2_pt"][i] = ph2.pt
    acc["ph2_eta"][i] = ph2.eta
    acc["ph2_phi"][i] = ph2.phi
    acc["ph2_e"][i] = ph2.e
    acc["met_pt"][i] = met.pt
    acc["met_phi"][i] = met.phi
    acc["_n"] = i + 1


def save_cache(cache_file: str, acc: dict):
    n = acc["_n"]
    np.savez_compressed(cache_file, **{k: acc[k][:n] for k in _CACHE_KEYS})


def filter_selection_cache(parent_cache_path: str, additional_exprs: list,
                           output_cache_path: str, compiled_exprs=None):
    """Build a child selection cache by applying additional expressions to a parent cache.

    Used when the parent prefix cache already exists on disk (e.g. sel_[hash_A]_s.npz)
    so we only need to apply the new expression rather than re-reading the ROOT file.

    ``compiled_exprs`` is accepted only for call-signature compatibility and is otherwise
    ignored: a caller-supplied compiled object is never trusted as evidence that its source
    was validated (``fce_web.safe_eval.CompiledExpr``'s own docstring explains why -- it can
    be forged by code already running in this process). Every expression in
    ``additional_exprs`` is (re)validated and compiled by this function, through
    ``fce_web.safe_eval.compile_expr``, before ``parent_cache_path`` is opened -- an unsafe
    expression is rejected without reading a single byte of the cache.

    Unexercised by any caller in the reference repo (kskovpen/fce) as of the commit this
    was vendored from, and by anything in this repo as of task B-007 -- vendored anyway
    because it is part of the module's public surface, but no production code path reaches
    it yet.
    """
    compiled = _compile_all(additional_exprs)

    data = np.load(parent_cache_path, mmap_mode='r')
    n = len(data["weight"])

    # ── Vectorized fast path ─────────────────────────────────────────────────
    # Evaluate the additional expression as a numpy boolean mask over all events.
    # numpy operations release the Python GIL, enabling true parallel execution
    # when multiple workers call this function on different samples simultaneously.
    # Produces the same output as the per-event fallback but orders of magnitude faster.
    try:
        nphot_arr = data["nphot"] if "nphot" in data else np.zeros(n, dtype=np.float32)
        vec_vars = {
            "nlep": data["nlep"], "nel": data["nel"],
            "nmu":  data["nmu"],  "njets": data["njets"],
            "nphot": nphot_arr,
            "l1": _ArrayProxy("l1", data), "l2": _ArrayProxy("l2", data),
            "j1": _ArrayProxy("j1", data), "j2": _ArrayProxy("j2", data),
            "ph1": _ArrayProxy("ph1", data), "ph2": _ArrayProxy("ph2", data),
            "met": _ArrayProxy("met", data),
            "deltaR": _delta_r_vec, "mT": _mT_vec,
        }
        mask = np.ones(n, dtype=bool)
        for ce in compiled:
            result = safe_evaluate(ce, vec_vars)
            result = np.asarray(result, dtype=bool).ravel()
            if result.shape[0] != n:
                raise ValueError("shape mismatch")
            mask &= result
        # Save filtered arrays directly — same format as save_cache (float32 npz).
        np.savez_compressed(output_cache_path,
                            **{k: data[k][mask] for k in data.files})
        return
    except Exception:
        pass

    # ── Per-event fallback (handles 4-vector expressions the vectorized path can't) ─
    acc = make_cache_acc()
    _NULL = _P()

    for i in range(n):
        try:
            l1  = _obj_from_cache(data, i, "l1",  ["eta", "phi", "e", "d0", "z0", "charge", "flavour"])
            l2  = _obj_from_cache(data, i, "l2",  ["eta", "phi", "e", "d0", "z0", "charge", "flavour"])
            j1  = _obj_from_cache(data, i, "j1",  ["eta", "phi", "e", "btag"])
            j2  = _obj_from_cache(data, i, "j2",  ["eta", "phi", "e", "btag"])
            ph1 = (_obj_from_cache(data, i, "ph1", ["eta", "phi", "e"])
                   if "ph1_pt" in data else _NULL)
            ph2 = (_obj_from_cache(data, i, "ph2", ["eta", "phi", "e"])
                   if "ph2_pt" in data else _NULL)
            met = _make_met(float(data["met_pt"][i]),
                            float(data["met_phi"][i]) if "met_phi" in data else 0.0)
            local_vars = {
                "nlep": int(data["nlep"][i]), "nel": int(data["nel"][i]),
                "nmu":  int(data["nmu"][i]),  "njets": int(data["njets"][i]),
                "nphot": int(data["nphot"][i]) if "nphot" in data else 0,
                "l1": l1, "l2": l2, "j1": j1, "j2": j2,
                "ph1": ph1, "ph2": ph2, "met": met,
                "deltaR": _delta_r, "mT": _mT,
            }
            skip = False
            for ce in compiled:
                try:
                    if not safe_evaluate(ce, local_vars):
                        skip = True
                        break
                except Exception:
                    skip = True
                    break
            if skip:
                continue
            nel  = int(data["nel"][i])
            nmu  = int(data["nmu"][i])
            _nbjets = int(data["nbjets"][i]) if "nbjets" in data else 0
            _append_event(acc,
                          nel + nmu, nel, nmu,
                          int(data["njets"][i]),
                          int(data["nphot"][i]) if "nphot" in data else 0,
                          _nbjets,
                          l1, l2, j1, j2, ph1, ph2, met, float(data["weight"][i]))
        except Exception:
            continue

    save_cache(output_cache_path, acc)


def _obj_from_cache(data, i, prefix, keys, extra=None) -> _P:
    """Reconstruct a _P physics object from a loaded .npz cache."""
    pt = float(data[f"{prefix}_pt"][i])
    if pt <= -900:
        return _P()
    kw = {}
    for k in keys:
        cache_key = f"{prefix}_{k}"
        kw[k] = float(data[cache_key][i]) if cache_key in data else -999.0
    kw["pt"] = pt
    try:
        kw["p4"] = vector.obj(pt=pt, eta=kw["eta"], phi=kw["phi"], e=kw["e"])
    except Exception:
        pass
    return _P(**kw)


def fill_histogram_from_cache(cache_file: str, outHist, observable_target: str,
                              with_syst: bool = True,
                              cancel: Optional[threading.Event] = None):
    """Load a selection-level cache and fill the histogram with a fresh observable eval.

    When with_syst is True (all non-data samples), also fills per-source UP variation
    histograms keyed as h_{src}_up (src in SYST_SOURCES) using per-event weight factors.

    ``cancel``, if given, is polled once per ``max(1, n // 100)`` events in the per-event
    fallback loop (mirroring the reference's poll of its global stop flag at that
    same call site); when it is set the function returns immediately, leaving the histogram
    partially filled. ``cancel=None`` means the loop always runs to completion.

    ``observable_target`` is validated and compiled exactly once, through
    ``fce_web.safe_eval.compile_expr``, before ``cache_file`` is opened -- an unsafe
    expression is rejected without reading a single byte of the cache. The same compiled
    code object is then reused, via ``fce_web.safe_eval.evaluate``, by both the vectorized
    fast path and the per-event fallback below.
    """
    # Local import: keeps module import-time deps minimal (boost_histogram is only
    # needed here, not for the proxy/eval/cache-I/O paths exercised by unit tests).
    import boost_histogram as bh

    compiled_obs = compile_expr(observable_target)

    # OPT-1: mmap_mode='r' lets the OS page in only accessed columns; unaccessed arrays
    # are never faulted into RAM (particularly useful in the vectorized path below).
    data = np.load(cache_file, mmap_mode='r')
    n = len(data["weight"])
    weights = data["weight"].astype(np.float64)

    # Backward-compat: nbjets may be absent in caches built before this column was added.
    nbjets_arr = data["nbjets"] if "nbjets" in data else np.zeros(n, dtype=np.float32)

    # ── Vectorized fast path: evaluate observable over all events at once ──
    try:
        vec_vars = {
            "nlep": data["nlep"], "nel": data["nel"],
            "nmu":  data["nmu"],  "njets": data["njets"],
            "nphot": data["nphot"] if "nphot" in data else np.zeros(n, dtype=np.float32),
            "l1": _ArrayProxy("l1", data), "l2": _ArrayProxy("l2", data),
            "j1": _ArrayProxy("j1", data), "j2": _ArrayProxy("j2", data),
            "ph1": _ArrayProxy("ph1", data), "ph2": _ArrayProxy("ph2", data),
            "met": _ArrayProxy("met", data),
            "deltaR": _delta_r_vec, "mT": _mT_vec,
        }
        vals = safe_evaluate(compiled_obs, vec_vars)
        vals = np.asarray(vals, dtype=np.float64).ravel()
        if vals.shape[0] == n:
            mask = np.isfinite(vals) & (vals > -900.0)
            outHist.h["h"].fill(vals[mask], weight=weights[mask])
            # ── Systematic variation histograms (vectorized) ──────────────
            if with_syst:
                nom_axis = outHist.h["h"].axes[0]
                njets_m = data["njets"][mask].astype(np.float64)
                nel_m = data["nel"][mask].astype(np.float64)
                nmu_m = data["nmu"][mask].astype(np.float64)
                nbjets_m = nbjets_arr[mask].astype(np.float64)
                w_m = weights[mask]
                v_m = vals[mask]
                for src in systematics.SYST_SOURCES:
                    outHist.h[f"h_{src}_up"] = bh.Histogram(nom_axis)
                    factor = systematics.event_syst_factor(src, njets_m, nel_m, nmu_m, nbjets_m)
                    outHist.h[f"h_{src}_up"].fill(v_m, weight=w_m * factor)
            return
    except Exception:
        pass

    # ── Per-event fallback (handles any expression the vectorized path can't) ─
    # OPT-2: no separate compile step here -- ``compiled_obs`` was already built once,
    # above, before ``cache_file`` was even opened, and is reused for every event.

    # Create variation histograms before the loop when with_syst is requested.
    if with_syst:
        nom_axis = outHist.h["h"].axes[0]
        for src in systematics.SYST_SOURCES:
            outHist.h[f"h_{src}_up"] = bh.Histogram(nom_axis)

    _step = max(1, n // 100)
    for i in range(n):
        if i % _step == 0:
            if cancel is not None and cancel.is_set():
                return
        try:
            l1 = _obj_from_cache(data, i, "l1", ["eta", "phi", "e", "d0", "z0", "charge", "flavour"])
            l2 = _obj_from_cache(data, i, "l2", ["eta", "phi", "e", "d0", "z0", "charge", "flavour"])
            j1 = _obj_from_cache(data, i, "j1", ["eta", "phi", "e", "btag"])
            j2 = _obj_from_cache(data, i, "j2", ["eta", "phi", "e", "btag"])
            ph1 = _obj_from_cache(data, i, "ph1", ["eta", "phi", "e"]) if "ph1_pt" in data else _P()
            ph2 = _obj_from_cache(data, i, "ph2", ["eta", "phi", "e"]) if "ph2_pt" in data else _P()
            met = _make_met(float(data["met_pt"][i]),
                            float(data["met_phi"][i]) if "met_phi" in data else 0.0)
            local_vars = {
                "nlep": int(data["nlep"][i]), "nel": int(data["nel"][i]),
                "nmu":  int(data["nmu"][i]),  "njets": int(data["njets"][i]),
                "nphot": int(data["nphot"][i]) if "nphot" in data else 0,
                "l1": l1, "l2": l2, "j1": j1, "j2": j2,
                "ph1": ph1, "ph2": ph2, "met": met,
                "deltaR": _delta_r, "mT": _mT,
            }
            obs_val = safe_evaluate(compiled_obs, local_vars)
            if obs_val is None:
                continue
            obs_val = float(obs_val)
            if obs_val <= -900:
                continue
            ev_w = float(data["weight"][i])
            outHist.h["h"].fill(obs_val, weight=ev_w)
            if with_syst:
                ev_njets = int(data["njets"][i])
                ev_nel = int(data["nel"][i])
                ev_nmu = int(data["nmu"][i])
                ev_nbjets = int(nbjets_arr[i])
                for src in systematics.SYST_SOURCES:
                    factor = float(systematics.event_syst_factor(src, ev_njets, ev_nel,
                                                                  ev_nmu, ev_nbjets))
                    outHist.h[f"h_{src}_up"].fill(obs_val, weight=ev_w * factor)
        except Exception:
            continue


def _count_bjets(btag_scores, wp: float) -> int:
    """Count jets with a b-tag score strictly above the working point.

    Extracted to its own function (the reference inlines this as a single expression at
    line 511) so tests can monkeypatch this one symbol to prove they exercise production
    b-jet counting rather than a private reimplementation -- see the carry-forward from
    B-005's cycle-1 review, discharged in ``tests/test_systematics.py``.
    """
    return int(np.count_nonzero(np.asarray(btag_scores) > wp))


# ---------------------------------------------------------------------------
# Main per-basket filter
# ---------------------------------------------------------------------------

def filter_raw_event_data(arrays, nev, cfg, outHist, observable_target,
                          cache_acc=None,
                          cancel: Optional[threading.Event] = None) -> Tuple[List, List, bool]:
    """Filter one basket of raw ROOT arrays: multiplicity cuts, selection expressions,
    cache accumulation, and observable histogramming.

    ``cancel``, if given, is checked once as an entry guard before any event in this
    basket is processed (mirroring the reference's poll of its global stop flag at that
    same call site); when it is set the function returns ``([], [], True)`` without
    touching ``outHist`` or ``cache_acc``.
    ``cancel=None`` means never cancel. The third element of the return tuple is that
    same cancelled flag for both the cancelled and completed paths.

    ``cfg["sel_exprs"]`` and ``observable_target`` are validated and compiled, through
    ``fce_web.safe_eval.compile_expr``, before this basket's ``arrays`` are touched at all
    -- not even to read a column reference, let alone index into a single event. A rejected
    expression's ``UnsafeExpression`` therefore propagates before a single event in *any*
    basket of the run has been processed. ``cfg["compiled_sel_exprs"]``, previously an
    opt-in pre-compiled-code fast path, is no longer read here: a caller-supplied compiled
    object is never trusted as evidence its source was validated (see
    ``fce_web.safe_eval.CompiledExpr``'s own docstring for why), so this function always
    (re)compiles ``cfg["sel_exprs"]`` itself.
    """
    if cancel is not None and cancel.is_set():
        return [], [], True

    sel_exprs = cfg.get("sel_exprs", [])
    compiled_sel_exprs = _compile_all(sel_exprs)
    compiled_obs = compile_expr(observable_target) if observable_target else None

    has_el = "electron_pt" in arrays and len(arrays["electron_pt"]) > 0
    has_mu = "muon_pt"     in arrays and len(arrays["muon_pt"])     > 0
    has_jt = "jet_pt"      in arrays and len(arrays["jet_pt"])      > 0
    has_ph = "photon_pt"   in arrays and len(arrays["photon_pt"])   > 0

    w_arr       = arrays["weight"]
    met_pt_arr  = arrays["MET_pt"]
    met_phi_arr = arrays.get("MET_phi")

    el_pt     = arrays["electron_pt"]  if has_el else None
    el_eta    = arrays["electron_eta"] if has_el else None
    el_phi    = arrays["electron_phi"] if has_el else None
    el_e      = arrays["electron_e"]   if has_el else None
    el_d0     = arrays.get("electron_d0signif") if has_el else None
    el_z0     = arrays.get("electron_z0signif") if has_el else None
    el_charge = arrays.get("electron_charge")   if has_el else None

    mu_pt     = arrays["muon_pt"]  if has_mu else None
    mu_eta    = arrays["muon_eta"] if has_mu else None
    mu_phi    = arrays["muon_phi"] if has_mu else None
    mu_e      = arrays["muon_e"]   if has_mu else None
    mu_d0     = arrays.get("muon_d0signif") if has_mu else None
    mu_z0     = arrays.get("muon_z0signif") if has_mu else None
    mu_charge = arrays.get("muon_charge")   if has_mu else None

    jet_pt   = arrays["jet_pt"]  if has_jt else None
    jet_eta  = arrays["jet_eta"] if has_jt else None
    jet_phi  = arrays["jet_phi"] if has_jt else None
    jet_e    = arrays["jet_e"]   if has_jt else None
    jet_btag = arrays.get("jet_btag") if has_jt else None

    ph_pt  = arrays["photon_pt"]  if has_ph else None
    ph_eta = arrays["photon_eta"] if has_ph else None
    ph_phi = arrays["photon_phi"] if has_ph else None
    ph_e   = arrays["photon_e"]   if has_ph else None

    mult_cuts = cfg.get("mult_cuts", [])

    _NULL = _P()

    for i in range(nev):
        try:
            w       = float(w_arr[i])
            met_pt  = float(met_pt_arr[i])
            met_phi = float(met_phi_arr[i]) if met_phi_arr is not None else 0.0

            nel   = len(el_pt[i]) if has_el else 0
            nmu   = len(mu_pt[i]) if has_mu else 0
            nlep  = nel + nmu
            njets = len(jet_pt[i]) if has_jt else 0
            nphot = len(ph_pt[i])  if has_ph else 0
            if has_jt and jet_btag is not None:
                nbjets = _count_bjets(jet_btag[i], systematics.BTAG_WP)
            else:
                nbjets = 0

            # ── Multiplicity cuts ────────────────────────────────────────
            skip = False
            for cut in mult_cuts:
                if len(cut) == 7:
                    cut_nlep, op_lep, cut_njets, op_jet, ltype, cut_nphot, op_phot = cut
                else:
                    # Legacy 4-tuple format: (nlep, njets, ltype, nphot)
                    cut_nlep, cut_njets = cut[0], cut[1]
                    ltype = cut[2] if len(cut) > 2 else "Any"
                    cut_nphot = cut[3] if len(cut) > 3 else 0
                    op_lep = op_jet = op_phot = ">="
                count = {"Electron": nel, "Muon": nmu}.get(ltype, nlep)

                def _cmp(actual, op, threshold):
                    if op == "==":
                        return actual == threshold
                    if op == "<=":
                        return actual <= threshold
                    return actual >= threshold

                if not (_cmp(count, op_lep, cut_nlep)
                        and _cmp(njets, op_jet, cut_njets)
                        and _cmp(nphot, op_phot, cut_nphot)):
                    skip = True
                    break
            if skip:
                continue

            # ── Build lepton list (pt-sorted) ────────────────────────────
            leptons = []
            if has_el:
                for il in range(nel):
                    leptons.append({
                        "pt": float(el_pt[i][il]), "eta": float(el_eta[i][il]),
                        "phi": float(el_phi[i][il]), "e": float(el_e[i][il]),
                        "d0": float(el_d0[i][il]) if el_d0 is not None else 0.0,
                        "z0": float(el_z0[i][il]) if el_z0 is not None else 0.0,
                        "charge": float(el_charge[i][il]) if el_charge is not None else 0.0,
                        "flavour": 11.0,
                    })
            if has_mu:
                for im in range(nmu):
                    leptons.append({
                        "pt": float(mu_pt[i][im]), "eta": float(mu_eta[i][im]),
                        "phi": float(mu_phi[i][im]), "e": float(mu_e[i][im]),
                        "d0": float(mu_d0[i][im]) if mu_d0 is not None else 0.0,
                        "z0": float(mu_z0[i][im]) if mu_z0 is not None else 0.0,
                        "charge": float(mu_charge[i][im]) if mu_charge is not None else 0.0,
                        "flavour": 13.0,
                    })
            leptons.sort(key=lambda x: x["pt"], reverse=True)

            # ── Build jet list (pt-sorted) ──────────────────────────────
            jets = []
            if has_jt:
                for ij in range(njets):
                    btag = float(jet_btag[i][ij]) if jet_btag is not None else 0.0
                    jets.append({"pt": float(jet_pt[i][ij]), "eta": float(jet_eta[i][ij]),
                                 "phi": float(jet_phi[i][ij]), "e":  float(jet_e[i][ij]),
                                 "btag": btag})
            jets.sort(key=lambda x: x["pt"], reverse=True)

            # ── Build photon list (pt-sorted) ─────────────────────────────
            photons = []
            if has_ph:
                for ip in range(nphot):
                    photons.append({"pt": float(ph_pt[i][ip]), "eta": float(ph_eta[i][ip]),
                                    "phi": float(ph_phi[i][ip]), "e":  float(ph_e[i][ip])})
                photons.sort(key=lambda x: x["pt"], reverse=True)

            # ── Physics objects ──────────────────────────────────────────
            l1  = _make_lepton(leptons[0])  if len(leptons) >= 1 else _NULL
            l2  = _make_lepton(leptons[1])  if len(leptons) >= 2 else _NULL
            j1  = _make_jet(jets[0])        if len(jets)    >= 1 else _NULL
            j2  = _make_jet(jets[1])        if len(jets)    >= 2 else _NULL
            ph1 = _make_photon(photons[0])  if len(photons) >= 1 else _NULL
            ph2 = _make_photon(photons[1])  if len(photons) >= 2 else _NULL
            met = _make_met(met_pt, met_phi)

            local_vars = {
                "nlep": nlep, "nel": nel, "nmu": nmu, "njets": njets, "nphot": nphot,
                "l1": l1, "l2": l2, "j1": j1, "j2": j2,
                "ph1": ph1, "ph2": ph2, "met": met,
                "deltaR": _delta_r, "mT": _mT,
            }

            # ── Selection expressions ────────────────────────────────────
            skip = False
            for ce in compiled_sel_exprs:
                try:
                    if not safe_evaluate(ce, local_vars):
                        skip = True
                        break
                except Exception:
                    skip = True
                    break
            if skip:
                continue

            # ── Event passes all cuts — accumulate for cache ─────────────
            if cache_acc is not None:
                _append_event(cache_acc, nlep, nel, nmu, njets, nphot, nbjets,
                              l1, l2, j1, j2, ph1, ph2, met, w)

            # ── Observable evaluation ────────────────────────────────────
            if outHist is not None and compiled_obs is not None:
                try:
                    obs_val = safe_evaluate(compiled_obs, local_vars)
                    if obs_val is None:
                        continue
                    obs_val = float(obs_val)
                    if obs_val <= -900:
                        continue
                    outHist.h["h"].fill(obs_val, weight=w)
                except Exception:
                    continue

        except Exception:
            continue

    return [], [], False
