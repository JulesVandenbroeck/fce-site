"""Tests for the committed fixture dataset at ``tests/fixtures/datasets/IDEA/91GeV/``
(task B-018).

Runs entirely offline against the already-committed fixture -- unlike
``tests/fixtures/make_fixture.py``, which needs the network and the real
dataset to (re)build it. See that module's docstring for why the split.
"""
import os
import shutil

import numpy as np
import pytest
import uproot

from fce_web.engine.driver import run_analysis
from fce_web.engine.runconfig import RunConfig
from fce_web.runs import RunContext

FIXTURE_ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(FIXTURE_ROOT, "fixtures", "datasets", "IDEA", "91GeV")
ANALYSIS_CONFIG = os.path.join(
    os.path.dirname(FIXTURE_ROOT), "content", "analyses", "zpeak-dilepton.json"
)

# The 24 branches engine/analytical_loop.py's key filter selects
# (analytical_loop.py:156-159, substring match on "pt"/"eta"/"phi"/"e"/
# "weight"/"btag"/"d0signif"/"z0signif"/"charge") and engine/path_filter.py
# reads by name (path_filter.py:609-643), for every object kind the engine
# knows -- electron, muon, jet, photon -- plus weight/MET_pt/MET_phi, plus
# the 6 more the fixture also carries but the engine never reads by name:
# MET_e/MET_eta (present upstream, unread) and the four structural
# per-object counters (electron_n, jet_n, muon_n, photon_n -- the ROOT/
# uproot requirement for any variable-length branch). All of this is native
# to the real production files, unchanged by the downsample -- confirmed
# against the real ~/.fce/datasets/IDEA/91GeV files this fixture was cut
# from.
FULL_BRANCH_SET = {
    "weight", "MET_pt", "MET_phi",
    "electron_pt", "electron_eta", "electron_phi", "electron_e",
    "electron_d0signif", "electron_z0signif",
    "muon_pt", "muon_eta", "muon_phi", "muon_e",
    "muon_d0signif", "muon_z0signif",
    "jet_pt", "jet_eta", "jet_phi", "jet_e", "jet_btag",
    "photon_pt", "photon_eta", "photon_phi", "photon_e",
    "MET_e", "MET_eta", "electron_n", "muon_n", "jet_n", "photon_n",
}

SAMPLES = ("X1", "X2", "X3", "data")


# ---------------------------------------------------------------------------
# Criterion 1: exact branch set.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sample", SAMPLES)
def test_branch_set_matches_the_real_fixture_schema(sample):
    with uproot.open(os.path.join(DATASET_DIR, f"{sample}.root")) as f:
        branches = set(f["ntuple"].keys())
    assert branches == FULL_BRANCH_SET, branches


# ---------------------------------------------------------------------------
# Criterion 2: exactly X1, X2, X3, data -- no X4/X5.
# ---------------------------------------------------------------------------

def test_sample_set_is_x1_x2_x3_data_only():
    present = {f[:-len(".root")] for f in os.listdir(DATASET_DIR) if f.endswith(".root")}
    assert present == set(SAMPLES), present


# ---------------------------------------------------------------------------
# Criterion 3: X1's dilepton mass peaks at the Z mass.
# ---------------------------------------------------------------------------

def _leading_two_lepton_mass(path: str) -> np.ndarray:
    """m(l1, l2) for the two highest-pt leptons (electron or muon) in every
    event that has at least two, computed directly from the fixture file --
    independent of the engine, per the criterion's own check.
    """
    with uproot.open(path) as f:
        arrs = f["ntuple"].arrays(
            ["electron_pt", "electron_eta", "electron_phi", "electron_e",
             "muon_pt", "muon_eta", "muon_phi", "muon_e"],
            library="np",
        )
    masses = []
    for i in range(len(arrs["electron_pt"])):
        leptons = []
        for kind in ("electron", "muon"):
            pt, eta = arrs[f"{kind}_pt"][i], arrs[f"{kind}_eta"][i]
            phi, e = arrs[f"{kind}_phi"][i], arrs[f"{kind}_e"][i]
            for j in range(len(pt)):
                leptons.append((pt[j], eta[j], phi[j], e[j]))
        if len(leptons) < 2:
            continue
        leptons.sort(key=lambda lep: -lep[0])
        (pt1, eta1, phi1, e1), (pt2, eta2, phi2, e2) = leptons[0], leptons[1]
        px = pt1 * np.cos(phi1) + pt2 * np.cos(phi2)
        py = pt1 * np.sin(phi1) + pt2 * np.sin(phi2)
        pz = pt1 * np.sinh(eta1) + pt2 * np.sinh(eta2)
        e_tot = e1 + e2
        m2 = e_tot ** 2 - px ** 2 - py ** 2 - pz ** 2
        masses.append(np.sqrt(max(m2, 0.0)))
    return np.array(masses)


