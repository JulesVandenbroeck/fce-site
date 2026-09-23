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
from pathlib import Path

from playwright.sync_api import expect

from tests.e2e.conftest import LoadedPage

from fce_web.graph import Dataset, build_run_config
from fce_web.engine.runconfig import RunConfig

PALETTE_KINDS = ("Multiplicity", "Selection", "Observable", "Histogram")

# F-016's own node size constants (graph.js's NODE_W/NODE_H) -- duplicated as
# literals since a test file can't import a JS module.
_NODE_W = 160
_NODE_H = 104

CANVAS_FRAME_CSS = Path(__file__).resolve().parents[2] / "docs" / "design-explorations" / "canvas-frame.css"


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
    """C2: positions persist as {id, x, y}, edges as an ordered pair list.

    F-015: the canvas is no longer confined to a fixed strip beside the
    palette -- the two `.click()`s above can themselves scroll the page (the
    palette now sits below the canvas in the unstyled shell, per N12), so a
    coordinate read before that scroll settles is stale before it is even
    used. Every box a raw `page.mouse` drag depends on is read only after
    `scroll_into_view_if_needed()` on the element the drag starts from --
    never cached from an earlier point in the test.
    """
    page = index.page

    page.locator('.palette__add[data-add-kind="Multiplicity"]').click()
    page.locator('.palette__add[data-add-kind="Selection"]').click()

    graph = _graph(page)
    n1_start = _node_by_id(graph, "n1")

    # Drag n1 by its handle.
    handle = page.locator('.node[data-node-id="n1"] .node__handle')
    handle.scroll_into_view_if_needed()
    handle_box = handle.bounding_box()
    start = (handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(start[0] + 30, start[1] + 20)
    page.mouse.up()

    moved = _node_by_id(_graph(page), "n1")
    assert (moved["x"], moved["y"]) != (n1_start["x"], n1_start["y"])

    # Connect n1's output to n2's input by dragging between ports. Scroll
    # once, via the first port, so both ports are read in the same settled
    # frame -- scrolling to each independently would invalidate whichever
    # was measured first.
    out_port = page.locator('.node[data-node-id="n1"] .port--out')
    in_port = page.locator('.node[data-node-id="n2"] .port--in')
    out_port.scroll_into_view_if_needed()
    out_box = out_port.bounding_box()
    in_box = in_port.bounding_box()
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
        "nodes": [{**n, "config": node_config[n["kind"]]} for n in graph["nodes"]],
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


def test_recollapsed_node_returns_to_its_collapsed_height(index: LoadedPage) -> None:
    """N15/F-014: a node grown open and then closed again must shrink back
    to the same footprint it had before -- not keep the opened height.
    ObsVectorSum's default panel (six checkboxes) is taller than one line,
    so a one-line panel could not fail this."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1
    fo = page.locator('foreignObject[data-node-id="n1"]')
    collapsed_height = float(fo.get_attribute("height"))

    summary = page.locator('.node[data-node-id="n1"] summary')
    summary.focus()
    page.keyboard.press("Enter")
    page.wait_for_function(
        f"() => Number(document.querySelector('foreignObject[data-node-id=\"n1\"]')"
        f".getAttribute('height')) > {collapsed_height}"
    )
    opened_height = float(fo.get_attribute("height"))
    assert opened_height > collapsed_height

    page.keyboard.press("Enter")
    page.wait_for_function(
        f"() => Number(document.querySelector('foreignObject[data-node-id=\"n1\"]')"
        f".getAttribute('height')) < {opened_height}"
    )
    reclosed_height = float(fo.get_attribute("height"))
    assert reclosed_height == collapsed_height


def test_observable_mode_is_config_not_identity(index: LoadedPage) -> None:
    """C3: the exported node's `kind` stays `Observable`; the chosen mode
    rides along as `config.mode`, for the server to resolve at submit.

    Updated (F-011, orchestrator re-spec 2026-09-16): the default mode is
    now `ObsVectorSum`, not `ObsGlobal` (docs/plan-m4-recipe-builder.md's
    table, C1) -- switched to `ObsGlobal` here instead, so the test still
    demonstrates a change away from whatever the default is, not a
    same-value round trip."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1

    graph = _graph(page)
    node = _node_by_id(graph, "n1")
    assert node["kind"] == "Observable"
    assert node["config"]["mode"] == "ObsVectorSum"  # C1's default, unopened

    summary = page.locator('.node[data-node-id="n1"] summary')
    summary.focus()
    page.keyboard.press("Enter")
    # .focus() + Space, not .check()'s real pointer click: the interior is
    # unstyled until D-018, and VectorSum's now-larger default panel (six
    # checkboxes) can grow the node tall enough that a screen click on an
    # early radio lands under the palette column -- the same
    # unstyled-layout brittleness test_run.py's
    # test_layout_only_change_is_a_cache_hit_on_resubmit already documents
    # for a different node. Reaching the control by keyboard sidesteps it
    # and is exactly how a keyboard user would operate it anyway.
    global_radio = page.locator('.node[data-node-id="n1"] input[value="ObsGlobal"]')
    global_radio.focus()
    page.keyboard.press(" ")

    node = _node_by_id(_graph(page), "n1")
    assert node["kind"] == "Observable"
    assert node["config"]["mode"] == "ObsGlobal"


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
    screen reader -- a real check, not one certified green by construction.
    C8: opening it from the keyboard leaves focus on that same summary --
    the toggle handler moves the node's foreignObject to the end of
    #nodes-layer (C6), and that reparenting must not throw focus to
    <body>."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1
    summary = page.locator('.node[data-node-id="n1"] summary')

    assert summary.inner_text().strip() != ""  # accessible name: its own text

    summary.focus()
    page.keyboard.press("Enter")
    assert page.locator('.node[data-node-id="n1"] details').get_attribute("open") is not None
    expect(summary).to_be_focused()

    page.keyboard.press("Enter")
    assert page.locator('.node[data-node-id="n1"] details').get_attribute("open") is None
    expect(summary).to_be_focused()


def test_observable_default_subtitle_matches_exported_config(index: LoadedPage) -> None:
    """C9: a freshly placed node's visible subtitle names the same mode its
    exported `config` carries -- not a placeholder that lags behind the
    default `config.mode` until the student touches a radio.

    Updated (F-011, orchestrator re-spec 2026-09-16): default mode/subtitle
    are now `ObsVectorSum`/"Vector sum", not `ObsGlobal`/"Global" -- literals
    only, the guarded property (subtitle text matches config.mode's label)
    is unchanged."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1

    node = _node_by_id(_graph(page), "n1")
    assert node["config"]["mode"] == "ObsVectorSum"

    subtitle = page.locator('.node[data-node-id="n1"] .node__subtitle')
    assert subtitle.inner_text().strip() == "Vector sum"


def test_observable_interior_has_no_dead_controls(index: LoadedPage) -> None:
    """C10: every control inside the node interior either reaches the
    exported `config` or is absent.

    Updated (F-011, orchestrator re-spec 2026-09-16): C1 replaced the bare
    mode radios with four full per-mode panels (docs/plan-m4-recipe-builder.md's
    table) -- every panel's controls are always present in the DOM (only the
    active mode's panel is visible; switching modes, not remounting DOM,
    reveals the rest), so the expected count and type breakdown below covers
    all four panels, not just the radios. Each figure is the size of the
    thing it comes from, not a guessed number: 4 mode radios; Global's 1
    quantity <select>; Object's object + property <select>s (2); VectorSum's
    <select>s aren't checkboxes -- 6 object checkboxes (expr.js's
    VECTOR_SUM_OBJECTS, OBJECTS minus `met`) + 1 quantity <select>; Custom's
    1 text <input>. No control renders that C1's four panels don't define,
    and no defined control is missing."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1
    summary = page.locator('.node[data-node-id="n1"] summary')
    summary.focus()
    page.keyboard.press("Enter")

    interior = page.locator('.node[data-node-id="n1"] .node__interior')
    controls = interior.locator("input, select, textarea, button")
    assert controls.count() == 15
    kinds = [controls.nth(i).get_attribute("type") for i in range(controls.count())]
    assert kinds.count("radio") == 4  # the mode toggle
    assert kinds.count(None) == 4  # <select> has no `type` attribute
    assert kinds.count("checkbox") == 6  # VectorSum's ticked objects
    assert kinds.count("text") == 1  # Custom's expression field
    assert len(kinds) == 4 + 4 + 6 + 1  # nothing left over, no other type


