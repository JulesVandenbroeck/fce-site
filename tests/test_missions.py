"""Tests for ``fce_web.missions`` (task B-031): startup loading/validation
and ``evaluate()``'s objective logic.

Kept to one check per behaviour (`.claude/shared/CLAUDE.md` §6) rather than a
suite: one that the real ``content/missions/*.yaml`` load cleanly and produce
``M-1``'s peak-position verdict on a real-shaped payload, one that a
malformed field fails loudly naming it, and one mutation on ``evaluate``'s
tolerance check proving the assertion actually watches something.
"""
import os

import pytest

from fce_web.missions import Mission, MissionError, evaluate, load_missions

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


# ---------------------------------------------------------------------------
# Loading the real content/missions/*.yaml
# ---------------------------------------------------------------------------

def test_real_missions_load_and_validate():
    missions = load_missions(MISSIONS_DIR)
    assert set(missions) == {"M-1", "M-2"}
    assert missions["M-1"].order == 1
    assert missions["M-2"].order == 2
    assert missions["M-1"].objective["type"] == "peak_position"
    assert missions["M-2"].objective == {"type": "none"}


_VALID_RAW = {
    "id": "M-9", "order": 9, "title": "t", "brief": "b", "success": "s",
    "dataset": {"energy": "91 GeV", "detector": "IDEA"},
    "cards": ["Histogram"],
    "observable_modes": ["ObsVectorSum"],
    "objective": {"type": "none"},
    "hints": ["h"],
}


@pytest.mark.parametrize(
    "override, bad_field",
    [
        ({"_drop": "order"}, "order"),  # missing required field
        ({"cards": ["NotACard"]}, "cards"),
        ({"objective": {"type": "not-a-real-type"}}, "objective.type"),
    ],
)
def test_malformed_mission_fails_naming_field(tmp_path, override, bad_field):
    import yaml

    raw = dict(_VALID_RAW)
    raw.pop(override.pop("_drop", None), None)
    raw.update(override)
    bad_file = tmp_path / "m-9.yaml"
    bad_file.write_text(yaml.safe_dump(raw))
    with pytest.raises(MissionError) as exc_info:
        load_missions(str(tmp_path))
    assert str(bad_file) in str(exc_info.value)
    assert bad_field in str(exc_info.value)


def test_duplicate_order_fails_naming_field(tmp_path):
    import yaml

    common = {
        "id": "M-A", "title": "t", "brief": "b", "success": "s",
        "dataset": {"energy": "91 GeV", "detector": "IDEA"},
        "cards": ["Histogram"],
        "observable_modes": ["ObsVectorSum"],
        "objective": {"type": "none"},
        "hints": ["h"],
    }
    (tmp_path / "a.yaml").write_text(yaml.safe_dump({**common, "id": "M-A", "order": 1}))
    (tmp_path / "b.yaml").write_text(yaml.safe_dump({**common, "id": "M-B", "order": 1}))
    with pytest.raises(MissionError, match="order"):
        load_missions(str(tmp_path))


# ---------------------------------------------------------------------------
# evaluate() -- C3/C4
# ---------------------------------------------------------------------------

M1 = load_missions(MISSIONS_DIR)["M-1"]
NONE_MISSION = load_missions(MISSIONS_DIR)["M-2"]


def test_evaluate_met_when_peak_within_tolerance():
    # Peak at 90-93 GeV, target 91.19 +/- 3.0 -> met.
    result = evaluate(M1, _peak_payload(90.0))
    assert result["met"] is True
    assert 90.0 <= result["value"] <= 93.0
    assert "message" in result and result["message"]


def test_evaluate_not_met_when_peak_shifted():
    # Peak at 60-63 GeV, far outside tolerance -> not met, but a value and a
    # helpful (non-error) message are still reported.
    result = evaluate(M1, _peak_payload(60.0))
    assert result["met"] is False
    assert result["value"] is not None
    assert "60" in result["message"] or "61" in result["message"]


def test_evaluate_no_data_sample_reports_not_met_with_hint():
    result = evaluate(M1, {"edges": [0.0, 1.0], "samples": [], "data": []})
    assert result == {
        "met": False,
        "value": None,
        "message": "No histogram for sample 'data' yet -- run the analysis first.",
    }


def test_evaluate_objective_none_never_met():
    result = evaluate(NONE_MISSION, _peak_payload(90.0))
    assert result["met"] is False
    assert result["value"] is None


def test_evaluate_tolerance_check_is_load_bearing(monkeypatch):
    """Mutation test (`.claude/backend/CLAUDE.md` §2): widen the tolerance so
    an off-peak run would wrongly pass, and confirm the assertion catches it
    -- proving `test_evaluate_not_met_when_peak_shifted` actually exercises
    the tolerance comparison rather than always returning False."""
    mutant = Mission(**{**M1.__dict__, "objective": {**M1.objective, "tolerance": 1000.0}})
    result = evaluate(mutant, _peak_payload(60.0))
    assert result["met"] is True  # the mutant now (wrongly) accepts anything
