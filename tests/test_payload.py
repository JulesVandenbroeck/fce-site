"""Tests for ``fce_web.payload.build_histogram_payload`` (task B-019).

The missing half of the run -> chart pipe: ``run_analysis`` writes
``output/hist{plot_idx}_{sample}.root`` and stops (``driver.py`` module
docstring); nothing in this repo read those files back until this module.
``build_histogram_payload`` is a pure read: given the output directory and
the histogram identity, it returns a dict that must validate against
``tests.test_api_contract.HISTOGRAM_SCHEMA``.
"""
import os
import shutil

import pytest

from fce_web.engine.driver import run_analysis
from fce_web.engine.runconfig import RunConfig
from fce_web.payload import PayloadError, build_histogram_payload
from fce_web.runs import RunContext
from tests.test_api_contract import ALL_SCHEMA, HISTOGRAM_SCHEMA, _MISSING, _resolve

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_DATASET_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "datasets", "IDEA", "91GeV")
ANALYSIS_CONFIG = os.path.join(REPO_ROOT, "content", "analyses", "zpeak-dilepton.json")

MC_SAMPLES = ("X1", "X2", "X3")
DATA_SAMPLE = "data"

META = {
    "mission": "M-1",
    "detector": "IDEA",
    "energy": "91 GeV",
    "xLabel": "m(l1, l2) [GeV]",
    "processNames": {"X1": "X1: Z->2l", "X2": "X2: Z->2q", "X3": "X3: Z->2l+g"},
}


def _run_fixture_analysis(tmp_path, monkeypatch):
    """Run the real engine against B-018's fixture, output landing in a tmp
    ``FCE_HOME`` -- never the committed fixture tree (B-018 contract note:
    ``analytical_loop.run_physics_loop`` resolves ``get_fce_home()`` with no
    argument, so both the env var and the ``env=`` kwarg must point the same
    place, mirroring ``tests/test_fixture_dataset.py``)."""
    monkeypatch.setenv("FCE_HOME", str(tmp_path))
    dataset_dir = tmp_path / "datasets" / "IDEA" / "91GeV"
    shutil.copytree(FIXTURE_DATASET_DIR, dataset_dir)

    config = RunConfig.from_file(ANALYSIS_CONFIG)
    ctx = RunContext(n_workers=2)
    result = run_analysis(config, ctx, env={"FCE_HOME": str(tmp_path)})
    assert result.processed_any is True, result
    return str(tmp_path)


@pytest.fixture()
def fixture_payload(tmp_path, monkeypatch):
    hdir = _run_fixture_analysis(tmp_path, monkeypatch)
    return build_histogram_payload(hdir, 0, MC_SAMPLES, META, data_sample=DATA_SAMPLE)


# ---------------------------------------------------------------------------
# C1 / C4: schema conformance and array-length parity, reusing the existing
# validator from tests.test_api_contract rather than writing a second one.
# ---------------------------------------------------------------------------

def test_payload_conforms_to_histogram_schema(fixture_payload):
    for path in HISTOGRAM_SCHEMA:
        expected_type, (may_be_missing, may_be_null), _doc_type = ALL_SCHEMA[path]
        for value in _resolve(fixture_payload, path.split(".")):
            if value is _MISSING:
                assert may_be_missing, f"{path} missing but required"
                continue
            if value is None:
                assert may_be_null, f"{path} is null but not nullable"
                continue
            assert isinstance(value, expected_type), (path, value)


def test_counts_length_matches_edges_minus_one(fixture_payload):
    n_bins = len(fixture_payload["edges"]) - 1
    assert len(fixture_payload["data"]) == n_bins
    for sample in fixture_payload["samples"]:
        assert len(sample["counts"]) == n_bins
        # C10: each systUp array must be exactly n_bins long -- docs/api.md:112
        # requires it and docs/api.md:133's band formula divides by these
        # sums, so key *presence* alone (C3, below) is not enough.
        for variation in sample["systUp"].values():
            assert len(variation) == n_bins


# ---------------------------------------------------------------------------
# C3: variations land under systUp, absent (not empty) when there are none.
# Only mc_samples appear in samples[] -- data_sample never does, so this
# test cannot and does not assert anything about it.
# ---------------------------------------------------------------------------

def test_mc_samples_carry_systup(fixture_payload):
    by_name = {s["name"]: s for s in fixture_payload["samples"]}
    for name in MC_SAMPLES:
        assert set(by_name[name]["systUp"]) == {"jec", "lep", "btag"}


# ---------------------------------------------------------------------------
# C5: end-to-end proof -- the X1 distribution peaks at the Z mass.
# ---------------------------------------------------------------------------

def test_x1_distribution_peaks_near_the_z_mass(fixture_payload):
    by_name = {s["name"]: s for s in fixture_payload["samples"]}
    counts = by_name["X1"]["counts"]
    edges = fixture_payload["edges"]
    peak_bin = max(range(len(counts)), key=lambda i: counts[i])
    peak_centre = (edges[peak_bin] + edges[peak_bin + 1]) / 2
    assert abs(peak_centre - 91.2) <= 3.0, peak_centre


# ---------------------------------------------------------------------------
# C6: a missing or truncated output file raises PayloadError, not a
# half-built payload.
# ---------------------------------------------------------------------------

def test_missing_histogram_file_raises_payload_error(tmp_path):
    os.makedirs(os.path.join(tmp_path, "output"), exist_ok=True)
    with pytest.raises(PayloadError):
        build_histogram_payload(str(tmp_path), 0, ("X1",), META, data_sample=DATA_SAMPLE)


def test_truncated_histogram_file_raises_payload_error(tmp_path):
    out_dir = os.path.join(tmp_path, "output")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "hist0_X1.root"), "wb") as f:
        f.write(b"not a root file")
    with pytest.raises(PayloadError):
        build_histogram_payload(str(tmp_path), 0, ("X1",), META, data_sample=DATA_SAMPLE)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
