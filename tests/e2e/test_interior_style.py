"""One test guarding the four node interiors' styling (D-018).

Uses the existing `browser`/`live_server` fixtures from `tests/e2e/conftest.py`,
adding none. Guards a control falling back to UA default colours, and
`.node__interior[open]` losing `flex-shrink: 0` and silently deadlocking
`growNode()`'s height measurement.
"""

from __future__ import annotations

from playwright.sync_api import Browser

from tests.e2e.test_run import _place_mission1_chain

WIDTHS = (1440, 1024, 768)


def test_interior_styling_and_fit(browser: Browser, live_server: str) -> None:
    """Every native control inside an opened interior carries the
    paper/label-on-fill colours (not a UA fallback), Multiplicity's opened
    node reaches its full grown height (not deadlocked by a missing
    `flex-shrink: 0`), and no width produces page-level horizontal scroll.
    """
    for width in WIDTHS:
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        try:
            page.goto(f"{live_server}/", wait_until="networkidle")
            _place_mission1_chain(page)

            # Selection (n2) grown to three rows, per C3.
            page.locator('.node[data-node-id="n2"] .node__interior-summary').focus()
            page.keyboard.press("Enter")
            for _ in range(2):
                page.locator('.node[data-node-id="n2"] .selection-add').focus()
                page.keyboard.press("Enter")
                page.wait_for_timeout(30)
            assert page.locator('.node[data-node-id="n2"] .selection-row').count() == 3

            for nid in ("n1", "n3", "n4"):
                page.locator(f'.node[data-node-id="{nid}"] .node__interior-summary').focus()
                page.keyboard.press("Enter")
            page.wait_for_timeout(100)

            if width == WIDTHS[0]:
                controls = page.eval_on_selector_all(
                    '.node__interior[open] :is(select, input[type="number"], input[type="text"])',
                    """els => els.map(e => {
                        const s = getComputedStyle(e);
                        return { tag: e.tagName, bg: s.backgroundColor, border: s.borderTopColor };
                    })""",
                )
                # Multiplicity(7) + Histogram(3) alone clear this.
                assert len(controls) >= 6, controls
                for c in controls:
                    assert c["bg"] == "rgb(244, 236, 218)", c  # --paper
                    assert c["border"] == "rgb(255, 255, 255)", c  # --node-label-on-fill

                n1_height = int(
                    page.eval_on_selector('foreignObject[data-node-id="n1"]', "el => el.getAttribute('height')")
                )
                assert n1_height >= 300, n1_height

            scroll_w = page.evaluate("document.documentElement.scrollWidth")
            client_w = page.evaluate("document.documentElement.clientWidth")
            assert scroll_w <= client_w, (width, scroll_w, client_w)
        finally:
            context.close()