def test_x1_dilepton_mass_peaks_within_3gev_of_the_z_mass():
    masses = _leading_two_lepton_mass(os.path.join(DATASET_DIR, "X1.root"))
    assert len(masses) > 100, "too few X1 events with >= 2 leptons to test a peak"
    counts, edges = np.histogram(masses, bins=60, range=(60.0, 120.0))
    modal_bin_centre = (edges[np.argmax(counts)] + edges[np.argmax(counts) + 1]) / 2
    assert abs(modal_bin_centre - 91.2) <= 3.0, modal_bin_centre


# ---------------------------------------------------------------------------
# Criterion 4: X3's dilepton mass sits below the peak.
# ---------------------------------------------------------------------------

def test_x3_dilepton_mass_sits_below_the_z_peak():
    masses = _leading_two_lepton_mass(os.path.join(DATASET_DIR, "X3.root"))
    assert len(masses) > 100, "too few X3 events with >= 2 leptons to test the tail"
    counts, edges = np.histogram(masses, bins=60, range=(60.0, 120.0))
    modal_bin_centre = (edges[np.argmax(counts)] + edges[np.argmax(counts) + 1]) / 2
    assert modal_bin_centre < 91.2 - 3.0, modal_bin_centre


# ---------------------------------------------------------------------------
# Criterion 5: run_analysis completes against the fixture, writing output/
# into a tmp FCE_HOME.
# ---------------------------------------------------------------------------

def test_run_analysis_completes_against_the_fixture(tmp_path, monkeypatch):
    """``run_analysis`` completes against a copy of the fixture in a tmp
    ``FCE_HOME``, writing ``output/hist0_<sample>.root`` per sample.
    ``monkeypatch.setenv`` covers ``analytical_loop.run_physics_loop``'s own
    cache/output resolution, which forwards ``env`` alongside the ``env``
    dict already given to ``run_analysis`` for dataset discovery.
    """
    monkeypatch.setenv("FCE_HOME", str(tmp_path))
    tmp_dataset_dir = tmp_path / "datasets" / "IDEA" / "91GeV"
    shutil.copytree(DATASET_DIR, tmp_dataset_dir)

    config = RunConfig.from_file(ANALYSIS_CONFIG)
    ctx = RunContext(n_workers=2)
    result = run_analysis(config, ctx, env={"FCE_HOME": str(tmp_path)})

    assert result.processed_any is True, result
    for sample in SAMPLES:
        out_file = tmp_path / "output" / f"hist0_{sample}.root"
        assert out_file.exists(), f"missing {out_file}"


# ---------------------------------------------------------------------------
# Criterion 6: total fixture size <= 5 MB.
# ---------------------------------------------------------------------------

def test_fixture_size_is_at_most_5mb():
    total = sum(
        os.path.getsize(os.path.join(root, name))
        for root, _, files in os.walk(os.path.join(FIXTURE_ROOT, "fixtures"))
        for name in files
    )
    assert total <= 5 * 1024 * 1024, total


# ---------------------------------------------------------------------------
# B-025: MC weight scaled by N_source/2000; "data" left at unit weight.
#
# Expected values computed independently of make_fixture.py: the source
# file's original per-event weight (constant across its sample -- read
# directly from ~/.fce/datasets/IDEA/91GeV before this task's change) times
# N_source/2000, where N_source is that sample's ``tr.num_entries`` in the
# same source file (960403/652809/325794 for X1/X2/X3 -- see PR body).
# ---------------------------------------------------------------------------

EXPECTED_WEIGHT = {
    "X1": 0.008768 * (960403 / 2000),
    "X2": 0.032768 * (652809 / 2000),
    "X3": 0.004492 * (325794 / 2000),
    "data": 1.0,
}


@pytest.mark.parametrize("sample", SAMPLES)
def test_fixture_weight_is_scaled_to_the_2000_event_slice(sample):
    with uproot.open(os.path.join(DATASET_DIR, f"{sample}.root")) as f:
        w = f["ntuple"]["weight"].array(library="np")
    assert w.min() == w.max(), "fixture weight is expected constant per sample"
    assert w[0] == pytest.approx(EXPECTED_WEIGHT[sample], rel=1e-6), (sample, w[0])


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
