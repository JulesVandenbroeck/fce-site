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


def test_mission1_chain_runs_to_done(index: LoadedPage) -> None:
    """C3: a four-node chain placed through the real UI, with no config
    entered by hand, submits and reaches done. (C4's live-rendering claim
    is proven separately, by test_sse_frames_render_live_not_in_one_jump --
    cycle 2 F1/F2: this fixture run is too fast to observe frame-by-frame
    on the real engine, so it is not this test's job to prove that.)"""
    page = index.page
    _place_mission1_chain(page)

    page.locator("#run-button").click()
    expect(page.locator("#results-status")).to_have_text("Run complete.", timeout=60000)

    # "Run complete." lands synchronously; the result fetch that populates
    # data-result is a separate, slightly later async step -- give it a
    # moment rather than reading the attribute the instant the text changed.
    expect(page.locator("#results-chart")).to_have_attribute("data-result", re.compile(".+"), timeout=10000)
    result = json.loads(page.locator("#results-chart").get_attribute("data-result"))
    assert result["status"] == "done"
    assert page.locator("#run-button").get_attribute("aria-disabled") == "false"

    assert index.activity.console_errors == []
    assert index.activity.page_errors == []


def test_sse_frames_render_live_not_in_one_jump(index: LoadedPage) -> None:
    """C4/C13: the client renders each SSE frame as it arrives, not just a
    single jump from "Not run yet." to "Run complete.".

    Stubs both endpoints (cycle 2 F2) rather than depending on how fast the
    real engine happens to run against the fixture dataset -- a controlled
    stream is what lets this assert on something only a frame could have
    produced: a phase name that is not a client-local string at all.

    The mutation this guards against, and the bar cycle 1 failed to clear:
    deleting the two SSE-driven status writes in run.js (the `phase` and
    `progress` branches of streamRun's `onmessage`) must turn this red. See
    the PR body's C13 mutation transcript.
    """
    page = index.page
    run_id = "stub-run-1"

    def fulfill_run(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"runId": run_id, "cacheHit": False}),
        )

    frames = [
        {"type": "phase", "phase": "reading events", "runId": run_id},
        {"type": "progress", "value": 0.5, "runId": run_id},
        {"type": "phase", "phase": "filling histogram", "runId": run_id},
        {"type": "done", "status": "done", "runId": run_id},
    ]
    sse_body = "".join(f"data: {json.dumps(f)}\n\n" for f in frames)

    def fulfill_events(route):
        route.fulfill(status=200, content_type="text/event-stream", body=sse_body)

    def fulfill_result(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {"status": "done", "cacheHit": False, "meta": {}, "edges": [], "samples": [], "data": []}
            ),
        )

    page.route("**/api/run", fulfill_run)
    page.route(f"**/api/run/{run_id}/events", fulfill_events)
    page.route(f"**/api/run/{run_id}/result", fulfill_result)

    # Record every value #results-status takes, from before the click to
    # after completion, via a MutationObserver installed ahead of time --
    # polling from Python would risk missing a frame between reads, since
    # the stubbed stream (unlike a real run) can resolve within one tick.
    page.evaluate(
        """() => {
          window.__fceStatusHistory = [];
          const el = document.getElementById('results-status');
          window.__fceStatusHistory.push(el.textContent);
          new MutationObserver(() => window.__fceStatusHistory.push(el.textContent))
            .observe(el, { childList: true, characterData: true, subtree: true });
        }"""
    )

    _place_mission1_chain(page)
    page.locator("#run-button").click()
    expect(page.locator("#results-status")).to_have_text("Run complete.", timeout=10000)

    history = page.evaluate("window.__fceStatusHistory")
    # A phase frame's own text landed verbatim in #results-status at some
    # point -- not derivable from any client-local string ("Not run yet.",
    # "Submitting…", "Run complete."). This is exactly what goes missing if
    # the phase/progress branches of streamRun's onmessage are deleted.
    assert "reading events" in history or "filling histogram" in history, history


