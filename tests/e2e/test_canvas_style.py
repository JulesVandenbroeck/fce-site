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


def test_drawer_states_render_correctly(browser: Browser, live_server: str) -> None:
    """C3: collapsed does not cover the canvas (the body is display:none via
    the `hidden` attribute HTML already forces); expanded shows #results."""
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    try:
        page.goto(f"{live_server}/", wait_until="networkidle")

        assert page.locator("#drawer").get_attribute("data-state") == "collapsed"
        assert not page.locator("#drawer-body").is_visible()

        page.locator("#drawer-toggle").click()
        assert page.locator("#drawer").get_attribute("data-state") == "expanded"
        assert page.locator("#drawer-body").is_visible()
        assert page.locator("#results").is_visible()
    finally:
        context.close()
