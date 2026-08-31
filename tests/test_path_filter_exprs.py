"""B-008: prove ``fce_web.engine.path_filter`` routes every student-typed expression
through ``fce_web.safe_eval`` correctly, not just that it no longer calls the two unsafe
builtins by name.

Four things this file exists to prove, one per acceptance criterion:

* C2 -- the vectorized fast path and the per-event fallback, evaluating the *same*
  compiled expression against the *same* events, produce identical numbers.
* C3 -- an ``UnsafeExpression`` from a rejected expression is never swallowed by one of
  this module's several bare ``except Exception`` handlers.
* C4 -- a malicious expression fed in as a selection is refused before a single event
  in the basket is read, measured rather than assumed.
* C5 is exercised by ``tests/test_path_filter.py`` (unchanged, read-only to this task).
"""
import math

import numpy as np
import pytest

from fce_web.engine.path_filter import (
    _P, _ArrayProxy, _obj_from_cache, _make_met, _delta_r, _delta_r_vec, _mT, _mT_vec,
    make_cache_acc, _append_event, save_cache, filter_raw_event_data,
)
from fce_web.safe_eval import compile_expr, evaluate, UnsafeExpression

LEPTON_KEYS = ["eta", "phi", "e", "d0", "z0", "charge", "flavour"]
JET_KEYS = ["eta", "phi", "e", "btag"]
PHOTON_KEYS = ["eta", "phi", "e"]

#: Rejected purely by AST shape -- ``__class__`` starts with ``_``, which
#: ``fce_web.safe_eval._validate`` rejects unconditionally, before any name in the
#: expression is even looked up against the event namespace. This is the
#: attribute-traversal escape ``.claude/backend/CLAUDE.md`` §3.2 describes.
ESCAPE_EXPR = "l1.__class__.__init__.__globals__"

# ---------------------------------------------------------------------------
# Synthetic event corpus -- real numbers throughout (no null/sentinel objects,
# so p4 arithmetic and deltaR/mT stay finite on both paths and a mismatch can
# only come from the code under test, not from garbage-in-garbage-out agreement).
# ---------------------------------------------------------------------------

_EVENTS = [
    dict(nlep=2, nel=2, nmu=0, njets=1, nphot=0, nbjets=1,
         l1=_P(pt=40.0, eta=0.5, phi=0.2, e=45.61),
         l2=_P(pt=25.0, eta=-0.3, phi=1.0, e=26.63),
         j1=_P(pt=50.0, eta=1.0, phi=-0.5, e=55.0, btag=0.9),
         j2=_P(pt=18.0, eta=0.2, phi=1.5, e=20.0, btag=0.1),
         ph1=_P(pt=6.0, eta=0.1, phi=0.3, e=6.5),
         ph2=_P(pt=4.0, eta=-0.2, phi=2.0, e=4.2),
         met=_P(pt=10.0, phi=0.1), w=1.0),
    dict(nlep=2, nel=1, nmu=1, njets=2, nphot=1, nbjets=0,
         l1=_P(pt=15.0, eta=2.0, phi=-2.5, e=56.93),
         l2=_P(pt=8.0, eta=-1.8, phi=1.5, e=25.36),
         j1=_P(pt=30.0, eta=-1.5, phi=2.0, e=35.0, btag=0.02),
         j2=_P(pt=20.0, eta=0.0, phi=0.0, e=22.0, btag=0.04),
         ph1=_P(pt=12.0, eta=0.3, phi=0.4, e=13.0),
         ph2=_P(pt=3.0, eta=1.1, phi=-1.0, e=3.4),
         met=_P(pt=5.0, phi=-1.0), w=2.0),
    dict(nlep=0, nel=0, nmu=0, njets=3, nphot=0, nbjets=2,
         l1=_P(pt=1.0, eta=0.01, phi=0.02, e=1.5),
         l2=_P(pt=1.0, eta=0.02, phi=0.03, e=1.5),
         j1=_P(pt=90.0, eta=0.4, phi=1.2, e=95.0, btag=0.99),
         j2=_P(pt=60.0, eta=-0.9, phi=-2.9, e=65.0, btag=0.5),
         ph1=_P(pt=2.0, eta=0.0, phi=0.0, e=2.0),
         ph2=_P(pt=2.0, eta=0.0, phi=0.0, e=2.0),
         met=_P(pt=45.0, phi=3.0), w=0.5),
    dict(nlep=3, nel=2, nmu=1, njets=0, nphot=2, nbjets=0,
         l1=_P(pt=60.0, eta=-0.6, phi=0.9, e=71.63),
         l2=_P(pt=55.0, eta=0.6, phi=-0.9, e=65.7),
         j1=_P(pt=5.0, eta=0.0, phi=0.0, e=5.0, btag=0.01),
         j2=_P(pt=5.0, eta=0.0, phi=0.0, e=5.0, btag=0.01),
         ph1=_P(pt=25.0, eta=1.4, phi=-1.4, e=30.0),
         ph2=_P(pt=15.0, eta=-1.4, phi=1.4, e=18.0),
         met=_P(pt=0.5, phi=0.0), w=1.5),
    dict(nlep=2, nel=0, nmu=2, njets=1, nphot=0, nbjets=1,
         l1=_P(pt=91.0, eta=0.05, phi=0.1, e=91.61),
         l2=_P(pt=45.0, eta=-2.4, phi=-3.0, e=250.56),
         j1=_P(pt=12.0, eta=0.3, phi=0.3, e=12.5, btag=0.7),
         j2=_P(pt=8.0, eta=-0.3, phi=-0.3, e=8.5, btag=0.2),
         ph1=_P(pt=1.0, eta=0.0, phi=0.0, e=1.0),
         ph2=_P(pt=1.0, eta=0.0, phi=0.0, e=1.0),
         met=_P(pt=20.0, phi=2.5), w=1.0),
]

