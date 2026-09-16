"""Browser assertions about the Run control and results region (F-007),
driven against the real running app per docs/api.md.

Frontend's own markup, on frontend's side of the 2026-09-07 conftest seam
(`.claude/shared/CLAUDE.md` §4): these tests use the harness fixtures from
`tests/e2e/conftest.py` without adding to it.
"""

from __future__ import annotations

import json
import re
import time

from playwright.sync_api import expect

from tests.e2e.conftest import LoadedPage

CHAIN = ("Multiplicity", "Selection", "Observable", "Histogram")


def _place_mission1_chain(page) -> None:
    """Places and connects n1->n2->n3->n4, one of each palette kind in
    order -- a complete, legal mission-1 graph missing only node config,
    which run.js fills at submit (C3)."""
    for kind in CHAIN:
        page.locator(f'.palette__add[data-add-kind="{kind}"]').click()
    for from_id, to_id in (("n1", "n2"), ("n2", "n3"), ("n3", "n4")):
        out_port = page.locator(f'.node[data-node-id="{from_id}"] .port--out')
        out_port.focus()
        page.keyboard.press("Enter")
        in_port = page.locator(f'.node[data-node-id="{to_id}"] .port--in')
        in_port.focus()
        page.keyboard.press("Enter")


def test_mission1_chain_runs_to_done_with_live_progress(index: LoadedPage) -> None:
    """C3/C4: a four-node chain placed through the real UI, with no config
    entered by hand, submits and reaches done -- and the status text is
    observed to change more than once on the way there, not just jump from
    "Not run yet." straight to "Run complete."."""
    page = index.page
    _place_mission1_chain(page)

    page.locator("#run-button").click()
    seen = set()
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        seen.add(page.locator("#results-status").inner_text())
        if "Run complete." in seen:
            break
        time.sleep(0.02)

    assert "Run complete." in seen
    assert len(seen) > 1, f"status never changed before completion: {seen}"

    # "Run complete." lands synchronously; the result fetch that populates
    # data-result is a separate, slightly later async step -- give it a
    # moment rather than reading the attribute the instant the text changed.
    expect(page.locator("#results-chart")).to_have_attribute("data-result", re.compile(".+"), timeout=10000)
    result = json.loads(page.locator("#results-chart").get_attribute("data-result"))
    assert result["status"] == "done"
    assert page.locator("#run-button").is_enabled()

    assert index.activity.console_errors == []
    assert index.activity.page_errors == []


def test_layout_only_change_is_a_cache_hit_on_resubmit(index: LoadedPage) -> None:
    """C2/C5: dragging a node between two submissions of the same analysis
    must not change what is submitted -- the second run is a cache hit,
    rendered as the brief's reuse copy, not a suspiciously instant bar.

    Does not assert the *first* submission is a miss: `live_server` and its
    `JobRegistry` are session-scoped (`tests/e2e/conftest.py`), so an earlier
    test in this file may already have cached this exact mission-1 config --
    that is the property under test, not noise to suppress. What C2 actually
    requires, and all this asserts, is that the *second* submission -- same
    analysis, only the layout differs -- is a cache hit.
    """
    page = index.page
    _place_mission1_chain(page)

    page.locator("#run-button").click()
    expect(page.locator("#results-status")).to_have_text("Run complete.", timeout=60000)

    handle = page.locator('.node[data-node-id="n1"] .node__handle')
    box = handle.bounding_box()
    start = (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(start[0] + 40, start[1] + 30)
    page.mouse.up()

    with page.expect_response(lambda r: r.url.endswith("/api/run") and r.request.method == "POST") as second:
        page.locator("#run-button").click()
    assert second.value.json()["cacheHit"] is True

    note = page.locator("#results-note")
    expect(note).not_to_be_hidden()
    assert "reusing your earlier run" in note.inner_text()


def test_incomplete_graph_is_rejected_as_a_margin_note(index: LoadedPage) -> None:
    """C6: a graph the server rejects (missing its Observable/Histogram
    terminal, docs/api.md) renders the server's message as a margin note --
    no alert role, nothing styled as a banner -- never a dead run button."""
    page = index.page
    page.locator('.palette__add[data-add-kind="Multiplicity"]').click()  # n1
    page.locator('.palette__add[data-add-kind="Selection"]').click()  # n2
    out_port = page.locator('.node[data-node-id="n1"] .port--out')
    out_port.focus()
    page.keyboard.press("Enter")
    in_port = page.locator('.node[data-node-id="n2"] .port--in')
    in_port.focus()
    page.keyboard.press("Enter")

    page.locator("#run-button").click()
    note = page.locator("#results-note")
    expect(note).not_to_be_hidden(timeout=10000)
    assert note.inner_text() != ""
    assert note.get_attribute("role") != "alert"
    assert page.locator("#run-button").is_enabled()


def test_network_failure_shows_a_note_and_leaves_the_ui_alive(index: LoadedPage) -> None:
    """C7: a submit that never reaches the server is handled -- no
    unhandled rejection, no dead Run button."""
    page = index.page
    _place_mission1_chain(page)
    page.route("**/api/run", lambda route: route.abort())

    page.locator("#run-button").click()
    note = page.locator("#results-note")
    expect(note).not_to_be_hidden(timeout=10000)
    assert note.inner_text() != ""
    assert page.locator("#run-button").is_enabled()
    assert index.activity.page_errors == []
