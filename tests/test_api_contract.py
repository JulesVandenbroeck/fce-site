"""Executable checker for the histogram / cutflow / fit contract in ``docs/api.md``.

B-004 (cycle 2). This module holds the contract as Python data (``HISTOGRAM_SCHEMA``,
``CUTFLOW_SCHEMA``, ``FIT_SCHEMA``) and checks two independent things against it:

1. that every field the schema declares is actually documented in ``docs/api.md`` --
   the anti-drift bolt between the prose contract and this checker.
2. that ``docs/design-explorations/payload.json`` -- the concrete instance the design
   role built for D-003 -- satisfies that contract: required fields present, types
   correct, ``null`` accepted only where the schema marks a field nullable, and the
   array-length relationships the frontend chart code relies on.

The systematics-band formula (semantics 1 in ``docs/api.md``) is re-implemented here
from the document's prose, independently of ``docs/design-explorations/plot.js`` and
``docs/design-explorations/verify.py`` -- transcribing either would let a shared bug
hide from both.

**Doc-drift detection is row-anchored, not a bare-word search.** ``_documented_paths``
only counts a field as documented when it is the single backticked token in the first
cell of a table row inside a ``<!-- schema-table:start/end -->`` block in
``docs/api.md`` -- the actual shape of the field-reference tables. A cycle-1 version of
this checker used ``\\b<name>\\b`` over the whole document, which a cycle-2 review showed
was blind for five of the schema's leaf names (``data``, ``name``, ``samples``,
``edges``, ``stages``) because the bare word survives in unrelated prose after its
documenting row is deleted. ``test_removing_field_row_makes_documented_check_fail`` is a
meta-test, parametrized over every schema path, that proves this checker is falsifiable
for every one of them, permanently, rather than relying on a hand-picked transcript.

**Every mutation in this file's test suite runs by monkeypatching a module attribute,
never by editing a tracked file.** ``API_MD_TEXT`` and ``_raw_payload_text`` are the two
seams: a test's ``monkeypatch`` fixture rebinds one of them for the duration of that
test only, pytest itself restores it afterwards, and no file on disk is ever touched.
(An earlier cycle's PR body demonstrated mutations with ``sed -i`` against
``docs/api.md`` and against this file's own ``_compute_band`` -- that method is
forbidden by ``.claude/backend/CLAUDE.md`` and is not used here.)
"""
import json
import math
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
API_MD = REPO_ROOT / "docs" / "api.md"
PAYLOAD_PATH = REPO_ROOT / "docs" / "design-explorations" / "payload.json"

# The two mutation seams. Both are read once at import time and read again on
# every use through a function/attribute lookup, so a test's `monkeypatch`
# fixture can rebind either for the duration of a single test with no file
# ever touched. This is data cached from disk, not the kind of module-level
# *mutable application state* `.claude/shared/CLAUDE.md` forbids in `engine/`
# -- it is test fixture data, and it is rebound only inside `monkeypatch`'s
# automatically-reverted scope.
API_MD_TEXT = API_MD.read_text(encoding="utf-8")


def _raw_payload_text():
    return PAYLOAD_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# The contract, as data. Keys are dotted paths matching exactly how each
# field's own row spells it in docs/api.md's field-reference tables.
# ---------------------------------------------------------------------------

HISTOGRAM_SCHEMA = {
    "meta": (dict, False),
    "meta.mission": (str, False),
    "meta.detector": (str, False),
    "meta.energy": (str, False),
    "meta.xLabel": (str, False),
    "meta.processNames": (dict, False),
    "edges": (list, False),
    "lumiUnc": ((int, float), False),
    "systSources": (list, False),
    "samples": (list, False),
    "samples[].name": (str, False),
    "samples[].counts": (list, False),
    "samples[].weightsSquared": (list, True),
    "samples[].systUp": (dict, False),
    "samples[].systUp.jec": (list, False),
    "samples[].systUp.lep": (list, False),
    "samples[].systUp.btag": (list, False),
    "data": (list, False),
}

CUTFLOW_SCHEMA = {
    "cutflow.stages": (list, False),
    "cutflow.samples": (list, False),
    "cutflow.counts": (dict, False),
    "cutflow.totalRaw": (int, False),
    "cutflow.efficiencyPct": (list, False),
}

FIT_SCHEMA = {
    "fit.mu": ((int, float), True),
    "fit.muErr": ((int, float), True),
    "fit.significanceZ": ((int, float), True),
    "fit.method": (str, True),
    "fit.thresholds": (dict, False),
    "fit.thresholds.evidence": ((int, float), False),
    "fit.thresholds.discovery": ((int, float), False),
}