def test_no_layout_keys_reach_the_submitted_payload(index: LoadedPage) -> None:
    """C12: the POST body's nodes carry no `x`/`y`, checked directly on the
    request rather than inferred from a cache hit (cycle 2 F3 -- a mutated
    client that stamps a fresh x/y onto every node on every submit still
    produces a cache hit server-side, so C2's own check cannot see this).
    See the PR body's C12 mutation transcript for the red run."""
    page = index.page
    _place_mission1_chain(page)

    with page.expect_request(lambda r: r.url.endswith("/api/run") and r.method == "POST") as req_info:
        page.locator("#run-button").click()
    body = req_info.value.post_data_json
    for node in body["graph"]["nodes"]:
        assert "x" not in node and "y" not in node, node


def test_starting_a_new_run_clears_a_stale_result(index: LoadedPage) -> None:
    """C14: a run that ends in error or is rejected must not leave the
    previous run's histogram on #results-chart -- F-008 reads its
    data-result attribute and the published contract says it renders
    whatever is there. run.js's resetResults clears the attribute
    synchronously at the start of every run (cycle 2 F4), so a second click
    -- checked immediately, before that run's own outcome is known --
    already proves the stale payload is gone."""
    page = index.page
    _place_mission1_chain(page)

    page.locator("#run-button").click()
    expect(page.locator("#results-chart")).to_have_attribute("data-result", re.compile(".+"), timeout=60000)

    page.locator("#run-button").click()
    assert page.locator("#results-chart").get_attribute("data-result") is None
    expect(page.locator("#results-status")).to_have_text("Run complete.", timeout=60000)

    # C14 (cycle 3, F12): a graph that fails to serialise client-side --
    # buildSubmission() throwing on a corrupted data-graph -- returns before
    # ever reaching the network. That early-return path must still clear a
    # stale data-result; it was the one route resetResults() didn't run.
    page.evaluate("document.getElementById('canvas-wrap').setAttribute('data-graph', 'not json')")
    page.locator("#run-button").click()
    assert page.locator("#results-chart").get_attribute("data-result") is None
    expect(page.locator("#results-note")).not_to_be_hidden()


def test_run_button_keeps_focus_while_running(index: LoadedPage) -> None:
    """C15: the Run control does not cost the keyboard user their place --
    it is marked busy with aria-disabled, not the disabled attribute, which
    would drop focus to <body> mid-run (cycle 2 F5).

    Delays the SSE connection (real request, real server, just held up in
    transit) rather than checking "running" state immediately after the
    click: by this point in the file the mission-1 default graph has
    usually already been run and cached earlier in this session, so an
    uninstrumented run can finish between the keypress and the next line of
    Python -- flaky, not a product bug. The delay guarantees a "running"
    window long enough to observe.
    """
    page = index.page
    _place_mission1_chain(page)

    def delay_events(route):
        time.sleep(0.3)
        route.continue_()

    page.route("**/api/run/*/events", delay_events)

    page.locator("#run-button").focus()
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "run-button"
    assert page.locator("#run-button").get_attribute("aria-disabled") == "true"

    expect(page.locator("#results-status")).to_have_text("Run complete.", timeout=60000)
    assert page.locator("#run-button").get_attribute("aria-disabled") == "false"
    assert page.evaluate("document.activeElement.id") == "run-button"


def test_layout_only_change_is_a_cache_hit_on_resubmit(index: LoadedPage) -> None:
    """C2/C5: dragging a node between two submissions of the same analysis
    must not change what is submitted -- the second run is a cache hit,
    rendered as the brief's reuse copy, not a suspiciously instant bar.

    Does not assert the *first* submission is a miss: `live_server` and its
    `JobRegistry` are session-scoped (`tests/e2e/conftest.py`), so an earlier
    test in this file may already have cached this exact mission-1 config --
    that is the property under test, not noise to suppress. What C2 actually
    requires, and all this asserts, is that the *second* submission -- same
    analysis, only the layout differs -- is a cache hit. (C12, above, is what
    proves layout never reaches the payload in the first place.)
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
    assert page.locator("#run-button").get_attribute("aria-disabled") == "false"


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
    assert page.locator("#run-button").get_attribute("aria-disabled") == "false"
    assert index.activity.page_errors == []
