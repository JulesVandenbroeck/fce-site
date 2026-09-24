"""Tests for ``fce_web.missions`` (task B-031): startup loading/validation
and ``evaluate()``'s objective logic.

Ponytail's test rule (`.claude/shared/CLAUDE.md` §6): one check per
behaviour, not a suite. ``test_evaluate_not_met_when_peak_shifted`` is the
load-bearing check on ``evaluate()``'s tolerance comparison -- it goes red if
that comparison is dropped (verified via an in-memory mutation, not a
committed test, per B-031 cycle 2 review F1/F2). The second test covers
``load_missions()`` failing loudly: a malformed field, and an empty
directory (F3), both naming the offender.
"""
import os

import pytest
import yaml

from fce_web.missions import MissionError, evaluate, load_missions

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MISSIONS_DIR = os.path.join(REPO_ROOT, "content", "missions")


def _peak_payload(peak_edge_low: float) -> dict:
    """A histogram payload shaped like ``docs/api.md``'s contract: 50 bins,
    0-150 GeV, with the `data` sample's tallest bin starting at
    *peak_edge_low*."""
    n_bins = 50
    width = 150.0 / n_bins
    edges = [i * width for i in range(n_bins + 1)]
    data = [5] * n_bins
    peak_bin = int(peak_edge_low / width)
    data[peak_bin] = 500
    return {"edges": edges, "samples": [], "data": data}


M1 = load_missions(MISSIONS_DIR)["M-1"]


def test_evaluate_not_met_when_peak_shifted():
    # Peak at 60-63 GeV, far outside M-1's tolerance around 91.19 GeV ->
    # not met, but a value and a helpful (non-error) message are reported.
    result = evaluate(M1, _peak_payload(60.0))
    assert result["met"] is False
    assert result["value"] is not None


def test_malformed_or_empty_mission_dir_fails_naming_the_field(tmp_path):
    # A field that fails validation names both the file and the field.
    raw = {
        "id": "M-9", "title": "t", "brief": "b", "success": "s",
        "dataset": {"energy": "91 GeV", "detector": "IDEA"},
        "cards": ["Histogram"],
        "observable_modes": ["ObsVectorSum"],
        "objective": {"type": "none"},
        "hints": ["h"],
        # "order" deliberately missing
    }
    bad_file = tmp_path / "m-9.yaml"
    bad_file.write_text(yaml.safe_dump(raw))
    with pytest.raises(MissionError) as exc_info:
        load_missions(str(tmp_path))
    assert str(bad_file) in str(exc_info.value)
    assert "order" in str(exc_info.value)

    # An empty directory (no mission files at all, F3) fails naming the
    # directory rather than starting the app with no missions silently.
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(MissionError, match=str(empty_dir)):
        load_missions(str(empty_dir))