#: The operators actually used by the reference corpus (``.claude/backend/CLAUDE.md``
#: §3.2's worked examples): comparison, ``+ - * /``, attribute access one and two levels
#: deep, p4 addition and ``.mass``, and the two named helper calls plus ``abs``.
#:
#: Deliberately excludes any expression combining two conditions with ``and``/``or``/``not``
#: (e.g. ``l1.pt > 20 and l2.pt > 10``): a Python ``BoolOp``/``UnaryOp Not`` applied to a
#: numpy boolean *array* raises ``ValueError: truth value of an array ... is ambiguous`` --
#: not a bug introduced by this task, the reference's own vectorized fast path has exactly
#: the same limitation and relies on its bare ``except Exception`` to fall all the way back
#: to the per-event loop for such an expression. There is therefore no vectorized value to
#: compare against for that case; ``test_boolean_operators_agree_with_manual_combination``
#: below covers ``and``/``or``/``not`` on the per-event path instead, which is the only path
#: they ever actually run on.
EXPR_CORPUS = [
    "nlep >= 2",
    "l1.pt > 20",
    "(l1.p4 + l2.p4).mass",
    "j1.btag > 0.7",
    "abs(l1.eta) < 2.5",
    "deltaR(l1, l2) < 3.0",
    "mT(l1, met) > 5",
    "l1.pt - l2.pt",
    "l1.pt / (l2.pt + 1.0)",
    "njets == 0",
]

#: float32 is the cache's on-disk storage dtype (``make_cache_acc``); round-tripping a
#: value through it loses precision below roughly the 6th-7th significant digit. For
#: values in this corpus's range (single to low hundreds of GeV) that is an absolute
#: error on the order of 1e-3 at worst, so ``ATOL`` is set an order of magnitude above
#: that float32 noise floor, and ``RTOL`` covers the rest for larger magnitudes.
RTOL = 1e-4
ATOL = 1e-3


def _build_cache(tmp_path, name="expr_corpus.npz"):
    acc = make_cache_acc()
    for ev in _EVENTS:
        _append_event(acc, ev["nlep"], ev["nel"], ev["nmu"], ev["njets"], ev["nphot"],
                      ev["nbjets"], ev["l1"], ev["l2"], ev["j1"], ev["j2"],
                      ev["ph1"], ev["ph2"], ev["met"], ev["w"])
    cache_file = str(tmp_path / name)
    save_cache(cache_file, acc)
    return cache_file


def _vec_vars(data):
    n = len(data["weight"])
    return {
        "nlep": data["nlep"], "nel": data["nel"], "nmu": data["nmu"], "njets": data["njets"],
        "nphot": data["nphot"] if "nphot" in data else np.zeros(n, dtype=np.float32),
        "l1": _ArrayProxy("l1", data), "l2": _ArrayProxy("l2", data),
        "j1": _ArrayProxy("j1", data), "j2": _ArrayProxy("j2", data),
        "ph1": _ArrayProxy("ph1", data), "ph2": _ArrayProxy("ph2", data),
        "met": _ArrayProxy("met", data),
        "deltaR": _delta_r_vec, "mT": _mT_vec,
    }


