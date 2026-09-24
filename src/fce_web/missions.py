"""Mission loading, startup validation, and objective evaluation (task B-031).

Mission definitions live in ``content/missions/*.yaml`` and are loaded once at
startup (``fce_web.app.create_app``), never at request time -- adding a
mission must never require editing Python (``.claude/backend/CLAUDE.md`` §7).
A malformed file fails loudly, naming the file and the offending field, so a
mission author gets an immediate answer rather than a silent misparse.

``evaluate()`` is the other half: given a loaded mission and a finished run's
histogram payload (``fce_web.payload.build_histogram_payload``'s shape), it
decides whether the run met the mission's objective. It is a pure function --
no I/O, no engine access -- so B-032 can call it straight off ``/result``.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import yaml

from fce_web.graph import PALETTE_KINDS, _OBS_MODES as OBSERVABLE_MODES

__all__ = ["Mission", "MissionError", "load_missions", "evaluate"]

_REQUIRED_FIELDS = {
    "id", "order", "title", "brief", "dataset", "cards",
    "observable_modes", "objective", "hints", "success",
}
_DATASET_FIELDS = {"energy", "detector"}
_OBJECTIVE_TYPES = {"peak_position", "none"}
_PEAK_POSITION_FIELDS = {"sample", "target", "tolerance"}


class MissionError(ValueError):
    """A mission file failed to load or validate. The message always names
    the file and the field responsible, so a mistake in authored content
    (not code) is diagnosable from the startup error alone."""


@dataclass(frozen=True)
class Mission:
    """One validated mission, as declared in a ``content/missions/*.yaml``
    file. Immutable -- loaded once at startup and shared read-only after."""

    id: str
    order: int
    title: str
    brief: str
    dataset: Dict[str, str]
    cards: List[str]
    observable_modes: List[str]
    objective: Dict[str, Any]
    hints: List[str]
    success: str


def _fail(path: str, field: str, why: str) -> None:
    raise MissionError(f"{path}: field {field!r} {why}")


def _require_str(path: str, field: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        _fail(path, field, "must be a non-empty string")
    return value


def _validate_objective(path: str, objective: Any) -> Dict[str, Any]:
    if not isinstance(objective, dict) or "type" not in objective:
        _fail(path, "objective", "must be a mapping with a 'type'")
    obj_type = objective["type"]
    if obj_type not in _OBJECTIVE_TYPES:
        _fail(path, "objective.type", f"must be one of {sorted(_OBJECTIVE_TYPES)}, got {obj_type!r}")

    extra = set(objective) - {"type"}
    if obj_type == "none":
        if extra:
            _fail(path, "objective", "type 'none' takes no other fields")
        return {"type": "none"}

    if extra != _PEAK_POSITION_FIELDS:
        _fail(path, "objective", f"type 'peak_position' needs exactly {sorted(_PEAK_POSITION_FIELDS)}")
    _require_str(path, "objective.sample", objective["sample"])
    for key in ("target", "tolerance"):
        value = objective[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            _fail(path, f"objective.{key}", "must be a number")
    return dict(objective)


def _validate_mission(path: str, raw: Any) -> Mission:
    if not isinstance(raw, dict):
        _fail(path, "<root>", "must be a mapping")

    unknown = set(raw) - _REQUIRED_FIELDS
    if unknown:
        _fail(path, sorted(unknown)[0], "is not a recognised field")
    missing = _REQUIRED_FIELDS - set(raw)
    if missing:
        _fail(path, sorted(missing)[0], "is required")

    mission_id = _require_str(path, "id", raw["id"])
    order = raw["order"]
    if isinstance(order, bool) or not isinstance(order, int):
        _fail(path, "order", "must be an integer")
    title = _require_str(path, "title", raw["title"])
    brief = _require_str(path, "brief", raw["brief"])
    success = _require_str(path, "success", raw["success"])

    dataset = raw["dataset"]
    if not isinstance(dataset, dict) or set(dataset) != _DATASET_FIELDS:
        _fail(path, "dataset", f"must have exactly the fields {sorted(_DATASET_FIELDS)}")
    for key in _DATASET_FIELDS:
        _require_str(path, f"dataset.{key}", dataset[key])

    cards = raw["cards"]
    if not isinstance(cards, list) or not cards:
        _fail(path, "cards", "must be a non-empty list")
    for kind in cards:
        if kind not in PALETTE_KINDS:
            _fail(path, "cards", f"unknown card kind {kind!r}, must be one of {PALETTE_KINDS}")

    modes = raw["observable_modes"]
    if not isinstance(modes, list) or not modes:
        _fail(path, "observable_modes", "must be a non-empty list")
    for mode in modes:
        if mode not in OBSERVABLE_MODES:
            _fail(path, "observable_modes", f"unknown observable mode {mode!r}, must be one of {OBSERVABLE_MODES}")

    objective = _validate_objective(path, raw["objective"])

    hints = raw["hints"]
    if not isinstance(hints, list) or not all(isinstance(h, str) and h for h in hints):
        _fail(path, "hints", "must be a list of non-empty strings")

    return Mission(
        id=mission_id,
        order=order,
        title=title,
        brief=brief,
        dataset=dict(dataset),
        cards=list(cards),
        observable_modes=list(modes),
        objective=objective,
        hints=list(hints),
        success=success,
    )


def load_missions(content_dir: str) -> Dict[str, Mission]:
    """Load and validate every ``*.yaml`` file in *content_dir*.

    Raises :class:`MissionError`, naming the offending file and field, on any
    unknown/missing field, unknown card kind or observable mode, unknown
    objective type, or a duplicate ``id``/``order`` across files. Files are
    read in sorted order so a duplicate is always reported against the
    second file alphabetically, not arbitrarily.
    """
    missions: Dict[str, Mission] = {}
    orders: Dict[int, str] = {}
    for path in sorted(glob.glob(os.path.join(content_dir, "*.yaml"))):
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        mission = _validate_mission(path, raw)
        if mission.id in missions:
            _fail(path, "id", f"duplicate mission id {mission.id!r}")
        if mission.order in orders:
            _fail(path, "order", f"duplicate order {mission.order!r} (already used by {orders[mission.order]!r})")
        missions[mission.id] = mission
        orders[mission.order] = mission.id
    return missions


def _sample_histogram(payload: Dict[str, Any], sample: str) -> Tuple[List[float], List[float]]:
    """The named sample's ``(counts, edges)`` out of a histogram payload
    (``docs/api.md``'s histogram payload). ``"data"`` is the payload's
    top-level pseudo-data array; any other name is looked up by ``name`` in
    ``samples[]``. Returns ``([], edges)`` if the sample is not present."""
    edges = payload.get("edges") or []
    if sample == "data":
        return payload.get("data") or [], edges
    for entry in payload.get("samples") or []:
        if entry.get("name") == sample:
            return entry.get("counts") or [], edges
    return [], edges


def evaluate(mission: Mission, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Decide whether *payload* (a finished run's histogram payload) meets
    *mission*'s objective. Pure: no I/O, no engine access.

    Returns ``{"met": bool, "value": float | None, "message": str}``.
    ``value`` is the peak position found, when there is one to report.
    """
    objective = mission.objective
    if objective["type"] != "peak_position":
        return {"met": False, "value": None, "message": "This mission has no automatic objective yet."}

    sample = objective["sample"]
    counts, edges = _sample_histogram(payload, sample)
    if not counts or len(edges) < 2 or not any(counts):
        return {
            "met": False,
            "value": None,
            "message": f"No histogram for sample {sample!r} yet -- run the analysis first.",
        }

    modal_bin = max(range(len(counts)), key=lambda i: counts[i])
    value = (edges[modal_bin] + edges[modal_bin + 1]) / 2.0
    target = objective["target"]
    tolerance = objective["tolerance"]
    met = abs(value - target) <= tolerance
    if met:
        message = f"Peak found at {value:.1f} GeV -- within {tolerance:g} GeV of {target:g} GeV."
    else:
        message = f"Your peak is at {value:.1f} GeV, not close enough to {target:g} GeV yet."
    return {"met": met, "value": value, "message": message}
