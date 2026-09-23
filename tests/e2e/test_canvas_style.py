"""One test guarding the D-022 canvas-frame port: shell.css's overlay frame
onto the merged F-015 markup (`.frame`, `.canvas-region`, `.canvas-wrap`,
`.palette`, `.mission-panel`, `.drawer`).

Asserts only computed style and layout of design's own CSS -- no markup
structure, no JS behaviour, no harness -- per the D-022 dispatch's explicit
ruling on a design-owned e2e guard (following D-018's
tests/e2e/test_interior_style.py precedent).
"""

from __future__ import annotations

from playwright.sync_api import Browser

WIDTHS = (1440, 1024, 768)


def test_canvas_wrap_scrolls_and_overlays_are_absolute(browser: Browser, live_server: str) -> None:
    """C1: #canvas-wrap has real horizontal AND vertical scroll range at
    every width. C2: #palette/#mission-panel are overlays (position not
    static) and #canvas-region's width tracks #frame's within 2px."""
    for width in WIDTHS:
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        try:
            page.goto(f"{live_server}/", wait_until="networkidle")

            scroll_w, client_w, scroll_h, client_h = page.eval_on_selector(
                "#canvas-wrap",
                "el => [el.scrollWidth, el.clientWidth, el.scrollHeight, el.clientHeight]",
            )
            assert scroll_w > client_w, (width, scroll_w, client_w)
            assert scroll_h > client_h, (width, scroll_h, client_h)

            if width == WIDTHS[0]:
                palette_pos, panel_pos = page.eval_on_selector_all(
                    "#palette, #mission-panel", "els => els.map(e => getComputedStyle(e).position)"
                )
                assert palette_pos != "static", palette_pos
                assert panel_pos != "static", panel_pos

                frame_w = page.eval_on_selector("#frame", "el => el.getBoundingClientRect().width")
                region_w = page.eval_on_selector("#canvas-region", "el => el.getBoundingClientRect().width")
                assert abs(frame_w - region_w) <= 2, (frame_w, region_w)
        finally:
            context.close()


def _drawer_at_bottom_edge(page) -> None:
    """F2: `is_visible()` alone stays true for an element below the fold, so
    it certified the drawer green while it sat off-screen (cycle 1). This
    checks the property that actually matters -- the drawer's own bottom
    edge against the real viewport, and that the page never scrolls to
    reach it."""
    bottom, inner_h, doc_h = page.evaluate(
        "() => [document.getElementById('drawer').getBoundingClientRect().bottom,"
        " window.innerHeight, document.documentElement.scrollHeight]"
    )
    assert bottom <= inner_h + 1, (bottom, inner_h)
    assert doc_h <= inner_h + 1, (doc_h, inner_h)


def test_canvas_top_left_is_not_covered_by_a_panel(browser: Browser, live_server: str) -> None:
    """C11: with the palette at its default `data-state="expanded"`, the
    canvas surface's own top-left occupiable point (just inside
    `#canvas-wrap`'s padding, D-022 cycle 2's F4 fix) resolves to the canvas
    or a node -- never the palette or mission panel sitting over it."""
    for width in WIDTHS:
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        try:
            page.goto(f"{live_server}/", wait_until="networkidle")

            covered = page.evaluate(
                "() => {"
                " const wrap = document.getElementById('canvas-wrap');"
                " const rect = wrap.getBoundingClientRect();"
                " const padLeft = parseFloat(getComputedStyle(wrap).paddingLeft);"
                " const x = rect.left + padLeft + 2;"
                " const y = rect.top + 2;"
                " const el = document.elementFromPoint(x, y);"
                " return !!(el && el.closest('.palette, .palette__head, .mission-panel'));"
                "}"
            )
            assert not covered, width
        finally:
            context.close()


def test_zoom_controls_are_clickable_over_both_panels(browser: Browser, live_server: str) -> None:
    """C2 (D-023): each zoom button hit-tests as itself -- elementFromPoint at
    its own centre returns the button or a descendant, never the palette or
    mission panel sitting under `.zoom-controls`' toolbar -- with the palette
    both expanded and collapsed, and the mission panel expanded, at every
    width."""
    for width in WIDTHS:
        for collapse_palette in (False, True):
            context = browser.new_context(viewport={"width": width, "height": 900})
            page = context.new_page()
            try:
                page.goto(f"{live_server}/", wait_until="networkidle")
                if collapse_palette:
                    page.locator("#palette-toggle").click()

                for button_id in ("zoom-out", "zoom-in", "zoom-fit"):
                    hits_self = page.evaluate(
                        "(id) => {"
                        " const btn = document.getElementById(id);"
                        " const r = btn.getBoundingClientRect();"
                        " const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
                        " return !!(el && el.closest('#' + id) === btn);"
                        "}",
                        button_id,
                    )
                    assert hits_self, (width, collapse_palette, button_id)
            finally:
                context.close()


def test_drawer_states_render_correctly(browser: Browser, live_server: str) -> None:
    """C3: the drawer sits at the bottom edge of the viewport -- not merely
    visible, actually reachable without scrolling the page -- and both
    `data-state` values render correctly (collapsed hides `#drawer-body` via
    the `hidden` attribute HTML already forces; expanded shows `#results`)."""
    for width in WIDTHS:
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        try:
            page.goto(f"{live_server}/", wait_until="networkidle")

            assert page.locator("#drawer").get_attribute("data-state") == "collapsed"
            assert not page.locator("#drawer-body").is_visible()
            _drawer_at_bottom_edge(page)

            page.locator("#drawer-toggle").click()
            assert page.locator("#drawer").get_attribute("data-state") == "expanded"
            assert page.locator("#drawer-body").is_visible()
            assert page.locator("#results").is_visible()
            _drawer_at_bottom_edge(page)
        finally:
            context.close()
