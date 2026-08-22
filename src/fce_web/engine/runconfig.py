"""Loader for the analysis config the engine consumes, and its two
content-addressed md5 cache keys.

In the reference (``kskovpen/fce``), the ``cfg`` dict the engine runs against
has no headless producer -- it is built only by ``compile_graph_topology()``
in ``ui/graph.py``, ~230 lines of ``dpg.get_value()`` calls behind a dearpygui
UI. This module is *not* a reimplementation of that compiler (that is a later
milestone's job); it is a typed loader for the 13-key shape that compiler
returns, plus the six lines of that function that compute ``h5_sel`` and
``h5`` -- carried over here verbatim so the disk cache stays content-addressed
against the same keys the desktop app already wrote
(``.claude/shared/CLAUDE.md`` §2).

The digest formula, quoted from ``ui/graph.py``::

    mult_h5_base = energy + detector + str(mult_cuts)                          # :1866
    h5_sel = hashlib.md5((mult_h5_base + str(sel_exprs)).encode()).hexdigest() # :1877
    h5_full = hashlib.md5(
        (h5_sel + hcfg_raw["observable"] + hcfg_raw["bins"]
         + hcfg_raw["min"] + hcfg_raw["max"] + hcfg_raw["target"]).encode()
    ).hexdigest()                                                              # :1881-1884

Two properties of that formula are load-bearing and easy to break by
"normalising" the data on the way in:

* It is **raw string concatenation with no separators**, over fields
  (``bins``, ``min``, ``max``, ``target``) that arrive from dpg text widgets
  as *strings*, never as numbers. Coercing ``bins`` to ``int`` changes the
  digest and silently misses every cache entry the desktop app ever wrote.
* ``str(mult_cuts)`` and ``str(sel_exprs)`` are Python's ``repr`` of a
  *container*, so both element order and container type matter: a list and a
  tuple with the same contents produce different digests. The reference
  builds ``mult_cuts`` as a ``list`` of ``tuple``s
  (``mult_cuts.append((nlep, op_lep, ...))`` at ``ui/graph.py``:1719), so
  this loader reproduces that exact shape rather than a JSON-native
  list-of-lists. Element *types* matter for the same reason: a JSON ``"2"``
  where the reference's ``int(dpg.get_value(...))`` produces ``2`` changes
  ``str(mult_cuts)`` and therefore the digest, so ``_load_mult_cuts``
  enforces the 7-tuple's ``(int, str, int, str, str, int, str)`` shape.

``from_dict`` raises :class:`RunConfigError` -- rather than silently
accepting -- when a stored digest does not match the one recomputed from a
config's other fields. This is deliberate (B-010 cycle 1): a mis-authored
fixture failing loudly at load time is worth more than one that misses the
disk cache forever. **This now covers the nested digests, not just the
top-level ones.** ``cfg["h5"]`` / ``cfg["h5_sel"]`` are validated as before,
and in addition every ``selections[i]["h5_sel"]`` and every
``selections[i]["histograms"][j]["h5"]`` is recomputed and compared. This
matters because the top-level ``h5``/``h5_sel``/``histograms`` fields are
`ui/graph.py`'s backward-compat flattening of the *first* selection only
(``ui/graph.py``:1907-1923) -- the engine itself never reads them when
``cfg["selections"]`` is present. ``engine/analytical_loop.py``:68,79,183-186
read ``sel_cfg["h5_sel"]`` and ``hcfg["h5"]`` out of ``cfg["selections"]``,
so top-level validation alone leaves the digests that are actually used for
cache addressing unchecked. (The top-level fields are still validated,
because they remain the source of truth for the fallback path
``engine/analytical_loop.py``:203-212 takes when ``cfg["selections"]`` is
empty.)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__all__ = ["RunConfig", "RunConfigError", "HistogramConfig", "SelectionConfig"]


class RunConfigError(ValueError):
    """A config file or dict could not be loaded into a ``RunConfig``.

    Covers an unknown field, a missing field, a field of the wrong type, or a
    stored digest that does not match the one recomputed from the config's
    other fields.
    """


# The 13-key shape returned by ``compile_graph_topology()`` at
# ui/graph.py:1914-1923.
_CFG_KEYS = (
    "energy", "detector", "observable", "bins", "min", "max", "target",
    "h5", "h5_sel", "mult_cuts", "sel_exprs", "histograms", "selections",
)

_HISTOGRAM_KEYS = (
    "observable", "x_label", "bins", "min", "max", "target", "node_name",
    "obs_nid", "hist_nid", "h5", "plot_idx",
)

_SELECTION_KEYS = (
    "nid", "prefix_nids", "node_name", "sel_custom_name", "sel_exprs",
    "h5_sel", "histograms",
)

# The seven-element shape of one Multiplicity node's cut, from
# ui/graph.py:1719: (nlep, op_lep, njets, op_jet, ltype, nphot, op_phot).
_MULT_CUT_LEN = 7

# Fields whose value must stay a str all the way to the point of hashing,
# because the digest formula concatenates them with no separator and no
# type coercion. THE TRAP this module exists to not repeat.
_STRING_DIGEST_FIELDS = ("energy", "detector", "observable", "bins", "min", "max", "target")


def _reject_unknown_keys(data: dict, allowed: tuple, context: str) -> None:
    unknown = sorted(set(data) - set(allowed))
    if unknown:
        raise RunConfigError(
            f"unknown field(s) in {context}: {', '.join(unknown)}"
        )


def _require_keys(data: dict, required: tuple, context: str) -> None:
    missing = sorted(set(required) - set(data))
    if missing:
        raise RunConfigError(
            f"missing field(s) in {context}: {', '.join(missing)}"
        )


def _require_str(data: dict, keys: tuple, context: str) -> None:
    for key in keys:
        value = data[key]
        if not isinstance(value, str):
            raise RunConfigError(
                f"field '{key}' in {context} must be a string (dpg text widgets never "
                f"produce anything else), got {type(value).__name__}: {value!r}"
            )


# The element types of one Multiplicity node's cut, from ui/graph.py:1709-1719
# -- (nlep, op_lep, njets, op_jet, ltype, nphot, op_phot), where the counts are
# ``int(dpg.get_value(...))`` and the rest are dpg combo-box strings. A count
# stored as a JSON string ("2" instead of 2) still passes the length/container
# checks below but changes ``str(mult_cuts)`` -- the same trap _require_str
# exists to close for bins/min/max/target, one level down.
_MULT_CUT_TYPES = (int, str, int, str, str, int, str)


def _load_mult_cuts(raw) -> list:
    """Reproduce the reference's ``mult_cuts``: a *list* of 7-tuples.

    JSON has no tuple type, so the fixture stores each cut as a JSON array;
    this converts each one to a tuple, because ``str(list_of_tuples)`` and
    ``str(list_of_lists)`` are different strings and the digest formula
    hashes whichever one the reference actually built.
    """
    if not isinstance(raw, list):
        raise RunConfigError(f"'mult_cuts' must be a list, got {type(raw).__name__}")
    cuts = []
    for i, cut in enumerate(raw):
        if not isinstance(cut, (list, tuple)) or len(cut) != _MULT_CUT_LEN:
            raise RunConfigError(
                f"'mult_cuts[{i}]' must be a {_MULT_CUT_LEN}-element sequence, got {cut!r}"
            )
        for j, (element, expected_type) in enumerate(zip(cut, _MULT_CUT_TYPES)):
            # bool is a subclass of int; reject it explicitly so a JSON
            # `true`/`false` cannot slip past an `isinstance(x, int)` check.
            if expected_type is int and (
                not isinstance(element, int) or isinstance(element, bool)
            ):
                raise RunConfigError(
                    f"'mult_cuts[{i}][{j}]' must be an int, got "
                    f"{type(element).__name__}: {element!r}"
                )
            if expected_type is str and not isinstance(element, str):
                raise RunConfigError(
                    f"'mult_cuts[{i}][{j}]' must be a string, got "
                    f"{type(element).__name__}: {element!r}"
                )
        cuts.append(tuple(cut))
    return cuts


def _dump_mult_cuts(cuts: list) -> list:
    return [list(cut) for cut in cuts]


@dataclass(frozen=True)
class HistogramConfig:
    """One entry of ``cfg["histograms"]`` -- one Histogram node's settings.

    ``obs_nid`` / ``hist_nid`` are the dpg node ids the reference threads
    through purely to colour nodes green in the desktop UI. The headless
    path has no nodes to colour, so they are optional here.
    """

    observable: str
    x_label: str
    bins: str
    min: str
    max: str
    target: str
    node_name: str
    h5: str
    plot_idx: int
    obs_nid: Optional[int] = None
    hist_nid: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "HistogramConfig":
        _reject_unknown_keys(data, _HISTOGRAM_KEYS, "histogram entry")
        _require_keys(
            data,
            ("observable", "x_label", "bins", "min", "max", "target", "node_name", "h5", "plot_idx"),
            "histogram entry",
        )
        _require_str(
            data, ("observable", "bins", "min", "max", "target"), "histogram entry",
        )
        return cls(
            observable=data["observable"],
            x_label=data["x_label"],
            bins=data["bins"],
            min=data["min"],
            max=data["max"],
            target=data["target"],
            node_name=data["node_name"],
            h5=data["h5"],
            plot_idx=data["plot_idx"],
            obs_nid=data.get("obs_nid"),
            hist_nid=data.get("hist_nid"),
        )

    def to_dict(self) -> dict:
        return {
            "observable": self.observable,
            "x_label": self.x_label,
            "bins": self.bins,
            "min": self.min,
            "max": self.max,
            "target": self.target,
            "node_name": self.node_name,
            "obs_nid": self.obs_nid,
            "hist_nid": self.hist_nid,
            "h5": self.h5,
            "plot_idx": self.plot_idx,
        }


@dataclass(frozen=True)
class SelectionConfig:
    """One entry of ``cfg["selections"]`` -- one Selection branch's cuts and
    the histograms hung off it.

    ``nid`` / ``prefix_nids`` are dpg node ids, optional for the same reason
    as ``HistogramConfig.obs_nid`` / ``hist_nid``.
    """

    node_name: str
    sel_custom_name: str
    sel_exprs: list = field(default_factory=list)
    h5_sel: str = ""
    histograms: list = field(default_factory=list)
    nid: Optional[int] = None
    prefix_nids: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "SelectionConfig":
        _reject_unknown_keys(data, _SELECTION_KEYS, "selection entry")
        _require_keys(
            data,
            ("node_name", "sel_custom_name", "sel_exprs", "h5_sel", "histograms"),
            "selection entry",
        )
        if not isinstance(data["sel_exprs"], list):
            raise RunConfigError("'sel_exprs' in selection entry must be a list")
        for i, expr in enumerate(data["sel_exprs"]):
            if not isinstance(expr, str):
                raise RunConfigError(
                    f"'sel_exprs[{i}]' in selection entry must be a string, got {type(expr).__name__}"
                )
        histograms = [HistogramConfig.from_dict(h) for h in data["histograms"]]
        return cls(
            node_name=data["node_name"],
            sel_custom_name=data["sel_custom_name"],
            sel_exprs=list(data["sel_exprs"]),
            h5_sel=data["h5_sel"],
            histograms=histograms,
            nid=data.get("nid"),
            prefix_nids=list(data.get("prefix_nids") or []),
        )

    def to_dict(self) -> dict:
        return {
            "nid": self.nid,
            "prefix_nids": list(self.prefix_nids),
            "node_name": self.node_name,
            "sel_custom_name": self.sel_custom_name,
            "sel_exprs": list(self.sel_exprs),
            "h5_sel": self.h5_sel,
            "histograms": [h.to_dict() for h in self.histograms],
        }


def _validate_nested_digests(cfg: "RunConfig") -> None:
    """Recompute and compare ``h5_sel``/``h5`` per selection and per
    histogram, not just at the top level.

    ``engine/analytical_loop.py``:68,79,183-186 read ``sel_cfg["h5_sel"]``
    and ``hcfg["h5"]`` out of ``cfg["selections"]`` -- never the top-level
    flattened fields ``from_dict`` already checks -- so a nested digest that
    disagrees with its own selection's cuts is exactly the silent,
    permanent cache miss the top-level check was meant to prevent.
    """
    mult_h5_base = cfg.energy + cfg.detector + str(cfg.mult_cuts)
    for i, sel in enumerate(cfg.selections):
        expected_h5_sel = hashlib.md5(
            (mult_h5_base + str(sel.sel_exprs)).encode()
        ).hexdigest()
        if sel.h5_sel != expected_h5_sel:
            raise RunConfigError(
                f"'selections[{i}].h5_sel' ({sel.h5_sel}) does not match the value "
                f"computed from energy/detector/mult_cuts/selections[{i}].sel_exprs "
                f"({expected_h5_sel})"
            )
        for j, hist in enumerate(sel.histograms):
            expected_h5 = hashlib.md5(
                (
                    expected_h5_sel + hist.observable + hist.bins
                    + hist.min + hist.max + hist.target
                ).encode()
            ).hexdigest()
            if hist.h5 != expected_h5:
                raise RunConfigError(
                    f"'selections[{i}].histograms[{j}].h5' ({hist.h5}) does not match "
                    f"the value computed from selections[{i}].h5_sel/observable/bins/"
                    f"min/max/target ({expected_h5})"
                )


@dataclass(frozen=True)
class RunConfig:
    """A typed ``cfg``: the 13-key shape ``compile_graph_topology()`` returns
    in the reference, plus the two content-addressed cache keys computed the
    same way it computes them.

    Construct with :meth:`from_file` or :meth:`from_dict`. Both validate that
    the stored ``h5`` / ``h5_sel`` match what :meth:`compute_h5` /
    :meth:`compute_h5_sel` derive from the config's other fields -- a
    hand-authored fixture with a wrong digest is rejected loudly rather than
    silently missing the cache forever.
    """

    energy: str
    detector: str
    observable: str
    bins: str
    min: str
    max: str
    target: str
    h5: str
    h5_sel: str
    mult_cuts: list
    sel_exprs: list
    histograms: list
    selections: list

    def compute_h5_sel(self) -> str:
        """``h5_sel`` per ``ui/graph.py``:1866,1877 -- covers ``energy``,
        ``detector``, ``mult_cuts``, ``sel_exprs``."""
        mult_h5_base = self.energy + self.detector + str(self.mult_cuts)
        return hashlib.md5((mult_h5_base + str(self.sel_exprs)).encode()).hexdigest()

    def compute_h5(self) -> str:
        """``h5`` per ``ui/graph.py``:1881-1884 -- covers everything
        :meth:`compute_h5_sel` covers, plus ``observable``, ``bins``,
        ``min``, ``max``, ``target``."""
        h5_sel = self.compute_h5_sel()
        return hashlib.md5(
            (h5_sel + self.observable + self.bins + self.min + self.max + self.target).encode()
        ).hexdigest()

    @classmethod
    def from_dict(cls, data: dict) -> "RunConfig":
        _reject_unknown_keys(data, _CFG_KEYS, "config")
        _require_keys(data, _CFG_KEYS, "config")
        _require_str(data, _STRING_DIGEST_FIELDS, "config")
        if not isinstance(data["h5"], str) or not isinstance(data["h5_sel"], str):
            raise RunConfigError("'h5' and 'h5_sel' in config must be strings")

        mult_cuts = _load_mult_cuts(data["mult_cuts"])
        if not isinstance(data["sel_exprs"], list):
            raise RunConfigError("'sel_exprs' in config must be a list")
        for i, expr in enumerate(data["sel_exprs"]):
            if not isinstance(expr, str):
                raise RunConfigError(
                    f"'sel_exprs[{i}]' in config must be a string, got {type(expr).__name__}"
                )
        sel_exprs = list(data["sel_exprs"])
        histograms = [HistogramConfig.from_dict(h) for h in data["histograms"]]
        selections = [SelectionConfig.from_dict(s) for s in data["selections"]]

        cfg = cls(
            energy=data["energy"],
            detector=data["detector"],
            observable=data["observable"],
            bins=data["bins"],
            min=data["min"],
            max=data["max"],
            target=data["target"],
            h5=data["h5"],
            h5_sel=data["h5_sel"],
            mult_cuts=mult_cuts,
            sel_exprs=sel_exprs,
            histograms=histograms,
            selections=selections,
        )

        expected_h5_sel = cfg.compute_h5_sel()
        if data["h5_sel"] != expected_h5_sel:
            raise RunConfigError(
                f"'h5_sel' in config ({data['h5_sel']}) does not match the value computed "
                f"from energy/detector/mult_cuts/sel_exprs ({expected_h5_sel})"
            )
        expected_h5 = cfg.compute_h5()
        if data["h5"] != expected_h5:
            raise RunConfigError(
                f"'h5' in config ({data['h5']}) does not match the value computed "
                f"from h5_sel/observable/bins/min/max/target ({expected_h5})"
            )

        _validate_nested_digests(cfg)

        return cfg

    @classmethod
    def from_file(cls, path) -> "RunConfig":
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        return {
            "energy": self.energy,
            "detector": self.detector,
            "observable": self.observable,
            "bins": self.bins,
            "min": self.min,
            "max": self.max,
            "target": self.target,
            "h5": self.h5,
            "h5_sel": self.h5_sel,
            "mult_cuts": _dump_mult_cuts(self.mult_cuts),
            "sel_exprs": list(self.sel_exprs),
            "histograms": [h.to_dict() for h in self.histograms],
            "selections": [s.to_dict() for s in self.selections],
        }
