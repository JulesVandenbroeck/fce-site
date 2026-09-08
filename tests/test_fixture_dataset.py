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

# The 26 branches engine/analytical_loop.py's key filter selects
# (analytical_loop.py:156-159, substring match on "pt"/"eta"/"phi"/"e"/
# "weight"/"btag"/"d0signif"/"z0signif"/"charge") and engine/path_filter.py
# reads by name (path_filter.py:609-643), for every object kind the engine
# knows -- electron, muon, jet, photon -- plus weight/MET_pt/MET_phi. This
# is a *subset* of what the real files (and this fixture, downsampled from
# them byte-for-byte otherwise -- see make_fixture.py) actually carry: the
# real files also have MET_e/MET_eta (unread) and one counter branch per
# object (electron_n, jet_n, muon_n, photon_n) -- the ROOT/uproot structural
# requirement for any variable-length branch, not something read by name.
# Of those four counters, "electron_n" and "jet_n" happen to also match the
# substring filter (they contain the letter "e"); "muon_n" and "photon_n" do
# not. All of this is native to the real production files, unchanged by the
# downsample -- confirmed against the real ~/.fce/datasets/IDEA/91GeV files
# this fixture was cut from.
ENGINE_READ_BRANCHES = {
    "weight", "MET_pt", "MET_phi",
    "electron_pt", "electron_eta", "electron_phi", "electron_e",
    "electron_d0signif", "electron_z0signif",
    "muon_pt", "muon_eta", "muon_phi", "muon_e",
    "muon_d0signif", "muon_z0signif",
    "jet_pt", "jet_eta", "jet_phi", "jet_e", "jet_btag",
    "photon_pt", "photon_eta", "photon_phi", "photon_e",
}

# The exact branch set the fixture files carry: ENGINE_READ_BRANCHES, plus
# MET_e/MET_eta (present upstream, never read by name) and the four
# structural per-object counters.
FULL_BRANCH_SET = ENGINE_READ_BRANCHES | {
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
    # The engine's own key filter selects a subset of this; confirm the
    # relationship rather than asserting it in prose.
    assert ENGINE_READ_BRANCHES <= branches


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
# into a tmp FCE_HOME -- never into the committed fixture tree.
# ---------------------------------------------------------------------------

def test_run_analysis_completes_against_the_fixture(tmp_path, monkeypatch):
    """``run_analysis``'s ``env`` parameter reaches ``driver._dataset_dir``
    (dataset discovery) but not ``analytical_loop.run_physics_loop``'s own
    cache/output directory, which resolves ``get_fce_home()`` with no
    argument (``analytical_loop.py:272``) and therefore always reads the
    real process environment for where to read/write ``cache/`` and
    ``output/`` -- a real inconsistency between the two (reported in this
    task's PR body as a backlog candidate; out of this task's file scope to
    fix, since ``analytical_loop.py`` is read-only here). ``monkeypatch.setenv``
    closes that gap for this test the same way the ``env`` dict closes it for
    dataset discovery, so both land in the same tmp directory and the
    committed fixture tree is never touched.
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

    fixture_output_dir = os.path.join(FIXTURE_ROOT, "fixtures", "output")
    assert not os.path.exists(fixture_output_dir), (
        f"run_analysis wrote into the committed fixture tree: {fixture_output_dir}"
    )


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


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