ALL_SCHEMA_PATHS = sorted(set(HISTOGRAM_SCHEMA) | set(CUTFLOW_SCHEMA) | set(FIT_SCHEMA))


# ---------------------------------------------------------------------------
# Doc-drift detection: row-anchored, not a bare-word search.
# ---------------------------------------------------------------------------

_SCHEMA_TABLE_BLOCK_RE = re.compile(
    r"<!-- schema-table:start -->(.*?)<!-- schema-table:end -->", re.DOTALL
)
_SCHEMA_TABLE_ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|", re.MULTILINE)


def _documented_paths(doc_text):
    """Dotted field paths documented in a schema-table row of ``doc_text``."""
    paths = set()
    for block in _SCHEMA_TABLE_BLOCK_RE.findall(doc_text):
        for row in _SCHEMA_TABLE_ROW_RE.findall(block):
            paths.add(row)
    return paths


def _remove_row_for_path(doc_text, path):
    """``doc_text`` with the schema-table row documenting ``path`` deleted."""
    pattern = re.compile(rf"^\|\s*`{re.escape(path)}`\s*\|.*\n", re.MULTILINE)
    mutated, n = pattern.subn("", doc_text)
    assert n == 1, f"expected exactly one schema-table row for {path!r}, found {n}"
    return mutated


def _append_orphan_row(doc_text):
    """``doc_text`` with one extra schema-table row for a field no schema declares."""
    marker = "<!-- schema-table:start -->\n| Field | Type | Nullable | Meaning |\n|---|---|---|---|\n"
    orphan_row = "| `totallyMadeUp.field` | string | no | not in any schema |\n"
    assert marker in doc_text, "no schema-table header found to inject an orphan row after"
    return doc_text.replace(marker, marker + orphan_row, 1)


def _check_field_documented_in_source(path):
    assert path in _documented_paths(API_MD_TEXT), (
        f"schema field {path!r} is not documented in a schema-table row of docs/api.md"
    )


