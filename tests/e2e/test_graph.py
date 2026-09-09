"""Browser assertions about the node graph (F-005), ported from
docs/design-explorations/bench.html onto templates/shell.html's canvas.

Frontend's own markup, on frontend's side of the 2026-09-07 conftest seam
(`.claude/shared/CLAUDE.md` §4): these tests use the harness fixtures from
`tests/e2e/conftest.py` without adding to it.

The exported model these tests assert on: `#canvas-wrap` carries a
`data-graph` attribute, JSON-shaped
    { nodes: { <id>: {kind, x, y}, ... }, edges: [[from, to], ...] }
per the F-005 PR body's contract.
"""

import json

from tests.e2e.conftest import LoadedPage

PALETTE_KINDS = ("Multiplicity", "Selection", "Observable", "Histogram")


def _graph(page) -> dict:
    return json.loads(page.locator("#canvas-wrap").get_attribute("data-graph"))


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
    assert set(graph["nodes"].keys()) == {"n1", "n2", "n3", "n4"}
    assert [graph["nodes"][f"n{i}"]["kind"] for i in range(1, 5)] == list(PALETTE_KINDS)

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
    before = graph["nodes"]["n1"]
    handle = page.locator('.node[data-node-id="n1"] .node__handle')
    handle.focus()
    page.keyboard.press("ArrowRight")
    after = _graph(page)["nodes"]["n1"]
    assert after["x"] == before["x"] + 12
    assert after["y"] == before["y"]


def test_pointer_places_drags_and_connects_nodes(index: LoadedPage) -> None:
    """C2: positions persist as {id, x, y}, edges as an ordered pair list."""
    page = index.page

    page.locator('.palette__add[data-add-kind="Multiplicity"]').click()
    page.locator('.palette__add[data-add-kind="Selection"]').click()

    graph = _graph(page)
    n1_start = graph["nodes"]["n1"]

    # Drag n1 by its handle.
    handle_box = page.locator('.node[data-node-id="n1"] .node__handle').bounding_box()
    start = (handle_box["x"] + handle_box["width"] / 2, handle_box["y"] + handle_box["height"] / 2)
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(start[0] + 30, start[1] + 20)
    page.mouse.up()

    moved = _graph(page)["nodes"]["n1"]
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