# ---- F-009: an opened node is re-clamped by its measured size, not the
# collapsed NODE_W/NODE_H -------------------------------------------------


def _inside(inner: dict, outer: dict, eps: float = 0.5) -> bool:
    return (
        inner["x"] >= outer["x"] - eps
        and inner["y"] >= outer["y"] - eps
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + eps
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + eps
    )


def _await_settled(page, node_id: str) -> None:
    """C6's reparent-on-open restarts the node's CSS entrance animation
    (translateY) -- measure the settled box, not one still mid-transform."""
    page.evaluate(
        "async (id) => {"
        " const el = document.querySelector(`.node[data-node-id=\"${id}\"]`);"
        " await Promise.all(el.getAnimations().map((a) => a.finished));"
        "}",
        node_id,
    )


def _open_and_settle(page, node_id: str) -> None:
    """Opens the node by keyboard, waits for the grow-in-place resize to
    land, then waits for the reparent-restarted entrance animation to
    settle (see _await_settled) before anything measures the node's box."""
    fo = page.locator(f'foreignObject[data-node-id="{node_id}"]')
    collapsed_height = float(fo.get_attribute("height"))
    page.locator(f'.node[data-node-id="{node_id}"] summary').focus()
    page.keyboard.press("Enter")
    page.wait_for_function(
        f"() => Number(document.querySelector('foreignObject[data-node-id=\"{node_id}\"]')"
        f".getAttribute('height')) > {collapsed_height}"
    )
    _await_settled(page, node_id)


