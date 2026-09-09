"""Browser assertions about the node graph (F-005), ported from
docs/design-explorations/bench.html onto templates/shell.html's canvas.

Frontend's own markup, on frontend's side of the 2026-09-07 conftest seam
(`.claude/shared/CLAUDE.md` §4): these tests use the harness fixtures from
`tests/e2e/conftest.py` without adding to it.

The exported model these tests assert on: `#canvas-wrap` carries a
`data-graph` attribute, JSON-shaped
    { nodes: [{id, kind, x, y}, ...], edges: [[from, to], ...] }
per the F-005 PR body's contract -- `nodes` is a list, matching what
`fce_web.graph.build_run_config` requires (`src/fce_web/graph.py:120,122-123`).
"""

import json

import pytest

from tests.e2e.conftest import LoadedPage

from fce_web.graph import Dataset, build_run_config
from fce_web.engine.runconfig import RunConfig

PALETTE_KINDS = ("Multiplicity", "Selection", "Observable", "Histogram")


def _graph(page) -> dict:
    return json.loads(page.locator("#canvas-wrap").get_attribute("data-graph"))


def _node_by_id(graph: dict, node_id: str) -> dict:
    return next(n for n in graph["nodes"] if n["id"] == node_id)


def test_palette_offers_exactly_four_kinds(index: LoadedPage) -> None:
    """C1: not seven, not eight -- bench.html's extra buttons are superseded."""
    page = index.page
    buttons = page.locator(".palette__add[data-add-kind]")
    assert buttons.count() == 4
    kinds = {buttons.nth(i).get_attribute("data-add-kind") for i in range(4)}
    assert kinds == set(PALETTE_KINDS)


def test_no_datasource_node_is_placeable(index: LoadedPage) -> None:
    """C5: the server synthesises DataSource at submit (B-020 C4)."""
    assert index.page.locator('[data-add-kind="DataSource"]').count() == 0


def test_locked_node_kind_is_shown_and_inert(index: LoadedPage) -> None:
    """C6: shown, labelled, aria-disabled, and carries no focusable control."""
    page = index.page
    locked = page.locator(".palette__locked")
    assert locked.count() == 1
    assert locked.get_attribute("aria-disabled") == "true"
    assert "locked" in locked.inner_text().lower()
    assert locked.locator("button").count() == 0


def test_keyboard_only_builds_a_complete_mission_1_graph(index: LoadedPage) -> None:
    """C3: place four nodes, arm an output, complete a connection, and move a
    node -- all via keyboard, then assert on the resulting model."""
    page = index.page

    for kind in PALETTE_KINDS:
        btn = page.locator(f'.palette__add[data-add-kind="{kind}"]')
        btn.focus()
        page.keyboard.press("Enter")

    graph = _graph(page)
    assert isinstance(graph["nodes"], list)
    assert {n["id"] for n in graph["nodes"]} == {"n1", "n2", "n3", "n4"}
    assert [_node_by_id(graph, f"n{i}")["kind"] for i in range(1, 5)] == list(PALETTE_KINDS)

    # Arm n1's output, then complete on n2's input -- Enter/Space only, never
    # a click, per handleOutKey/handleInKey.
    for from_id, to_id in (("n1", "n2"), ("n2", "n3"), ("n3", "n4")):
        out_port = page.locator(f'.node[data-node-id="{from_id}"] .port--out')
        out_port.focus()
        page.keyboard.press("Enter")
        in_port = page.locator(f'.node[data-node-id="{to_id}"] .port--in')
        in_port.focus()
        page.keyboard.press("Enter")

    graph = _graph(page)
    assert graph["edges"] == [["n1", "n2"], ["n2", "n3"], ["n3", "n4"]]

    # Move n1 with the arrow keys via its handle.
    before = _node_by_id(graph, "n1")
    handle = page.locator('.node[data-node-id="n1"] .node__handle')
    handle.focus()
    page.keyboard.press("ArrowRight")
    after = _node_by_id(_graph(page), "n1")
    assert after["x"] == before["x"] + 12
    assert after["y"] == before["y"]


