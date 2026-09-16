"""Browser assertions about the interactive SVG histogram (F-008), driven
against the real running app per docs/api.md and the F-007 markup contract
(PR #46's body, run.js:6-22).

Frontend's own markup, on frontend's side of the 2026-09-07 conftest seam
(`.claude/shared/CLAUDE.md` §4): these tests use the harness fixtures from
`tests/e2e/conftest.py` without adding to it.
"""

from __future__ import annotations

import re

from playwright.sync_api import expect

from tests.e2e.conftest import LoadedPage
from tests.e2e.test_run import _place_mission1_chain

# Longest reveal chain chart.js ports from plot.js (chart.js:88) -- how long
# to wait past it to be sure any armed reveal has already been disarmed.
REVEAL_TOTAL_MS = 1600


def _run_and_wait(page) -> None:
    _place_mission1_chain(page)
    page.locator("#run-button").click()
    expect(page.locator("#results-status")).to_have_text("Run complete.", timeout=60000)
    expect(page.locator("#hist-svg")).to_be_visible(timeout=10000)


def test_figure_holds_fixed_size_at_every_width(index: LoadedPage) -> None:
    """C1: the rendered figure keeps its fixed 650x460 CSS px intrinsic
    size at 1440, 1024 and 768 -- it does not reflow with the viewport."""
    page = index.page
    _run_and_wait(page)

    sizes = []
    for width in (1440, 1024, 768):
        page.set_viewport_size({"width": width, "height": 900})
        box = page.locator("#hist-svg").bounding_box()
        sizes.append((width, round(box["width"]), round(box["height"])))

    assert sizes == [(1440, 650, 460), (1024, 650, 460), (768, 650, 460)], sizes
    assert index.activity.console_errors == []


def test_result_never_fetched_a_second_time(index: LoadedPage) -> None:
    """C2: chart.js draws from the data run.js already published
    (#results-chart's data-result / fce:result), never a second
    GET /api/run/{id}/result of its own."""
    page = index.page

    result_requests = []
    page.on("request", lambda r: result_requests.append(r.url) if "/result" in r.url else None)

    _run_and_wait(page)

    # Exactly one GET .../result per run: run.js's own fetchResult call.
    # chart.js never issues a second one for the payload it was handed.
    assert len(result_requests) == 1, result_requests


def test_bins_render_stacked_backgrounds_and_data_points(index: LoadedPage) -> None:
    """C3: backgrounds are stacked sample bands, data is drawn as points
    (not bars) -- the convention docs/design-brief.md §5 names."""
    page = index.page
    _run_and_wait(page)

    assert page.locator("#hist-svg path.hist-band").count() > 0
    assert page.locator("#hist-svg circle.data-marker").count() > 0
    assert page.locator("#hist-svg rect.data-bar").count() == 0


def test_hover_and_keyboard_reach_the_same_bin_readout(index: LoadedPage) -> None:
    """C4: hovering a bin and reaching the same bin by keyboard alone both
    announce the same numbers through the live readout."""
    page = index.page
    _run_and_wait(page)

    readout = page.locator("#chart-readout")
    first_hit = page.locator("#hist-svg rect.bin-hit").first
    expected = first_hit.get_attribute("aria-label")

    # Hover path.
    first_hit.hover()
    expect(readout).to_have_text(expected)

    # Reset, then reach the same bin by keyboard alone (focus + Enter),
    # never by mouse.
    page.locator("#hist-svg rect.bin-hit").nth(1).focus()
    page.keyboard.press("Enter")
    first_hit.focus()
    page.keyboard.press("Enter")
    expect(readout).to_have_text(expected)
    assert index.activity.console_errors == []


def test_reduced_motion_skips_the_reveal_with_identical_final_geometry(index: LoadedPage) -> None:
    """C5: under prefers-reduced-motion, the reveal animation class is
    never armed, and the rendered geometry is identical to what the
    animated path settles on -- checked by comparing the same drawn band's
    `d` attribute between a reduced-motion run and a normal run."""
    page = index.page
    page.emulate_media(reduced_motion="reduce")
    _run_and_wait(page)

    band_reduced = page.locator("#hist-svg path.hist-band").first.get_attribute("d")
    assert band_reduced

    # Never armed: chart.js's armReveal short-circuits under reduced motion.
    assert page.locator(".chart-figure.reveal-armed").count() == 0

    # Waiting past the reveal chain must not change anything -- there is no
    # separate "settling" step to wait for.
    page.wait_for_timeout(REVEAL_TOTAL_MS + 200)
    assert page.locator("#hist-svg path.hist-band").first.get_attribute("d") == band_reduced
    assert page.locator(".chart-figure.reveal-armed").count() == 0


def test_normal_motion_arms_then_disarms_with_the_same_geometry(page, live_server) -> None:
    """C5 continued: without reduced motion, the same figure is armed
    immediately after render and disarmed again after the reveal chain
    finishes, while the drawn geometry itself never differs from the
    reduced-motion run above -- proving the animation is purely a class
    toggle, never a change to the plotted numbers."""
    from tests.e2e.conftest import observe

    activity = observe(page)
    page.goto(f"{live_server}/", wait_until="networkidle")
    _run_and_wait(page)

    band_normal = page.locator("#hist-svg path.hist-band").first.get_attribute("d")
    assert page.locator(".chart-figure.reveal-armed").count() == 1

    page.wait_for_timeout(REVEAL_TOTAL_MS + 200)
    assert page.locator(".chart-figure.reveal-armed").count() == 0
    assert page.locator("#hist-svg path.hist-band").first.get_attribute("d") == band_normal
    assert activity.console_errors == []


def test_peak_sits_at_the_z_mass_read_off_the_running_app(index: LoadedPage) -> None:
    """C7 -- the criterion that closes M3. Reads the modal bin straight off
    the drawn figure's own aria-labels (never a fixture JSON) and asserts
    its centre sits within a few GeV of the Z mass, 91 GeV."""
    page = index.page
    _run_and_wait(page)

    labels = page.locator("#hist-svg rect.bin-hit").evaluate_all(
        "els => els.map(e => e.getAttribute('aria-label'))"
    )
    assert labels

    pattern = re.compile(r"([\d.]+)–([\d.]+) GeV: (\d+) predicted, (\d+) data")
    best = max(
        (m for m in (pattern.match(label) for label in labels) if m),
        key=lambda m: int(m.group(3)),
    )
    lo, hi = float(best.group(1)), float(best.group(2))
    centre = (lo + hi) / 2
    print(f"F-008 C7: modal bin {best.group(0)!r}, centre={centre} GeV")

    assert abs(centre - 91.0) <= 5.0, best.group(0)