def test_opened_node_near_bottom_edge_stays_inside_canvas_in_every_mode(index: LoadedPage) -> None:
    """C1: an Observable dragged low on the canvas, then opened, keeps its
    measured box (`.node`'s own `getBoundingClientRect`, not the
    foreignObject) fully inside the canvas SVG -- in every one of the four
    modes, since switching modes re-measures and re-clamps too.

    F-015: placing the node, opening it, and checking a mode radio can each
    scroll the page on their own (the palette and the node's own controls
    can land off-screen once the canvas is no longer confined to a fixed
    strip, N12), so `svg_box` is never captured once and trusted -- both it
    and `node_box` are (re)measured together, immediately after bringing
    the canvas back into view, right where each is used.
    """
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1

    svg = page.locator("#canvas-svg")
    handle = page.locator('.node[data-node-id="n1"] .node__handle')
    handle.scroll_into_view_if_needed()
    svg_box = svg.bounding_box()
    handle_box = handle.bounding_box()
    start = (handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    target = (svg_box["x"] + svg_box["width"] / 2, svg_box["y"] + svg_box["height"] - 5)
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(*target, steps=5)
    page.mouse.up()

    _open_and_settle(page, "n1")

    for mode in ("ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom"):
        page.locator(f'.node[data-node-id="n1"] input[value="{mode}"]').check()
        svg.scroll_into_view_if_needed()
        svg_box = svg.bounding_box()
        node_box = page.locator('.node[data-node-id="n1"]').bounding_box()
        assert _inside(node_box, svg_box), f"mode {mode}: {node_box} not inside {svg_box}"


def test_dragging_opened_node_past_edges_clamps_by_measured_size(index: LoadedPage) -> None:
    """C2: dragging an opened node past the bottom and right edges clamps by
    the live measured box, not the collapsed NODE_W/NODE_H -- revert the
    clamp in graph.js to use NODE_H and this goes red, since an opened
    Observable's real height (~232px) is well over NODE_H (104px), leaving
    its bottom edge outside the SVG. C3: closing it afterwards still holds."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Observable"]').click()  # n1

    _open_and_settle(page, "n1")

    svg_box = page.locator("#canvas-svg").bounding_box()
    handle = page.locator('.node[data-node-id="n1"] .node__handle')
    handle_box = handle.bounding_box()
    start = (handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    target = (svg_box["x"] + svg_box["width"] + 200, svg_box["y"] + svg_box["height"] + 200)
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(*target, steps=5)
    page.mouse.up()

    node_box = page.locator('.node[data-node-id="n1"]').bounding_box()
    assert _inside(node_box, svg_box)

    page.locator('.node[data-node-id="n1"] summary').focus()
    page.keyboard.press("Enter")  # close it
    assert page.locator('.node[data-node-id="n1"] details').get_attribute("open") is None
    closed_box = page.locator('.node[data-node-id="n1"]').bounding_box()
    assert _inside(closed_box, svg_box)


# ---- F-016: pan and zoom on the canvas surface ---------------------------
#
# canvas.css/shell.css predate D-022 (last touched at D-019, before F-015's
# markup restructure) and do not yet give #canvas-wrap `overflow: auto` or
# leave the SVG's own width/height attributes alone (shell.css still forces
# `.canvas-svg { width: 100% }` and a fixed `.canvas-wrap` width) -- so
# without extra CSS there is no scroll range to pan and no rendered size
# change to measure for zoom. That CSS is design's file, not this task's
# (D-022 ships it). These tests inject the already-approved
# docs/design-explorations/canvas-frame.css, which styles exactly the
# selectors this port uses (`.canvas-viewport`, `.canvas-svg`,
# `#zoom-controls`, `.frame`, `.canvas-region`), plus two ID-selector
# overrides for the two shell.css rules that would otherwise still win by
# loading later than nothing -- not invented behaviour, the CSS contract
# D-022 is expected to ship, applied so the real JS/DOM mechanism can be
# exercised in a real browser today.
def _use_panzoom_css(page) -> None:
    page.add_style_tag(path=str(CANVAS_FRAME_CSS))
    page.add_style_tag(content="#canvas-wrap { width: auto; } #canvas-svg { width: auto; height: auto; }")
    # graph.js sizes the sheet once at page load, against whatever CSS was
    # active then (the stale, fixed-width production rules) -- a `resize`
    # is the same recompute applyZoom already does for a real window resize,
    # so it is the honest way to have it re-measure under the CSS just added.
    page.evaluate("window.dispatchEvent(new Event('resize'))")


def _scroll_offset(page):
    return page.evaluate(
        "() => { const w = document.getElementById('canvas-wrap'); return [w.scrollLeft, w.scrollTop]; }"
    )


def _drag(page, start, end, steps=5):
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(*end, steps=steps)
    page.mouse.up()


def test_drag_on_empty_canvas_pans_both_axes_at_100_and_50_percent(index: LoadedPage) -> None:
    """C1: a left-drag on empty canvas pans in both axes, at 100% and 50%."""
    page = index.page
    _use_panzoom_css(page)
    wrap = page.locator("#canvas-wrap")
    wrap.scroll_into_view_if_needed()

    for zoom_out_clicks in (0, 2):  # 100%, then two steps down to 50%
        for _ in range(zoom_out_clicks):
            page.locator("#zoom-out").click()
        before = _scroll_offset(page)
        box = wrap.bounding_box()
        start = (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        _drag(page, start, (start[0] + 80, start[1] + 60))
        after = _scroll_offset(page)
        assert after[0] != before[0] and after[1] != before[1], (zoom_out_clicks, before, after)


def test_drag_starting_on_a_node_moves_it_and_does_not_pan(index: LoadedPage) -> None:
    """C2: the drag's meaning is decided by where it starts, not a mode."""
    page = index.page
    _use_panzoom_css(page)
    page.locator('.palette__add[data-add-kind="Multiplicity"]').click()  # n1

    handle = page.locator('.node[data-node-id="n1"] .node__handle')
    handle.scroll_into_view_if_needed()
    scroll_before = _scroll_offset(page)
    node_before = _node_by_id(_graph(page), "n1")

    handle_box = handle.bounding_box()
    start = (handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    _drag(page, start, (start[0] + 40, start[1] + 30))

    node_after = _node_by_id(_graph(page), "n1")
    scroll_after = _scroll_offset(page)
    assert (node_after["x"], node_after["y"]) != (node_before["x"], node_before["y"])
    assert scroll_after == scroll_before


def test_keyboard_pans_the_focused_canvas_on_both_axes(index: LoadedPage) -> None:
    """C3: arrow keys pan once the canvas has focus -- native `overflow:
    auto` scrolling of the focused, tabindex=0 #canvas-wrap, no JS of ours."""
    page = index.page
    _use_panzoom_css(page)
    wrap = page.locator("#canvas-wrap")
    wrap.focus()
    expect(wrap).to_be_focused()

    before = _scroll_offset(page)
    for _ in range(25):
        page.keyboard.press("ArrowRight")
    for _ in range(25):
        page.keyboard.press("ArrowDown")
    after = _scroll_offset(page)
    assert after[0] > before[0]
    assert after[1] > before[1]


def test_zoom_clamps_between_50_and_200_percent(index: LoadedPage) -> None:
    """C4."""
    page = index.page
    _use_panzoom_css(page)

    for _ in range(10):  # well past the 200% ceiling
        if page.locator("#zoom-in").is_disabled():
            break
        page.locator("#zoom-in").click()
    assert page.locator("#zoom-readout").inner_text() == "200%"
    assert page.locator("#zoom-in").is_disabled()

    for _ in range(20):  # well past the 50% floor
        if page.locator("#zoom-out").is_disabled():
            break
        page.locator("#zoom-out").click()
    assert page.locator("#zoom-readout").inner_text() == "50%"
    assert page.locator("#zoom-out").is_disabled()


def test_node_extent_stays_inside_the_sheet_after_zooming_in(index: LoadedPage) -> None:
    """C5, D-021's F2: a node dragged to the far edge at 50% must not be
    orphaned outside the sheet once zoomed back in to 200%."""
    page = index.page
    _use_panzoom_css(page)
    page.locator('.palette__add[data-add-kind="Multiplicity"]').click()  # n1

    page.locator("#zoom-out").click()
    page.locator("#zoom-out").click()  # 50%

    handle = page.locator('.node[data-node-id="n1"] .node__handle')
    handle.scroll_into_view_if_needed()
    svg_box = page.locator("#canvas-svg").bounding_box()
    handle_box = handle.bounding_box()
    start = (handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    target = (svg_box["x"] + svg_box["width"] - 5, svg_box["y"] + svg_box["height"] - 5)
    _drag(page, start, target, steps=8)

    for _ in range(6):
        page.locator("#zoom-in").click()  # back up to 200%

    node = _node_by_id(_graph(page), "n1")
    sheet = page.evaluate(
        "() => document.getElementById('canvas-svg').getAttribute('viewBox').split(' ').slice(2).map(Number)"
    )
    assert node["x"] + _NODE_W <= sheet[0]
    assert node["y"] + _NODE_H <= sheet[1]


def test_fit_shows_the_whole_graph_and_is_the_only_reset_control(index: LoadedPage) -> None:
    """C6: Fit is the one reset affordance -- pan and zoom away, press it,
    and every node is back inside the visible canvas."""
    page = index.page
    _use_panzoom_css(page)
    for kind in ("Multiplicity", "Selection"):
        page.locator(f'.palette__add[data-add-kind="{kind}"]').click()

    page.locator("#zoom-out").click()
    page.locator("#zoom-out").click()
    wrap = page.locator("#canvas-wrap")
    wrap.scroll_into_view_if_needed()
    box = wrap.bounding_box()
    _drag(page, (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2), (box["x"] + 5, box["y"] + 5))

    page.locator("#zoom-fit").click()

    wrap_box = wrap.bounding_box()
    for node_id in ("n1", "n2"):
        node_box = page.locator(f'.node[data-node-id="{node_id}"]').bounding_box()
        assert _inside(node_box, wrap_box), (node_id, node_box, wrap_box)

    # One affordance only -- no separate reset-to-100% control.
    assert page.locator("#zoom-controls button").count() == 3  # zoom-out, zoom-in, zoom-fit
    assert page.locator('button:has-text("Reset")').count() == 0





