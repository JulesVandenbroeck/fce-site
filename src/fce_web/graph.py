"""Validates a student graph against the connection allowlist and translates
it into the payload :meth:`fce_web.engine.runconfig.RunConfig.from_dict`
accepts.

**The palette the student places is four kinds**, not the engine's eight
(``docs/design-brief.md`` §4, rulings 2026-09-01/02):

* ``DataSource`` is never drawn. V1 ships one energy and each mission
  declares its own dataset, so it is synthesised here from the mission's
  :class:`Dataset` and made the implicit root of every chain -- a student
  payload that *contains* one is a client bug and is rejected (C4).
* ``Observable`` is one palette node with a ``mode`` field naming the engine
  subtype it resolves to (``ObsGlobal`` / ``ObsObject`` / ``ObsVectorSum`` /
  ``ObsCustom``) -- mode is config, not identity.

``VALID_CONNECTIONS`` is nonetheless keyed on the engine's eight kinds,
because that is the shape the reference's own ``ui/graph.py:_VALID_CONNECTIONS``
uses and ``tests/test_graph.py`` parity-checks against it directly
(``FCE_PARITY_REFERENCE_ROOT``, same pattern as ``tests/test_engine_parity.py``).
An ``Observable`` node is resolved to its ``mode`` before the allowlist is
consulted; nothing about which graphs are legal changes, because all four
``Obs*`` rows are identical (brief §4).

This module is pure: no HTTP, no filesystem, no module-level mutable state.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Tuple

from fce_web.engine.runconfig import RunConfig

__all__ = [
    "VALID_CONNECTIONS",
    "PALETTE_KINDS",
    "GraphError",
    "Dataset",
    "build_run_config",
]


class GraphError(ValueError):
    """A student graph is not a legal input -- an illegal edge, a cycle, a
    disconnected node, a missing ``Histogram`` terminal, or a node the
    palette does not offer (``DataSource``, an unknown kind, an unknown
    ``Observable`` mode). Distinct from :class:`RunConfigError`, which is
    raised by the engine's own loader on a config that is well-formed as a
    *graph* but wrong as a *config*.
    """


# The reference's `_VALID_CONNECTIONS` (`ui/graph.py`), reproduced verbatim --
# see docs/design-brief.md §4 and `docs/design-explorations/bench.html:245-255`,
# the non-authoritative JS copy this module supersedes. Keyed on the engine's
# eight kinds; the four `Obs*` rows are one row in the *palette* (`Observable`
# with a mode) but stay four rows here because the engine, and the reference
# this is parity-checked against, still distinguish them.
VALID_CONNECTIONS: Dict[str, List[str]] = {
    "DataSource": ["Multiplicity", "Selection"],
    "Multiplicity": ["Multiplicity", "Selection"],
    "Selection": ["Selection", "Observable", "ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom"],
    "Observable": ["Histogram"],
    "ObsGlobal": ["Histogram"],
    "ObsObject": ["Histogram"],
    "ObsVectorSum": ["Histogram"],
    "ObsCustom": ["Histogram"],
    "Histogram": [],
}

# The four kinds the student actually places (brief §4). `DataSource` is
# synthesised, not placed; `Observable` stands in for the four `Obs*` rows.
PALETTE_KINDS = ("Multiplicity", "Selection", "Observable", "Histogram")

_OBS_MODES = ("ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom")

# ui/graph.py:1719 -- one Multiplicity node's cut is this 7-tuple, in this
# field order. `_load_mult_cuts` in runconfig.py enforces the same shape on
# the way back out; reproduced here so a node's config dict translates to
# exactly the tuple the digest formula expects.
_MULT_CUT_FIELDS = ("nlep", "op_lep", "njets", "op_jet", "ltype", "nphot", "op_phot")


@dataclass(frozen=True)
class Dataset:
    """The energy/detector pair a mission declares. Synthesised into the
    implicit ``DataSource`` root at submit -- the student never draws or
    chooses one (brief §4, 2026-09-01 ruling)."""

    energy: str
    detector: str


@dataclass(frozen=True)
class _Node:
    id: str
    kind: str
    config: dict


def _resolved_kind(node: _Node) -> str:
    """The kind to check against `VALID_CONNECTIONS`: a node's own kind,
    except `Observable`, which resolves to its `mode` (2026-09-02 ruling)."""
    if node.kind != "Observable":
        return node.kind
    mode = node.config.get("mode")
    if mode not in _OBS_MODES:
        raise GraphError(
            f"node {node.id!r}: 'mode' must be one of {', '.join(_OBS_MODES)}, got {mode!r}"
        )
    return mode


def _parse_nodes(raw_nodes: list) -> Dict[str, _Node]:
    if not isinstance(raw_nodes, list):
        raise GraphError(f"'nodes' must be a list, got {type(raw_nodes).__name__}")
    nodes: Dict[str, _Node] = {}
    for i, raw in enumerate(raw_nodes):
        if not isinstance(raw, dict) or "id" not in raw or "kind" not in raw:
            raise GraphError(f"nodes[{i}] must be an object with 'id' and 'kind'")
        node_id = raw["id"]
        kind = raw["kind"]
        if kind == "DataSource":
            raise GraphError(
                f"node {node_id!r}: 'DataSource' is supplied from the mission's dataset, "
                "not drawn -- remove it from the graph you submit"
            )
        if kind not in PALETTE_KINDS:
            raise GraphError(
                f"node {node_id!r}: unknown kind {kind!r}, expected one of {', '.join(PALETTE_KINDS)}"
            )
        if node_id in nodes:
            raise GraphError(f"duplicate node id {node_id!r}")
        nodes[node_id] = _Node(id=node_id, kind=kind, config=raw.get("config") or {})
    return nodes


def _parse_edges(raw_edges: list, nodes: Dict[str, _Node]) -> List[Tuple[str, str]]:
    if not isinstance(raw_edges, list):
        raise GraphError(f"'edges' must be a list, got {type(raw_edges).__name__}")
    edges: List[Tuple[str, str]] = []
    for i, raw in enumerate(raw_edges):
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            raise GraphError(f"edges[{i}] must be a 2-element [from, to] pair")
        src, dst = raw
        for end in (src, dst):
            if end not in nodes:
                raise GraphError(f"edges[{i}]: unknown node id {end!r}")
        edges.append((src, dst))
    return edges


def _children(nodes: Dict[str, _Node], edges: List[Tuple[str, str]]) -> Dict[str, List[str]]:
    children: Dict[str, List[str]] = {node_id: [] for node_id in nodes}
    for src, dst in edges:
        children[src].append(dst)
    return children


def _check_no_cycle(nodes: Dict[str, _Node], children: Dict[str, List[str]]) -> None:
    WHITE, GREY, BLACK = 0, 1, 2
    color = {node_id: WHITE for node_id in nodes}

    def visit(node_id: str) -> None:
        color[node_id] = GREY
        for child in children[node_id]:
            if color[child] == GREY:
                raise GraphError(f"the graph is cyclic: {node_id!r} leads back to {child!r}")
            if color[child] == WHITE:
                visit(child)
        color[node_id] = BLACK

    for node_id in nodes:
        if color[node_id] == WHITE:
            visit(node_id)


def _check_connected(nodes: Dict[str, _Node], edges: List[Tuple[str, str]]) -> None:
    if not nodes:
        raise GraphError("the graph is empty")
    undirected: Dict[str, List[str]] = {node_id: [] for node_id in nodes}
    for src, dst in edges:
        undirected[src].append(dst)
        undirected[dst].append(src)
    start = next(iter(nodes))
    seen = {start}
    stack = [start]
    while stack:
        current = stack.pop()
        for neighbour in undirected[current]:
            if neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    disconnected = set(nodes) - seen
    if disconnected:
        raise GraphError(f"disconnected from the rest of the graph: {', '.join(sorted(disconnected))}")


def _check_edges_legal(nodes: Dict[str, _Node], edges: List[Tuple[str, str]]) -> None:
    for src, dst in edges:
        src_kind = _resolved_kind(nodes[src])
        dst_kind = _resolved_kind(nodes[dst])
        if dst_kind not in VALID_CONNECTIONS.get(src_kind, []):
            raise GraphError(
                f"illegal connection: {nodes[src].kind} ({src!r}) cannot connect to "
                f"{nodes[dst].kind} ({dst!r})"
            )


def _roots(nodes: Dict[str, _Node], edges: List[Tuple[str, str]]) -> List[str]:
    has_incoming = {dst for _, dst in edges}
    roots = [node_id for node_id in nodes if node_id not in has_incoming]
    for root in roots:
        kind = _resolved_kind(nodes[root])
        if kind not in VALID_CONNECTIONS["DataSource"]:
            raise GraphError(
                f"illegal connection: DataSource cannot connect to {nodes[root].kind} ({root!r})"
            )
    return roots


def _check_terminals(nodes: Dict[str, _Node], children: Dict[str, List[str]]) -> None:
    leaves = [node_id for node_id, kids in children.items() if not kids]
    histograms = [node_id for node_id in leaves if nodes[node_id].kind == "Histogram"]
    if not histograms:
        raise GraphError("the graph has no 'Histogram' terminal")
    non_terminal_leaves = [node_id for node_id in leaves if nodes[node_id].kind != "Histogram"]
    if non_terminal_leaves:
        raise GraphError(
            f"dangling node(s) not ending in 'Histogram': {', '.join(sorted(non_terminal_leaves))}"
        )


def _mult_cut_tuple(node: _Node) -> tuple:
    config = node.config
    missing = [field for field in _MULT_CUT_FIELDS if field not in config]
    if missing:
        raise GraphError(f"node {node.id!r}: Multiplicity is missing {', '.join(missing)}")
    return tuple(config[field] for field in _MULT_CUT_FIELDS)


def _histogram_paths(
    nodes: Dict[str, _Node], children: Dict[str, List[str]], roots: List[str]
) -> List[List[str]]:
    """Every root-to-Histogram path. Each is `[Multiplicity*, Selection*,
    Observable, Histogram]` -- the only shape the allowlist permits."""
    paths: List[List[str]] = []

    def walk(node_id: str, prefix: List[str]) -> None:
        prefix = prefix + [node_id]
        kids = children[node_id]
        if not kids:
            paths.append(prefix)
            return
        for child in kids:
            walk(child, prefix)

    for root in roots:
        walk(root, [])
    return paths


def _shared_mult_cuts(nodes: Dict[str, _Node], paths: List[List[str]]) -> list:
    """The one multiplicity cut list the whole run shares -- the digest
    formula (`RunConfig.compute_h5_sel`) has no per-selection `mult_cuts`,
    so every path's Multiplicity prefix must agree."""
    cuts_by_path = []
    for path in paths:
        cuts = [_mult_cut_tuple(nodes[node_id]) for node_id in path if nodes[node_id].kind == "Multiplicity"]
        cuts_by_path.append(cuts)
    first = cuts_by_path[0]
    for cuts in cuts_by_path[1:]:
        if cuts != first:
            raise GraphError(
                "all branches must share the same Multiplicity chain -- the engine has one "
                "multiplicity cut list for the whole run"
            )
    return first


