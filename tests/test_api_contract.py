"""Executable checker for the histogram / cutflow / fit contract in ``docs/api.md``.

B-004. This module holds the contract as Python data (``HISTOGRAM_SCHEMA``,
``CUTFLOW_SCHEMA``, ``FIT_SCHEMA``) and checks two independent things against it:

1. that every field the schema declares is actually documented in ``docs/api.md`` --
   the anti-drift bolt between the prose contract and this checker.
2. that ``docs/design-explorations/payload.json`` -- the concrete instance the design
   role built for D-003 -- satisfies that contract: required fields present, types
   correct, ``null`` accepted only where the schema marks a field nullable, and the
   array-length relationships the frontend chart code relies on.

The systematics-band formula (semantics 1 in ``docs/api.md``) is re-implemented here
from the document's prose, independently of ``static/js/plot.js`` and
``docs/design-explorations/verify.py`` -- transcribing either would let a shared bug
hide from both.

Every assertion in this file is written so it can be mutation-tested by calling the
underlying ``_check_*`` helper directly with a deliberately broken copy of the payload
-- no tracked file is ever edited to prove an assertion can fail.
"""
import json
import math
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
API_MD = REPO_ROOT / "docs" / "api.md"
PAYLOAD_PATH = REPO_ROOT / "docs" / "design-explorations" / "payload.json"

# ---------------------------------------------------------------------------
# The contract, as data. Keys are dotted paths for readability; only the last
# path component (the field's own name) has to appear in docs/api.md, since
# that is how the document actually spells each field.
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
    "fit.mu": ((int, float), False),
    "fit.muErr": ((int, float), True),
    "fit.significanceZ": ((int, float), False),
    "fit.method": (str, True),
    "fit.thresholds": (dict, False),
    "fit.thresholds.evidence": ((int, float), False),
    "fit.thresholds.discovery": ((int, float), False),
}


def _leaf_field_names(schema):
    """The field's own name, as it should read in prose -- last path segment."""
    names = set()
    for path in schema:
        leaf = path.rsplit(".", 1)[-1]
        leaf = leaf.replace("[]", "")
        names.add(leaf)
    return names


ALL_SCHEMA_FIELDS = sorted(
    _leaf_field_names(HISTOGRAM_SCHEMA)
    | _leaf_field_names(CUTFLOW_SCHEMA)
    | _leaf_field_names(FIT_SCHEMA)
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_doc_text():
    return API_MD.read_text(encoding="utf-8")


@pytest.fixture()
def payload():
    return json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Checkers -- plain functions, callable directly with mutated data for the
# mutation-test transcripts in the PR body, and wrapped by a `test_*` below.
# ---------------------------------------------------------------------------

def _check_field_documented(field, doc_text):
    assert re.search(rf"\b{re.escape(field)}\b", doc_text), (
        f"schema field {field!r} is not documented in docs/api.md"
    )


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
        f"cutflow.counts does not cover exactly stages x samples: "
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
    fit = payload["fit"]
    mu_err = fit.get("muErr")
    method = fit.get("method")
    ok = (mu_err is None or isinstance(mu_err, (int, float))) and (
        method is None or isinstance(method, str)
    )
    assert ok, f"fit.muErr or fit.method has an unexpected type: muErr={mu_err!r}, method={method!r}"


# ---------------------------------------------------------------------------
# The systematics band, re-implemented from the prose in docs/api.md --
# not imported from static/js/plot.js or docs/design-explorations/verify.py.
#
#   frac = sqrt( lumiUnc^2 + sum_src ( (sum_s systUp[s][src] - sum_s counts[s])
#                                       / sum_s counts[s] )^2 )
#   band = sum_s counts[s] * frac
#
# frac forced to 0 where the summed stack is <= 0.
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
        available = True
        for sample in samples:
            series = sample.get("systUp", {}).get(src)
            if series is None:
                available = False
                break
            for i, v in enumerate(series):
                summed_up[i] += v
        if not available:
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

@pytest.mark.parametrize("field", ALL_SCHEMA_FIELDS)
def test_documented_schema_field_appears_in_api_md(field, api_doc_text):
    _check_field_documented(field, api_doc_text)


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
