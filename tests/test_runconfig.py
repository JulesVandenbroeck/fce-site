"""Tests for ``fce_web.engine.runconfig`` -- the ``RunConfig`` loader and its
content-addressed md5 cache keys, ``h5_sel`` and ``h5``.

The digest formula is quoted verbatim from the reference (``ui/graph.py``:1866,
1877, 1881-1884) in B-010's task spec, and this test file recomputes it inline
with ``hashlib.md5`` from the raw fixture values -- never via ``RunConfig``'s
own digest methods -- so the implementation and its verification do not share
a hand.
"""

import copy
import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from fce_web.engine.runconfig import RunConfig, RunConfigError

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "content" / "analyses" / "zpeak-dilepton.json"
)


def _fixture_dict() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def _reference_h5_sel(raw: dict) -> str:
    mult_cuts = [tuple(c) for c in raw["mult_cuts"]]
    mult_h5_base = raw["energy"] + raw["detector"] + str(mult_cuts)
    return hashlib.md5((mult_h5_base + str(raw["sel_exprs"])).encode()).hexdigest()


def _reference_h5(raw: dict) -> str:
    h5_sel = _reference_h5_sel(raw)
    return hashlib.md5(
        (
            h5_sel
            + raw["observable"]
            + raw["bins"]
            + raw["min"]
            + raw["max"]
            + raw["target"]
        ).encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# 1. round-trip
# ---------------------------------------------------------------------------


def test_roundtrip_fixture():
    raw = _fixture_dict()
    cfg = RunConfig.from_dict(copy.deepcopy(raw))
    dumped = cfg.to_dict()

    assert dumped == raw
    assert set(dumped) == {
        "energy", "detector", "observable", "bins", "min", "max", "target",
        "h5", "h5_sel", "mult_cuts", "sel_exprs", "histograms", "selections",
    }


# ---------------------------------------------------------------------------
# 2. digests match the reference formula, computed independently in-test
# ---------------------------------------------------------------------------


def test_digest_h5_sel_matches_reference_formula():
    raw = _fixture_dict()
    cfg = RunConfig.from_dict(copy.deepcopy(raw))

    expected = _reference_h5_sel(raw)
    print(f"h5_sel: ours={cfg.h5_sel} reference-formula={expected}")

    assert cfg.h5_sel == expected


def test_digest_h5_matches_reference_formula():
    raw = _fixture_dict()
    cfg = RunConfig.from_dict(copy.deepcopy(raw))

    expected = _reference_h5(raw)
    print(f"h5: ours={cfg.h5} reference-formula={expected}")

    assert cfg.h5 == expected


# ---------------------------------------------------------------------------
# 3. covered fields change the digest; uncovered fields do not
# ---------------------------------------------------------------------------

COVERED_H5_FIELDS = [
    "energy", "detector", "mult_cuts", "sel_exprs",
    "observable", "bins", "min", "max", "target",
]
COVERED_H5_SEL_FIELDS = ["energy", "detector", "mult_cuts", "sel_exprs"]
UNCOVERED_FIELDS = ["histogram_node_name", "selection_nid"]


def _perturb_covered(cfg: RunConfig, field: str) -> RunConfig:
    if field == "energy":
        return dataclasses.replace(cfg, energy="240 GeV")
    if field == "detector":
        return dataclasses.replace(cfg, detector="CLD")
    if field == "mult_cuts":
        extra = (1, ">=", 0, ">=", "Any", 0, ">=")
        return dataclasses.replace(cfg, mult_cuts=cfg.mult_cuts + [extra])
    if field == "sel_exprs":
        return dataclasses.replace(cfg, sel_exprs=cfg.sel_exprs + ["l1.pt > 999"])
    if field == "observable":
        return dataclasses.replace(cfg, observable="met.pt")
    if field == "bins":
        return dataclasses.replace(cfg, bins="99")
    if field == "min":
        return dataclasses.replace(cfg, min="0.0")
    if field == "max":
        return dataclasses.replace(cfg, max="999.0")
    if field == "target":
        return dataclasses.replace(cfg, target="X1")
    raise ValueError(f"no perturbation defined for {field!r}")


def _perturb_uncovered(cfg: RunConfig, field: str) -> RunConfig:
    if field == "histogram_node_name":
        hists = list(cfg.histograms)
        hists[0] = dataclasses.replace(hists[0], node_name="renamed for test")
        return dataclasses.replace(cfg, histograms=hists)
    if field == "selection_nid":
        sels = list(cfg.selections)
        sels[0] = dataclasses.replace(sels[0], nid=999)
        return dataclasses.replace(cfg, selections=sels)
    raise ValueError(f"no perturbation defined for {field!r}")


@pytest.mark.parametrize("field", COVERED_H5_FIELDS)
def test_covered_field_changes_h5(field):
    cfg = RunConfig.from_dict(_fixture_dict())
    base = cfg.compute_h5()
    perturbed = _perturb_covered(cfg, field)
    assert perturbed.compute_h5() != base


@pytest.mark.parametrize("field", COVERED_H5_SEL_FIELDS)
def test_covered_field_changes_h5_sel(field):
    cfg = RunConfig.from_dict(_fixture_dict())
    base = cfg.compute_h5_sel()
    perturbed = _perturb_covered(cfg, field)
    assert perturbed.compute_h5_sel() != base


@pytest.mark.parametrize("field", UNCOVERED_FIELDS)
def test_uncovered_field_does_not_change_digest(field):
    cfg = RunConfig.from_dict(_fixture_dict())
    base_h5 = cfg.compute_h5()
    base_h5_sel = cfg.compute_h5_sel()
    perturbed = _perturb_uncovered(cfg, field)
    assert perturbed.compute_h5() == base_h5
    assert perturbed.compute_h5_sel() == base_h5_sel


# ---------------------------------------------------------------------------
# 4. string-typed digest inputs stay strings
# ---------------------------------------------------------------------------


def test_digest_inputs_are_strings_at_hash_time():
    cfg = RunConfig.from_dict(_fixture_dict())
    assert isinstance(cfg.energy, str)
    assert isinstance(cfg.detector, str)
    assert isinstance(cfg.bins, str)
    assert isinstance(cfg.min, str)
    assert isinstance(cfg.max, str)
    assert isinstance(cfg.target, str)


def test_bins_as_json_number_is_rejected():
    """The mutation this guards against: coercing ``bins`` with ``int()``
    before hashing. If that coercion is (re)introduced, this fixture (whose
    ``bins`` is deliberately the JSON *number* 50, not the string ``"50"``
    dpg text widgets actually produce) would silently succeed instead of
    being rejected here.
    """
    raw = _fixture_dict()
    raw["bins"] = 50  # JSON number, not a string
    with pytest.raises(RunConfigError, match="must be a string"):
        RunConfig.from_dict(raw)


# ---------------------------------------------------------------------------
# 5. unknown fields are rejected, not silently ignored
# ---------------------------------------------------------------------------


def test_unknown_top_level_field_is_rejected():
    raw = _fixture_dict()
    raw["totallyMadeUp"] = 1
    with pytest.raises(RunConfigError) as exc_info:
        RunConfig.from_dict(raw)
    assert "totallyMadeUp" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 6. from_file loads by path (closes the untested entry point B-011/B-012
#    are told to use)
# ---------------------------------------------------------------------------


def test_from_file_loads_fixture_by_path():
    cfg = RunConfig.from_file(FIXTURE_PATH)
    assert cfg.h5 == "fbb913c18c34530d355fdd949974ac58"
    assert cfg.h5_sel == "c9873a70ca371612fc24cf976ff7fd5c"


# ---------------------------------------------------------------------------
# 7. nested digests (selections[i].h5_sel, selections[i].histograms[j].h5)
#    are validated too -- these, not the top-level h5/h5_sel, are what the
#    engine actually addresses the cache with (engine/analytical_loop.py:
#    68,79,183-186 read sel_cfg["h5_sel"] and hcfg["h5"] out of cfg["selections"],
#    never out of the top-level flattened "histograms" list).
# ---------------------------------------------------------------------------


def test_wrong_nested_selection_h5_sel_is_rejected():
    raw = _fixture_dict()
    raw["selections"][0]["h5_sel"] = "0" * 32
    with pytest.raises(RunConfigError) as exc_info:
        RunConfig.from_dict(raw)
    assert "selections[0]" in str(exc_info.value)
    assert "h5_sel" in str(exc_info.value)


def test_wrong_nested_histogram_h5_is_rejected():
    raw = _fixture_dict()
    raw["selections"][0]["histograms"][0]["h5"] = "2" * 32
    with pytest.raises(RunConfigError) as exc_info:
        RunConfig.from_dict(raw)
    assert "selections[0].histograms[0]" in str(exc_info.value)
    assert "h5" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 8. mult_cuts element types are enforced, not just length and container type
# ---------------------------------------------------------------------------


def test_mult_cuts_element_type_is_enforced():
    """A fixture author writing "2" instead of 2 for the leptons-count slot
    gets a self-consistent-looking config that hashes to a *different*,
    silently-wrong digest (independently reproduced: a68ec19856f3ae17c6736
    691b6bc18d2 instead of c9873a70ca371612fc24cf976ff7fd5c) rather than the
    RunConfigError this test requires.
    """
    raw = _fixture_dict()
    raw["mult_cuts"][0][0] = "2"  # str, must be int
    with pytest.raises(RunConfigError) as exc_info:
        RunConfig.from_dict(raw)
    assert "mult_cuts[0][0]" in str(exc_info.value)