def _selection_group_key(path: List[str], nodes: Dict[str, _Node]) -> tuple:
    return tuple(node_id for node_id in path if nodes[node_id].kind == "Selection")


def _selection_exprs(path: List[str], nodes: Dict[str, _Node]) -> List[str]:
    exprs: List[str] = []
    for node_id in path:
        node = nodes[node_id]
        if node.kind == "Selection":
            branch_exprs = node.config.get("exprs")
            if not isinstance(branch_exprs, list) or not all(isinstance(e, str) for e in branch_exprs):
                raise GraphError(f"node {node_id!r}: Selection 'exprs' must be a list of strings")
            exprs.extend(branch_exprs)
    return exprs


def _histogram_dict(node: _Node, h5_sel: str, plot_idx: int) -> dict:
    config = node.config
    required = ("bins", "min", "max")
    missing = [field for field in required if field not in config]
    if missing:
        raise GraphError(f"node {node.id!r}: Histogram is missing {', '.join(missing)}")
    return {
        "observable": None,  # filled in by the caller, which knows the Observable node
        "x_label": config.get("x_label", ""),
        "bins": config["bins"],
        "min": config["min"],
        "max": config["max"],
        "target": config.get("target", "None"),
        "node_name": config.get("name", node.id),
        "obs_nid": None,
        "hist_nid": None,
        "h5": None,  # filled in by the caller once 'observable' is known
        "plot_idx": plot_idx,
    }


