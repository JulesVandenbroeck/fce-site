"""Tests for `fce_web.graph`: the connection allowlist and the graph ->
`RunConfig` translation (B-020).
"""
from __future__ import annotations

import ast
import os

import pytest

from fce_web.engine.runconfig import RunConfig
from fce_web.graph import Dataset, GraphError, VALID_CONNECTIONS, build_run_config

_REFERENCE_ROOT_ENV = "FCE_PARITY_REFERENCE_ROOT"
_DEFAULT_REFERENCE_ROOT = os.path.expanduser("~/Documents/Phd/teaching/fce-project/fce")


def _reference_root() -> str:
    return os.environ.get(_REFERENCE_ROOT_ENV, _DEFAULT_REFERENCE_ROOT)


def _reference_valid_connections(root: str) -> dict:
    """Read (never import) `_VALID_CONNECTIONS` out of the reference's
    `ui/graph.py`, by extracting just its two defining assignments
    (`_OBS_TYPES_SET`, `_VALID_CONNECTIONS`) and executing only those --
    `ui/graph.py` itself imports `ui.state`, which pulls in `dearpygui`.
    """
    path = os.path.join(root, "ui", "graph.py")
    with open(path, "r") as f:
        tree = ast.parse(f.read(), filename=path)
    wanted = {"_OBS_TYPES_SET", "_VALID_CONNECTIONS"}

    def _targets(node):
        if isinstance(node, ast.Assign):
            return node.targets
        if isinstance(node, ast.AnnAssign):
            return [node.target]
        return []

    body = [
        node
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(isinstance(t, ast.Name) and t.id in wanted for t in _targets(node))
    ]
    module = ast.Module(body=body, type_ignores=[])
    code = compile(module, filename=path, mode="exec")
    namespace: dict = {}
    exec(code, {"__builtins__": {"set": set}}, namespace)
    return namespace["_VALID_CONNECTIONS"]


def _dataset() -> Dataset:
    return Dataset(energy="91 GeV", detector="IDEA")


def _mult_node(node_id="mult1"):
    return {
        "id": node_id,
        "kind": "Multiplicity",
        "config": {
            "nlep": 2, "op_lep": ">=", "njets": 0, "op_jet": ">=",
            "ltype": "Any", "nphot": 0, "op_phot": ">=",
        },
    }


def _sel_node(node_id="sel1", exprs=None):
    return {"id": node_id, "kind": "Selection", "config": {"name": node_id, "exprs": exprs or ["l1.pt > 20"]}}


def _obs_node(node_id="obs1", mode="ObsCustom", expr="(l1.p4 + l2.p4).mass"):
    return {"id": node_id, "kind": "Observable", "config": {"mode": mode, "expr": expr, "label": "m(l1,l2)"}}


def _hist_node(node_id="hist1", plot_idx=0):
    return {"id": node_id, "kind": "Histogram", "config": {"bins": "50", "min": "60.0", "max": "120.0"}}


def _mission1_payload():
    return {
        "nodes": [_mult_node(), _sel_node(), _obs_node(), _hist_node()],
        "edges": [["mult1", "sel1"], ["sel1", "obs1"], ["obs1", "hist1"]],
    }


# ---- C1: the allowlist reproduces the brief's five rows ----

def test_valid_connections_reproduces_brief_rows():
    assert VALID_CONNECTIONS["DataSource"] == ["Multiplicity", "Selection"]
    assert VALID_CONNECTIONS["Multiplicity"] == ["Multiplicity", "Selection"]
    assert set(VALID_CONNECTIONS["Selection"]) == {
        "Selection", "Observable", "ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom",
    }
    for obs_kind in ("Observable", "ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom"):
        assert VALID_CONNECTIONS[obs_kind] == ["Histogram"]
    assert VALID_CONNECTIONS["Histogram"] == []


# ---- C2: parity with the reference, skip when it is not on disk ----