def _local_vars(data, i):
    l1 = _obj_from_cache(data, i, "l1", LEPTON_KEYS)
    l2 = _obj_from_cache(data, i, "l2", LEPTON_KEYS)
    j1 = _obj_from_cache(data, i, "j1", JET_KEYS)
    j2 = _obj_from_cache(data, i, "j2", JET_KEYS)
    ph1 = _obj_from_cache(data, i, "ph1", PHOTON_KEYS) if "ph1_pt" in data else _P()
    ph2 = _obj_from_cache(data, i, "ph2", PHOTON_KEYS) if "ph2_pt" in data else _P()
    met = _make_met(float(data["met_pt"][i]),
                    float(data["met_phi"][i]) if "met_phi" in data else 0.0)
    return {
        "nlep": int(data["nlep"][i]), "nel": int(data["nel"][i]), "nmu": int(data["nmu"][i]),
        "njets": int(data["njets"][i]),
        "nphot": int(data["nphot"][i]) if "nphot" in data else 0,
        "l1": l1, "l2": l2, "j1": j1, "j2": j2, "ph1": ph1, "ph2": ph2, "met": met,
        "deltaR": _delta_r, "mT": _mT,
    }


# ---------------------------------------------------------------------------
# C2: vectorized/per-event parity over the corpus
# ---------------------------------------------------------------------------

def test_vectorized_and_per_event_paths_agree_on_corpus(tmp_path):
    cache_file = _build_cache(tmp_path)
    data = np.load(cache_file, mmap_mode="r")
    n = len(data["weight"])
    compiled = [compile_expr(e) for e in EXPR_CORPUS]

    checked = 0
    for expr, ce in zip(EXPR_CORPUS, compiled):
        vec_result = np.asarray(evaluate(ce, _vec_vars(data)), dtype=np.float64).ravel()
        assert vec_result.shape[0] == n, f"expr {expr!r}: vectorized result shape mismatch"
        for i in range(n):
            per_event_result = float(evaluate(ce, _local_vars(data, i)))
            checked += 1
            assert math.isclose(vec_result[i], per_event_result, rel_tol=RTOL, abs_tol=ATOL), (
                f"expr {expr!r} event {i}: vectorized={vec_result[i]!r} "
                f"per-event={per_event_result!r}"
            )

    assert checked == len(EXPR_CORPUS) * n
    print(f"compared {len(EXPR_CORPUS)} expressions x {n} events = {checked} values, "
          f"rtol={RTOL} atol={ATOL}")


def test_boolean_operators_agree_with_manual_combination(tmp_path):
    """``and``/``or``/``not`` never reach the vectorized path (see the corpus comment
    above), so their parity check is against a manual combination of two independently
    validated sub-expressions on the per-event path -- the only path they run on in
    production.
    """
    cache_file = _build_cache(tmp_path, name="boolean_corpus.npz")
    data = np.load(cache_file, mmap_mode="r")
    n = len(data["weight"])

    left = compile_expr("l1.pt > 20")
    right = compile_expr("l2.pt > 10")
    and_expr = compile_expr("l1.pt > 20 and l2.pt > 10")
    or_expr = compile_expr("l1.pt > 20 or l2.pt > 10")
    not_expr = compile_expr("not (njets == 0)")
    eq_expr = compile_expr("njets == 0")

    checked = 0
    for i in range(n):
        names = _local_vars(data, i)
        left_val = bool(evaluate(left, names))
        right_val = bool(evaluate(right, names))
        assert bool(evaluate(and_expr, names)) == (left_val and right_val)
        assert bool(evaluate(or_expr, names)) == (left_val or right_val)
        assert bool(evaluate(not_expr, names)) == (not bool(evaluate(eq_expr, names)))
        checked += 3

    assert checked == n * 3
    print(f"compared 3 boolean expressions x {n} events = {checked} values (per-event only)")


def test_corpus_parity_mutation_gate_perturbed_vectorized_operand_is_caught(tmp_path, monkeypatch):
    """Perturbing only the vectorized ``_P4Proxy.mass`` (the per-event path computes mass
    through the ``vector`` package, an entirely separate code path, so this mutation cannot
    touch it) must make the comparison above fail -- proving it actually compares values
    instead of merely running both paths without checking anything.
    """
    from fce_web.engine import path_filter as pf

    cache_file = _build_cache(tmp_path, name="mutation_corpus.npz")
    data = np.load(cache_file, mmap_mode="r")
    n = len(data["weight"])
    expr = "(l1.p4 + l2.p4).mass"
    ce = compile_expr(expr)

    original_mass = pf._P4Proxy.mass

    def _perturbed_mass(self):
        return original_mass.fget(self) + 5.0

    monkeypatch.setattr(pf._P4Proxy, "mass", property(_perturbed_mass))

    vec_result = np.asarray(evaluate(ce, _vec_vars(data)), dtype=np.float64).ravel()

    mismatch = None
    for i in range(n):
        per_event_result = float(evaluate(ce, _local_vars(data, i)))
        if not math.isclose(vec_result[i], per_event_result, rel_tol=RTOL, abs_tol=ATOL):
            mismatch = (i, vec_result[i], per_event_result)
            break

    assert mismatch is not None, "the +5.0 mutation produced no detectable mismatch"
    i, vv, pv = mismatch
    message = f"expr {expr!r} event {i}: vectorized={vv!r} per-event={pv!r}"
    assert expr in message
    assert repr(vv) in message