def build_run_config(payload: dict, dataset: Dataset) -> RunConfig:
    """Validate a student graph and translate it into the config
    :meth:`RunConfig.from_dict` accepts.

    Raises :class:`GraphError` for an illegal graph, and lets
    :class:`~fce_web.engine.runconfig.RunConfigError` propagate for a
    well-formed graph this function nonetheless failed to translate
    correctly -- which would be a bug here, not a student mistake.
    """
    if not isinstance(payload, dict):
        raise GraphError(f"graph payload must be an object, got {type(payload).__name__}")
    nodes = _parse_nodes(payload.get("nodes", []))
    edges = _parse_edges(payload.get("edges", []), nodes)
    children = _children(nodes, edges)

    _check_no_cycle(nodes, children)
    _check_connected(nodes, edges)
    roots = _roots(nodes, edges)
    _check_edges_legal(nodes, edges)
    _check_terminals(nodes, children)

    paths = _histogram_paths(nodes, children, roots)
    mult_cuts = _shared_mult_cuts(nodes, paths)
    mult_h5_base = dataset.energy + dataset.detector + str(mult_cuts)

    grouped: Dict[tuple, dict] = {}
    plot_idx = 0
    for path in paths:
        obs_id = path[-2]
        hist_id = path[-1]
        obs_node = nodes[obs_id]
        hist_node = nodes[hist_id]
        observable_expr = obs_node.config.get("expr")
        if not isinstance(observable_expr, str):
            raise GraphError(f"node {obs_id!r}: Observable 'expr' must be a string")

        key = _selection_group_key(path, nodes)
        if key not in grouped:
            sel_exprs = _selection_exprs(path, nodes)
            h5_sel = hashlib.md5((mult_h5_base + str(sel_exprs)).encode()).hexdigest()
            last_sel_id = key[-1] if key else None
            sel_name = nodes[last_sel_id].config.get("name", last_sel_id) if last_sel_id else ""
            grouped[key] = {
                "nid": None,
                "prefix_nids": [],
                "node_name": sel_name,
                "sel_custom_name": sel_name,
                "sel_exprs": sel_exprs,
                "h5_sel": h5_sel,
                "histograms": [],
            }

        selection = grouped[key]
        histogram = _histogram_dict(hist_node, selection["h5_sel"], plot_idx)
        histogram["observable"] = observable_expr
        histogram["x_label"] = histogram["x_label"] or obs_node.config.get("label", "")
        histogram["h5"] = hashlib.md5(
            (
                selection["h5_sel"] + observable_expr + histogram["bins"]
                + histogram["min"] + histogram["max"] + histogram["target"]
            ).encode()
        ).hexdigest()
        selection["histograms"].append(histogram)
        plot_idx += 1

    selections = list(grouped.values())
    first = selections[0]
    first_hist = first["histograms"][0]

    data = {
        "energy": dataset.energy,
        "detector": dataset.detector,
        "observable": first_hist["observable"],
        "bins": first_hist["bins"],
        "min": first_hist["min"],
        "max": first_hist["max"],
        "target": first_hist["target"],
        "h5": first_hist["h5"],
        "h5_sel": first["h5_sel"],
        "mult_cuts": [list(cut) for cut in mult_cuts],
        "sel_exprs": first["sel_exprs"],
        "histograms": [dict(h) for h in first["histograms"]],
        "selections": selections,
    }
    return RunConfig.from_dict(data)