def test_pointer_places_drags_and_connects_nodes(index: LoadedPage) -> None:
    """C2: positions persist as {id, x, y}, edges as an ordered pair list."""
    page = index.page

    page.locator('.palette__add[data-add-kind="Multiplicity"]').click()
    page.locator('.palette__add[data-add-kind="Selection"]').click()

    graph = _graph(page)
    n1_start = _node_by_id(graph, "n1")

    # Drag n1 by its handle.
    handle_box = page.locator('.node[data-node-id="n1"] .node__handle').bounding_box()
    start = (handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(start[0] + 30, start[1] + 20)
    page.mouse.up()

    moved = _node_by_id(_graph(page), "n1")
    assert (moved["x"], moved["y"]) != (n1_start["x"], n1_start["y"])

    # Connect n1's output to n2's input by dragging between ports.
    out_box = page.locator('.node[data-node-id="n1"] .port--out').bounding_box()
    in_box = page.locator('.node[data-node-id="n2"] .port--in').bounding_box()
    out_center = (out_box["x"] + out_box["width"] / 2, out_box["y"] + out_box["height"] / 2)
    in_center = (in_box["x"] + in_box["width"] / 2, in_box["y"] + in_box["height"] / 2)
    page.mouse.move(*out_center)
    page.mouse.down()
    page.mouse.move(*in_center, steps=5)
    page.mouse.up()

    assert _graph(page)["edges"] == [["n1", "n2"]]


def test_illegal_connection_is_refused_client_side(index: LoadedPage) -> None:
    """C4: courtesy check mirroring fce_web.graph.VALID_CONNECTIONS -- the
    server is the authority (B-020); a client that disagrees is a bug."""
    page = index.page

    page.locator('.palette__add[data-add-kind="Histogram"]').click()  # n1
    page.locator('.palette__add[data-add-kind="Multiplicity"]').click()  # n2 -- Histogram has no out port

    # Selection -> Histogram is illegal (only Observable -> Histogram is).
    page.locator('.palette__add[data-add-kind="Selection"]').click()  # n3

    out_port = page.locator('.node[data-node-id="n3"] .port--out')
    out_port.focus()
    page.keyboard.press("Enter")
    in_port = page.locator('.node[data-node-id="n1"] .port--in')
    in_port.focus()
    page.keyboard.press("Enter")

    assert _graph(page)["edges"] == []
    assert "refused" in page.locator("#canvas-status").inner_text().lower()


def test_graph_page_logs_no_console_errors(index: LoadedPage) -> None:
    """C7."""
    page = index.page
    for kind in PALETTE_KINDS:
        page.locator(f'.palette__add[data-add-kind="{kind}"]').click()
    assert index.activity.console_errors == []
    assert index.activity.page_errors == []


def test_graph_page_has_no_bad_responses(index: LoadedPage) -> None:
    """C7."""
    assert index.activity.bad_responses == []


def test_duplicate_connection_is_not_appended_twice(index: LoadedPage) -> None:
    """C9: double-pressing the same out/in pair must not append a second
    edge -- `build_run_config` turns a duplicated edge into two identical
    `HistogramConfig`s, so an unguarded double-press would silently run and
    plot the analysis twice."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Multiplicity"]').click()  # n1
    page.locator('.palette__add[data-add-kind="Selection"]').click()  # n2

    def connect_by_keyboard():
        out_port = page.locator('.node[data-node-id="n1"] .port--out')
        out_port.focus()
        page.keyboard.press("Enter")
        in_port = page.locator('.node[data-node-id="n2"] .port--in')
        in_port.focus()
        page.keyboard.press("Enter")

    connect_by_keyboard()
    connect_by_keyboard()  # same pair again, by keyboard
    assert _graph(page)["edges"] == [["n1", "n2"]]

    out_box = page.locator('.node[data-node-id="n1"] .port--out').bounding_box()
    in_box = page.locator('.node[data-node-id="n2"] .port--in').bounding_box()
    out_center = (out_box["x"] + out_box["width"] / 2, out_box["y"] + out_box["height"] / 2)
    in_center = (in_box["x"] + in_box["width"] / 2, in_box["y"] + in_box["height"] / 2)
    page.mouse.move(*out_center)
    page.mouse.down()
    page.mouse.move(*in_center, steps=5)
    page.mouse.up()  # same pair again, by pointer

    assert _graph(page)["edges"] == [["n1", "n2"]]


def test_exported_nodes_is_a_list_accepted_by_build_run_config(index: LoadedPage) -> None:
    """C10: `nodes` is a list of `{id, kind, x, y}` (graph.py:120,122-123),
    not an object keyed by id -- checked against the real translator, not
    just the client-side shape."""
    page = index.page
    for kind in PALETTE_KINDS:
        page.locator(f'.palette__add[data-add-kind="{kind}"]').click()
    for from_id, to_id in (("n1", "n2"), ("n2", "n3"), ("n3", "n4")):
        out_port = page.locator(f'.node[data-node-id="{from_id}"] .port--out')
        out_port.focus()
        page.keyboard.press("Enter")
        in_port = page.locator(f'.node[data-node-id="{to_id}"] .port--in')
        in_port.focus()
        page.keyboard.press("Enter")

    graph = _graph(page)
    assert isinstance(graph["nodes"], list)

    # This client never sends node-interior config (brief §4/D-009 is still
    # open on that UI) -- fill in the minimum config build_run_config needs,
    # keyed by the kinds the client actually exported.
    node_config = {
        "Multiplicity": {"nlep": 2, "op_lep": ">=", "njets": 0, "op_jet": ">=",
                          "ltype": "Any", "nphot": 0, "op_phot": ">="},
        "Selection": {"name": "sel", "exprs": ["l1.pt > 20"]},
        "Observable": {"mode": "ObsCustom", "expr": "(l1.p4 + l2.p4).mass", "label": "m(l1,l2)"},
        "Histogram": {"bins": "50", "min": "60.0", "max": "120.0"},
    }
    payload = {
        "nodes": [{"id": n["id"], "kind": n["kind"], "config": node_config[n["kind"]]} for n in graph["nodes"]],
        "edges": graph["edges"],
    }

    cfg = build_run_config(payload, Dataset(energy="91 GeV", detector="IDEA"))
    assert isinstance(cfg, RunConfig)


# ---- F-006: the merged Observable node interior --------------------------
# Source: docs/design-explorations/observable.html (D-013). One `Observable`
# palette node, an in-node mode toggle, grows in place -- not the four-node
# `interiors.html` exploration D-009 superseded.


def test_observable_node_offers_exactly_four_modes(index: LoadedPage) -> None:
    """C1: the merged node's toggle offers ObsGlobal/ObsObject/ObsVectorSum/
    ObsCustom, and only those four."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1
    summary = page.locator('.node[data-node-id="n1"] summary')
    summary.focus()
    page.keyboard.press("Enter")

    radios = page.locator('.node[data-node-id="n1"] .mode-toggle input[type="radio"]')
    assert radios.count() == 4
    values = {radios.nth(i).get_attribute("value") for i in range(4)}
    assert values == {"ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom"}


def test_observable_node_grows_in_place_when_opened(index: LoadedPage) -> None:
    """C2: opening the node grows its own footprint -- no flyout, no second
    panel elsewhere on the page."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1
    fo = page.locator('foreignObject[data-node-id="n1"]')
    collapsed_height = float(fo.get_attribute("height"))

    summary = page.locator('.node[data-node-id="n1"] summary')
    summary.focus()
    page.keyboard.press("Enter")

    # The resize runs off the 'toggle' event, dispatched as its own task in
    # Chromium -- wait for the growth rather than race the keypress.
    page.wait_for_function(
        f"() => Number(document.querySelector('foreignObject[data-node-id=\"n1\"]')"
        f".getAttribute('height')) > {collapsed_height}"
    )
    opened_height = float(fo.get_attribute("height"))
    assert opened_height > collapsed_height
    assert page.locator('dialog, [role="dialog"], .inspector, .flyout').count() == 0


def test_observable_mode_is_config_not_identity(index: LoadedPage) -> None:
    """C3: the exported node's `kind` stays `Observable`; the chosen mode
    rides along as `config.mode`, for the server to resolve at submit."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1

    graph = _graph(page)
    node = _node_by_id(graph, "n1")
    assert node["kind"] == "Observable"
    assert node["config"]["mode"] == "ObsGlobal"  # default, unopened

    summary = page.locator('.node[data-node-id="n1"] summary')
    summary.focus()
    page.keyboard.press("Enter")
    page.locator('.node[data-node-id="n1"] input[value="ObsVectorSum"]').check()

    node = _node_by_id(_graph(page), "n1")
    assert node["kind"] == "Observable"
    assert node["config"]["mode"] == "ObsVectorSum"


def test_opened_observable_node_is_brought_to_front(index: LoadedPage) -> None:
    """C6: opening a node grows it over whatever else sits at that canvas
    position. SVG has no z-index -- paint order is the only stacking
    mechanism -- so the opened node moves to the end of #nodes-layer, painted
    last, even though it was placed before the node spawned after it."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1
    page.locator('.palette__add[data-add-kind="Histogram"]').click()  # n2, painted after n1

    summary = page.locator('.node[data-node-id="n1"] summary')
    summary.focus()
    page.keyboard.press("Enter")

    # The 'toggle' event that reorders the DOM is dispatched as its own task
    # in Chromium, not synchronously with the keypress -- wait for it rather
    # than race it.
    page.wait_for_function(
        "() => document.querySelector('#nodes-layer').lastElementChild.dataset.nodeId === 'n1'"
    )


def test_observable_mode_toggle_is_keyboard_operable_with_accessible_name(index: LoadedPage) -> None:
    """C5: the toggle's opener is reachable by Tab and names itself for a
    screen reader -- a real check, not one certified green by construction."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1
    summary = page.locator('.node[data-node-id="n1"] summary')

    assert summary.inner_text().strip() != ""  # accessible name: its own text

    summary.focus()
    page.keyboard.press("Enter")
    assert page.locator('.node[data-node-id="n1"] details').get_attribute("open") is not None


def test_c5_check_fails_when_the_accessible_name_is_removed(index: LoadedPage) -> None:
    """C5, explicitly required: proves the check above is not vacuous.
    D-009's Required/M1 checks were certified GREEN against unlabelled
    controls because they could not structurally fail; this mutates the
    summary's text (its accessible name) and shows the same assertion now
    goes red."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1
    summary = page.locator('.node[data-node-id="n1"] summary')
    summary.evaluate("el => { el.textContent = ''; }")

    with pytest.raises(AssertionError):
        assert summary.inner_text().strip() != ""