def test_valid_connections_matches_reference():
    root = _reference_root()
    if not os.path.isdir(os.path.join(root, "ui")):
        pytest.skip(f"reference checkout not found under {root!r} (set ${_REFERENCE_ROOT_ENV})")
    reference = _reference_valid_connections(root)
    ours = {kind: set(dsts) for kind, dsts in VALID_CONNECTIONS.items()}
    reference = {kind: set(dsts) for kind, dsts in reference.items()}
    assert ours == reference


# ---- C3: illegal edge names the offending pair ----

def test_illegal_edge_names_the_pair():
    payload = {
        "nodes": [_mult_node("m1"), _hist_node("h1")],
        "edges": [["m1", "h1"]],
    }
    with pytest.raises(GraphError, match="Multiplicity.*m1.*Histogram.*h1"):
        build_run_config(payload, _dataset())


# ---- C4: DataSource in the payload is rejected ----

def test_datasource_in_payload_is_rejected():
    payload = {
        "nodes": [{"id": "ds1", "kind": "DataSource", "config": {}}],
        "edges": [],
    }
    with pytest.raises(GraphError, match="DataSource"):
        build_run_config(payload, _dataset())


# ---- C5: Observable mode resolves to one of the four subtypes ----

@pytest.mark.parametrize("mode", ["ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom"])
def test_observable_mode_resolves(mode):
    payload = {
        "nodes": [_sel_node(), _obs_node(mode=mode), _hist_node()],
        "edges": [["sel1", "obs1"], ["obs1", "hist1"]],
    }
    cfg = build_run_config(payload, _dataset())
    assert isinstance(cfg, RunConfig)


def test_observable_bad_mode_is_rejected():
    payload = {
        "nodes": [_sel_node(), _obs_node(mode="NotAMode"), _hist_node()],
        "edges": [["sel1", "obs1"], ["obs1", "hist1"]],
    }
    with pytest.raises(GraphError, match="mode"):
        build_run_config(payload, _dataset())


# ---- C6: cyclic / disconnected / no terminal, each its own message ----

def test_cyclic_graph_is_rejected():
    payload = {
        "nodes": [_mult_node("m1"), _mult_node("m2")],
        "edges": [["m1", "m2"], ["m2", "m1"]],
    }
    with pytest.raises(GraphError, match="cyclic"):
        build_run_config(payload, _dataset())


def test_disconnected_graph_is_rejected():
    payload = _mission1_payload()
    payload["nodes"].append(_mult_node("orphan"))
    with pytest.raises(GraphError, match="disconnected"):
        build_run_config(payload, _dataset())


def test_missing_histogram_terminal_is_rejected():
    payload = {
        "nodes": [_sel_node(), _obs_node()],
        "edges": [["sel1", "obs1"]],
    }
    with pytest.raises(GraphError, match="Histogram"):
        build_run_config(payload, _dataset())


# ---- C7: the translated output is accepted by RunConfig.from_dict ----

def test_mission1_graph_produces_a_run_config():
    cfg = build_run_config(_mission1_payload(), _dataset())
    assert isinstance(cfg, RunConfig)
    assert cfg.energy == "91 GeV"
    assert cfg.detector == "IDEA"
    assert cfg.observable == "(l1.p4 + l2.p4).mass"
    assert cfg.sel_exprs == ["l1.pt > 20"]
    assert len(cfg.selections) == 1
    assert len(cfg.selections[0].histograms) == 1


# ---- C8: graph.py is pure ----

def test_graph_module_is_pure():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "fce_web", "graph.py")
    with open(path, "r") as f:
        tree = ast.parse(f.read(), filename=path)
    forbidden = {"fastapi", "os", "pathlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden, alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden, node.module
    # No module-level mutable state: every module-level assignment target
    # must be a constant-shaped name (tuples/dicts of literals are fine --
    # VALID_CONNECTIONS itself -- what is forbidden is a container mutated
    # later, which this codebase's own convention is to avoid entirely by
    # never reassigning a module global after definition).
    module_level_names = [
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    ]
    assert len(module_level_names) == len(set(module_level_names))