# ---------------------------------------------------------------------------
# C3: an UnsafeExpression is never swallowed
# ---------------------------------------------------------------------------

def test_unsafe_expression_propagates_from_filter_raw_event_data():
    with pytest.raises(UnsafeExpression):
        filter_raw_event_data(
            {"weight": [1.0], "MET_pt": [0.0]}, nev=1,
            cfg={"sel_exprs": [ESCAPE_EXPR]}, outHist=None, observable_target=None,
        )


def test_unsafe_expression_propagates_from_filter_raw_event_data_as_observable():
    with pytest.raises(UnsafeExpression):
        filter_raw_event_data(
            {"weight": [1.0], "MET_pt": [0.0]}, nev=1,
            cfg={}, outHist=object(), observable_target=ESCAPE_EXPR,
        )


def test_unsafe_expression_propagates_from_fill_histogram_from_cache(tmp_path):
    pytest.importorskip("boost_histogram")
    from fce_web.engine.path_filter import fill_histogram_from_cache

    cache_file = _build_cache(tmp_path, name="unsafe_hist.npz")

    class _Hist:
        def __init__(self):
            self.h = {}

    with pytest.raises(UnsafeExpression):
        fill_histogram_from_cache(cache_file, _Hist(), ESCAPE_EXPR, with_syst=False)


def test_unsafe_expression_propagates_from_filter_selection_cache(tmp_path):
    from fce_web.engine.path_filter import filter_selection_cache

    cache_file = _build_cache(tmp_path, name="unsafe_sel.npz")
    out_path = str(tmp_path / "unsafe_sel_out.npz")

    with pytest.raises(UnsafeExpression):
        filter_selection_cache(cache_file, [ESCAPE_EXPR], out_path)


def test_unsafe_expression_mutation_gate_widened_handler_is_caught(monkeypatch):
    """If the entry-point compilation step is monkeypatched to swallow
    ``UnsafeExpression`` instead of letting it propagate -- the exact defect this
    criterion guards against -- the propagation test above must fail: the malicious
    selection is silently dropped and the function completes normally instead of
    raising.
    """
    from fce_web.engine import path_filter as pf

    def _swallowing_compile_all(exprs):
        try:
            return [pf.compile_expr(e) for e in exprs if e]
        except UnsafeExpression:
            return []

    monkeypatch.setattr(pf, "_compile_all", _swallowing_compile_all)

    result = pf.filter_raw_event_data(
        {"weight": [1.0], "MET_pt": [0.0]}, nev=1,
        cfg={"sel_exprs": [ESCAPE_EXPR]}, outHist=None, observable_target=None,
    )
    assert result[2] is False, "widened handler should let the call complete without raising"


# ---------------------------------------------------------------------------
# C4: an escaping selection is refused before any event is read
# ---------------------------------------------------------------------------

class _CountingSeq(list):
    """A list that counts every ``__getitem__`` call -- a per-event read, in production."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.reads = 0

    def __getitem__(self, idx):
        self.reads += 1
        return super().__getitem__(idx)


def test_escape_expression_as_selection_refused_before_any_event_is_read():
    weight = _CountingSeq([1.0, 1.0, 1.0])
    met = _CountingSeq([0.0, 0.0, 0.0])
    arrays = {"weight": weight, "MET_pt": met}

    with pytest.raises(UnsafeExpression):
        filter_raw_event_data(
            arrays, nev=3, cfg={"sel_exprs": [ESCAPE_EXPR]},
            outHist=None, observable_target=None,
        )

    print(f"events read before rejection: weight={weight.reads} met_pt={met.reads}")
    assert weight.reads == 0
    assert met.reads == 0


def test_escape_expression_mutation_gate_late_validation_is_caught(monkeypatch):
    """Monkeypatching validation to a no-op simulates moving it to after the read loop
    begins: the malicious selection no longer raises, and the loop actually reads
    events -- proving the early-rejection test above is sensitive to exactly this
    regression, not merely to *some* exception happening somewhere.
    """
    from fce_web.engine import path_filter as pf

    monkeypatch.setattr(pf, "_compile_all", lambda exprs: [])

    weight = _CountingSeq([1.0, 1.0, 1.0])
    met = _CountingSeq([0.0, 0.0, 0.0])
    arrays = {"weight": weight, "MET_pt": met}

    result = pf.filter_raw_event_data(
        arrays, nev=3, cfg={"sel_exprs": [ESCAPE_EXPR]},
        outHist=None, observable_target=None,
    )

    assert result[2] is False, "no-op validation should let the call complete without raising"
    assert weight.reads > 0, "mutation should have let the event loop run and read events"