def _check_no_orphan_documented_paths():
    documented = _documented_paths(API_MD_TEXT)
    orphans = documented - set(ALL_SCHEMA_PATHS)
    assert not orphans, (
        f"docs/api.md documents field(s) with no matching schema entry: {sorted(orphans)}"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def payload():
    return json.loads(_raw_payload_text())


# ---------------------------------------------------------------------------
# Checkers -- plain functions wrapped by a `test_*` below.
# ---------------------------------------------------------------------------

def _check_top_level_fields_present(payload):
    required = {"meta", "edges", "lumiUnc", "systSources", "samples", "data", "cutflow", "fit"}
    assert required <= set(payload.keys()), (
        f"missing top-level field(s): {sorted(required - set(payload.keys()))}"
    )


def _check_meta_fields_typed(payload):
    meta = payload["meta"]
    assert (
        isinstance(meta.get("mission"), str)
        and isinstance(meta.get("detector"), str)
        and isinstance(meta.get("energy"), str)
        and isinstance(meta.get("xLabel"), str)
        and isinstance(meta.get("processNames"), dict)
    ), f"meta field(s) missing or wrong type: {meta!r}"


def _check_sample_array_lengths_coherent(payload):
    n_bins = len(payload["edges"]) - 1
    for sample in payload["samples"]:
        assert len(sample["counts"]) == n_bins, (
            f"sample {sample.get('name')!r} counts length {len(sample['counts'])} != n_bins {n_bins}"
        )
        w2 = sample.get("weightsSquared")
        assert w2 is None or len(w2) == n_bins, (
            f"sample {sample.get('name')!r} weightsSquared length {len(w2)} != n_bins {n_bins}"
        )
        for src, series in sample.get("systUp", {}).items():
            assert len(series) == n_bins, (
                f"sample {sample.get('name')!r} systUp[{src!r}] length {len(series)} != n_bins {n_bins}"
            )


def _check_data_length_matches_bins(payload):
    n_bins = len(payload["edges"]) - 1
    assert len(payload["data"]) == n_bins, (
        f"data length {len(payload['data'])} != n_bins {n_bins}"
    )


def _check_cutflow_counts_cover_stages_times_samples(payload):
    cutflow = payload["cutflow"]
    stages = cutflow["stages"]
    samples = cutflow["samples"]
    counts = cutflow["counts"]
    ok = set(counts.keys()) == set(stages) and all(
        set(counts[stage].keys()) >= set(samples) for stage in stages
    )
    assert ok, (
        f"cutflow.counts does not cover stages x samples (every stage must carry at "
        f"least every sample; extra samples are allowed): "
        f"stages={stages}, samples={samples}, counts keys={list(counts.keys())}"
    )


def _check_cutflow_efficiency_length_matches_stages(payload):
    cutflow = payload["cutflow"]
    assert len(cutflow["efficiencyPct"]) == len(cutflow["stages"]), (
        f"efficiencyPct length {len(cutflow['efficiencyPct'])} != "
        f"stages length {len(cutflow['stages'])}"
    )


def _check_cutflow_efficiency_starts_at_100(payload):
    assert payload["cutflow"]["efficiencyPct"][0] == 100.0, (
        f"efficiencyPct[0] = {payload['cutflow']['efficiencyPct'][0]!r}, expected 100.0"
    )


def _check_fit_thresholds_ordered(payload):
    thresholds = payload["fit"]["thresholds"]
    assert thresholds["evidence"] < thresholds["discovery"], (
        f"fit.thresholds.evidence ({thresholds['evidence']}) is not < "
        f"fit.thresholds.discovery ({thresholds['discovery']})"
    )


def _check_fit_nullable_fields_typed(payload):
    """`mu`, `significanceZ`, `muErr` and `method` are all nullable (docs/api.md
    semantics 7 and 8): each must be `None` or the type the schema declares."""
    fit = payload["fit"]
    mu = fit.get("mu")
    sig_z = fit.get("significanceZ")
    mu_err = fit.get("muErr")
    method = fit.get("method")
    ok = (
        (mu is None or isinstance(mu, (int, float)))
        and (sig_z is None or isinstance(sig_z, (int, float)))
        and (mu_err is None or isinstance(mu_err, (int, float)))
        and (method is None or isinstance(method, str))
    )
    assert ok, (
        f"fit.mu, fit.significanceZ, fit.muErr or fit.method has an unexpected type: "
        f"mu={mu!r}, significanceZ={sig_z!r}, muErr={mu_err!r}, method={method!r}"
    )


# ---------------------------------------------------------------------------
# The systematics band, re-implemented from the prose in docs/api.md --
# not imported from docs/design-explorations/plot.js or verify.py.
#
#   frac = sqrt( lumiUnc^2 + sum_src ( (sum_s systUp[s][src] - sum_s counts[s])
#                                       / sum_s counts[s] )^2 )
#   band = sum_s counts[s] * frac
#
# frac forced to 0 where the summed stack is <= 0. Each source's
# `sum_s systUp[s][src]` sums only over the samples that carry that source's
# key -- a sample missing it contributes nothing (not its nominal), and a
# source is skipped entirely only if *no* sample carries it at all. This is
# the partial-presence rule from engine/plotter.py:52-64,112, the opposite of
# the fit's all-or-nothing histosys rule -- see docs/api.md semantics 1 and 2.
# ---------------------------------------------------------------------------

def _compute_band(payload):
    samples = payload["samples"]
    n_bins = len(payload["edges"]) - 1
    lumi_unc = payload["lumiUnc"]

    stack = [0.0] * n_bins
    for sample in samples:
        for i, c in enumerate(sample["counts"]):
            stack[i] += c

    frac2 = [lumi_unc ** 2] * n_bins
    for src in payload["systSources"]:
        summed_up = [0.0] * n_bins
        any_sample_has_source = False
        for sample in samples:
            series = sample.get("systUp", {}).get(src)
            if series is None:
                continue
            any_sample_has_source = True
            for i, v in enumerate(series):
                summed_up[i] += v
        if not any_sample_has_source:
            continue
        for i in range(n_bins):
            if stack[i] > 0:
                delta = (summed_up[i] - stack[i]) / stack[i]
                frac2[i] += delta ** 2

    frac = [math.sqrt(frac2[i]) if stack[i] > 0 else 0.0 for i in range(n_bins)]
    band = [stack[i] * frac[i] for i in range(n_bins)]
    return stack, frac, band


def _check_band_is_finite(payload):
    _, _, band = _compute_band(payload)
    assert all(math.isfinite(b) for b in band), f"band has non-finite entries: {band}"


def _check_band_is_nonnegative(payload):
    _, _, band = _compute_band(payload)
    assert all(b >= 0.0 for b in band), f"band has negative entries: {band}"


def _check_band_frac_at_least_lumi_unc(payload):
    stack, frac, _ = _compute_band(payload)
    lumi_unc = payload["lumiUnc"]
    ok = all(f >= lumi_unc - 1e-12 for s, f in zip(stack, frac) if s > 0)
    assert ok, f"frac fell below lumiUnc ({lumi_unc}) in a bin with positive stack: {list(zip(stack, frac))}"


def _check_band_frac_zero_where_stack_zero(payload):
    stack, frac, _ = _compute_band(payload)
    ok = all(f == 0.0 for s, f in zip(stack, frac) if s == 0)
    assert ok, f"frac is nonzero in a bin with zero stack: {list(zip(stack, frac))}"


# ---------------------------------------------------------------------------
# Tests -- thin wrappers over the checkers above, run against the real files.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ALL_SCHEMA_PATHS)
def test_documented_schema_field_appears_in_api_md(path):
    _check_field_documented_in_source(path)


def test_no_orphan_schema_table_rows():
    _check_no_orphan_documented_paths()


@pytest.mark.parametrize("path", ALL_SCHEMA_PATHS)
def test_removing_field_row_makes_documented_check_fail(path, monkeypatch):
    """Falsifiability meta-test. For every schema path, delete its schema-table
    row from an in-memory copy of the doc text, monkeypatch that in for
    `API_MD_TEXT`, and prove `_check_field_documented_in_source` now raises
    naming that exact path. Runs for all of ALL_SCHEMA_PATHS permanently, so
    no one has to hand-pick which fields to demonstrate a mutation on."""
    mutated = _remove_row_for_path(API_MD_TEXT, path)
    monkeypatch.setattr(sys.modules[__name__], "API_MD_TEXT", mutated)
    with pytest.raises(AssertionError, match=re.escape(path)):
        _check_field_documented_in_source(path)


def test_appending_orphan_row_makes_no_orphan_check_fail(monkeypatch):
    """Falsifiability meta-test for the reverse direction: a documented row with
    no schema entry must be caught too."""
    mutated = _append_orphan_row(API_MD_TEXT)
    monkeypatch.setattr(sys.modules[__name__], "API_MD_TEXT", mutated)
    with pytest.raises(AssertionError, match="totallyMadeUp.field"):
        _check_no_orphan_documented_paths()


def test_top_level_fields_present(payload):
    _check_top_level_fields_present(payload)


def test_meta_fields_typed(payload):
    _check_meta_fields_typed(payload)


def test_sample_array_lengths_coherent(payload):
    _check_sample_array_lengths_coherent(payload)


def test_data_length_matches_bins(payload):
    _check_data_length_matches_bins(payload)


def test_cutflow_counts_cover_stages_times_samples(payload):
    _check_cutflow_counts_cover_stages_times_samples(payload)


def test_cutflow_efficiency_length_matches_stages(payload):
    _check_cutflow_efficiency_length_matches_stages(payload)


def test_cutflow_efficiency_starts_at_100(payload):
    _check_cutflow_efficiency_starts_at_100(payload)


def test_fit_thresholds_ordered(payload):
    _check_fit_thresholds_ordered(payload)


def test_fit_nullable_fields_typed(payload):
    _check_fit_nullable_fields_typed(payload)


def test_band_is_finite(payload):
    _check_band_is_finite(payload)


def test_band_is_nonnegative(payload):
    _check_band_is_nonnegative(payload)


def test_band_frac_at_least_lumi_unc_where_stack_positive(payload):
    _check_band_frac_at_least_lumi_unc(payload)


def test_band_frac_zero_where_stack_zero(payload):
    _check_band_frac_zero_where_stack_zero(payload)


def test_band_partial_presence_includes_source_from_samples_that_have_it():
    """Regression guard for the cycle-2 review finding: an earlier `_compute_band`
    dropped a systematic source entirely if *any* one sample lacked it -- the
    fit's rule, not the band's. `engine/plotter.py:52-64,112` sums a source from
    whichever samples carry it and only drops it if *no* sample does. Two
    samples, `A` with a `jec` variation and `B` without one: the source must
    still contribute, computed from `A` alone.

    stack = [10+10, 10+10] = [20, 20]
    summed_up (jec, from A only, B contributes nothing) = [11, 11]
    delta = (11 - 20) / 20 = -0.45  ->  frac = sqrt(0^2 + (-0.45)^2) = 0.45
    """
    payload = {
        "edges": [0.0, 1.0, 2.0],
        "lumiUnc": 0.0,
        "systSources": ["jec"],
        "samples": [
            {"name": "A", "counts": [10.0, 10.0], "systUp": {"jec": [11.0, 11.0]}},
            {"name": "B", "counts": [10.0, 10.0], "systUp": {}},
        ],
    }
    stack, frac, band = _compute_band(payload)
    assert stack == [20.0, 20.0]
    assert frac[0] == pytest.approx(0.45)
    assert frac[1] == pytest.approx(0.45)
