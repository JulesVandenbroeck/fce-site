#!/usr/bin/env python3
"""interior_style_verify.py -- D-018 checkpoint check for the four real node
interiors (Multiplicity, Selection, Observable, Histogram).

Unlike this directory's other `*_verify.py` scripts, there is no exploration
mockup for D-018 to check -- observable.css and canvas.css style the *real*
running app (F-011/F-012's markup, `src/fce_web/static/js/graph.js`), not a
`docs/design-explorations/*.html` page. D-016 (PR #48, the file-scope-cited
precedent for "where a design task's checks live") verified its own work the
same way -- a throwaway Playwright script against the real app, started via
`scripts/screenshot.py::serve_app` -- but did not commit it (its own PR body,
C12: "docs/design-explorations/verify.py untouched"). This script is that
missing, committed half for D-018, kept in this directory because every prior
design-task checker already lives here (`interiors_verify.py`, D-009;
`observable_verify.py`, D-013) even though those check static mockups and this
checks the live server.

Run from the repo root, with a real Chromium available (see
PLAYWRIGHT_BROWSERS_PATH):

    ./.venv/bin/python docs/design-explorations/interior_style_verify.py

What it checks, all against the real running app, the real fixture dataset,
and the real F-011/F-012 markup -- never a re-implementation of it:
  - no-ua-fallback   every native control inside an opened `.node__interior`
                     carries this task's own paper-face styling (a fixed
                     background/border-color pair), not the browser default
                     -- the regression this exists to catch (C6): interior
                     styling silently not applying.
  - fits             the default four-node chain, and the Selection node
                     grown to three rows, both keep every one of their
                     controls' bounding boxes non-overlapping, and produce no
                     page-level horizontal scroll at 1440/1024/768 (C3).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from scripts.screenshot import serve_app  # noqa: E402

FIXTURE_DATASET_DIR = REPO_ROOT / "tests" / "fixtures" / "datasets" / "IDEA" / "91GeV"
CHAIN = ("Multiplicity", "Selection", "Observable", "Histogram")
WIDTHS = (1440, 1024, 768)

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"FAIL: {msg}")


def place_chain(page) -> None:
    for kind in CHAIN:
        page.locator(f'.palette__add[data-add-kind="{kind}"]').click()
    for from_id, to_id in (("n1", "n2"), ("n2", "n3"), ("n3", "n4")):
        out_port = page.locator(f'.node[data-node-id="{from_id}"] .port--out')
        out_port.focus()
        page.keyboard.press("Enter")
        in_port = page.locator(f'.node[data-node-id="{to_id}"] .port--in')
        in_port.focus()
        page.keyboard.press("Enter")


def boxes_overlap(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


# `.selection-rows` deliberately caps its own height and scrolls (D-018,
# observable.css) -- a row past the cap is still in the DOM, at a real
# `getBoundingClientRect()` position, but clipped away and invisible at
# scrollTop 0. That is correct, working overflow, not an overlap a student
# can ever see: this JS clips every interior control's rect against every
# ancestor of it (up to `.node__interior`) that actually clips its own
# overflow, and reports a zero-area rect (skipped below) for one that is
# entirely scrolled out of view.
_VISIBLE_RECTS_JS = """
(nodeSel) => {
  function clip(rect, bound) {
    const x = Math.max(rect.x, bound.x);
    const y = Math.max(rect.y, bound.y);
    const right = Math.min(rect.x + rect.width, bound.x + bound.width);
    const bottom = Math.min(rect.y + rect.height, bound.y + bound.height);
    return { x, y, width: Math.max(0, right - x), height: Math.max(0, bottom - y) };
  }
  const interior = document.querySelector(nodeSel + ' .node__interior[open]');
  if (!interior) return [];
  const out = [];
  interior.querySelectorAll('label, select, input, button, legend').forEach((el) => {
    // `.mode-toggle__opt input[type=radio]` (pre-existing, F-011) is
    // deliberately laid over its own label via `position: absolute` so the
    // whole pill is one click target -- that is one semantic control, not
    // two overlapping ones, and not something D-018 introduced or should
    // flag.
    if (getComputedStyle(el).position === 'absolute') return;
    let rect = el.getBoundingClientRect();
    for (let node = el.parentElement; node && node !== interior.parentElement; node = node.parentElement) {
      const oy = getComputedStyle(node).overflowY;
      if (oy === 'auto' || oy === 'hidden' || oy === 'scroll') {
        rect = clip(rect, node.getBoundingClientRect());
      }
    }
    if (rect.width > 0 && rect.height > 0) {
      out.push({ tag: el.tagName, x: rect.x, y: rect.y, width: rect.width, height: rect.height });
    }
  });
  return out;
}
"""


def check_no_ua_fallback(page) -> None:
    """A control that fell back to the browser default would not have this
    task's paper background/white border pair -- the smallest signal that
    the CSS stopped applying (a selector rename in a review cycle, a
    specificity fight, a class typo)."""
    controls = page.eval_on_selector_all(
        '.node__interior[open] :is(select, input[type="number"], input[type="text"])',
        """els => els.map(e => {
            const s = getComputedStyle(e);
            return { tag: e.tagName, bg: s.backgroundColor, border: s.borderTopColor };
        })""",
    )
    if len(controls) < 6:  # Multiplicity(7) + Histogram(3) alone clear this
        fail(f"expected several styled controls, found {len(controls)}")
        return
    for c in controls:
        if c["bg"] not in ("rgb(244, 236, 218)",):  # --paper
            fail(f"{c['tag']} background is {c['bg']}, not --paper (UA fallback?)")
        if c["border"] not in ("rgb(255, 255, 255)",):  # --node-label-on-fill
            fail(f"{c['tag']} border is {c['border']}, not --node-label-on-fill (UA fallback?)")


def check_fits(pw, base_url: str) -> None:
    for width in WIDTHS:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.goto(f"{base_url}/", wait_until="networkidle")
        place_chain(page)

        # Grow the Selection node (n2) to three rows before opening anything,
        # per C3's explicit "Selection with 3 rows" case.
        page.locator('.node[data-node-id="n2"] .node__interior-summary').focus()
        page.keyboard.press('Enter')
        for _ in range(2):
            # Keyboard, not a mouse click: also proves the "Add condition"
            # button stays reachable once the interior is capped and
            # scrolling (D-018's fix for the sticky-summary dead end -- see
            # observable.css's own comment), and works regardless of
            # whatever the outer canvas-region's own horizontal scroll
            # position happens to be at narrower widths.
            page.locator('.node[data-node-id="n2"] .selection-add').focus()
            page.keyboard.press('Enter')
            page.wait_for_timeout(30)
        if page.locator('.node[data-node-id="n2"] .selection-row').count() != 3:
            fail(f"width {width}: expected 3 selection rows, got a different count")

        for nid in ("n1", "n3", "n4"):
            page.locator(f'.node[data-node-id="{nid}"] .node__interior-summary').focus()
            page.keyboard.press('Enter')
        page.wait_for_timeout(100)

        if width == WIDTHS[0]:
            check_no_ua_fallback(page)
            # C3/C6: a real regression this task hit -- `.node` is a flex
            # column (canvas.css) and a flex item's automatic minimum size
            # stops tracking its content once that item's own `overflow`
            # isn't `visible` (CSS Flexbox's min-size-auto rule). Without
            # `flex-shrink: 0` on `.node__interior[open]`, the interior gets
            # squeezed to fit the *not-yet-grown* node instead of the other
            # way around, `growNode()`'s `scrollHeight` read comes back
            # already-shrunk, and the node never grows past its collapsed
            # 104px -- silently, with no overlap and no UA-fallback colours
            # to catch it (both those checks still pass on the broken CSS).
            n1_height = int(
                page.eval_on_selector('foreignObject[data-node-id="n1"]', "el => el.getAttribute('height')")
            )
            if n1_height < 300:
                fail(f"width {width}: Multiplicity's opened node is only {n1_height}px tall -- grow deadlocked?")

        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        client_w = page.evaluate("document.documentElement.clientWidth")
        if scroll_w > client_w:
            fail(f"width {width}: page scrolls horizontally ({scroll_w} > {client_w})")

        for nid in ("n1", "n2", "n3", "n4"):
            control_boxes = page.evaluate(_VISIBLE_RECTS_JS, f'.node[data-node-id="{nid}"]')
            for i, a in enumerate(control_boxes):
                for b in control_boxes[i + 1:]:
                    if boxes_overlap(a, b):
                        fail(f"width {width}, node {nid}: two interior controls overlap ({a}, {b})")

        browser.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="fce-interior-verify-home-") as fce_home:
        dataset_dir = Path(fce_home, "datasets", "IDEA", "91GeV")
        dataset_dir.parent.mkdir(parents=True)
        os.symlink(FIXTURE_DATASET_DIR, dataset_dir)
        with serve_app(env={"FCE_HOME": fce_home}) as base_url:
            with sync_playwright() as pw:
                check_fits(pw, base_url)

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s).")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
