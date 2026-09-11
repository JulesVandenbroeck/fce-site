"""Browser assertions about the three-region app shell (F-004).

Frontend's own markup, on frontend's side of the 2026-09-07 conftest seam
(`.claude/shared/CLAUDE.md` §4): these tests use the harness fixtures from
`tests/e2e/conftest.py` without adding to it.
"""

from tests.e2e.conftest import LoadedPage


def test_three_regions_are_present_as_landmarks(index: LoadedPage) -> None:
    """C1: palette (left), canvas (always present), mission panel (right)."""
    page = index.page
    assert page.locator("aside.palette#palette").count() == 1
    assert page.locator("section.canvas-region#canvas-region").count() == 1
    assert page.locator("aside.mission-panel#mission-panel").count() == 1


def test_canvas_svg_is_present_for_the_graph_to_mount_into(index: LoadedPage) -> None:
    """C1: the canvas is never covered or collapsed -- it always renders an SVG."""
    assert index.page.locator("#canvas-svg #nodes-layer").count() == 1


def test_regions_start_expanded(index: LoadedPage) -> None:
    """Baseline for the collapse/expand tests below."""
    page = index.page
    assert page.locator("#palette").get_attribute("data-state") == "expanded"
    assert page.locator("#mission-panel").get_attribute("data-state") == "expanded"


def test_palette_collapses_by_keyboard(index: LoadedPage) -> None:
    """C2: the palette toggle is operable by keyboard, not only by pointer."""
    page = index.page
    toggle = page.locator("#palette-toggle")
    toggle.focus()
    page.keyboard.press("Enter")
    assert page.locator("#palette").get_attribute("data-state") == "collapsed"
    assert toggle.get_attribute("aria-expanded") == "false"


def test_mission_panel_collapses_by_keyboard(index: LoadedPage) -> None:
    """C2: the mission panel toggle is operable by keyboard, not only by pointer."""
    page = index.page
    toggle = page.locator("#panel-toggle")
    toggle.focus()
    page.keyboard.press("Enter")
    assert page.locator("#mission-panel").get_attribute("data-state") == "collapsed"
    assert toggle.get_attribute("aria-expanded") == "false"


def test_no_inline_style_attributes(index: LoadedPage) -> None:
    """C3: the design role owns all appearance; nothing here may outrank it."""
    assert index.page.locator("[style]").count() == 0


def test_no_inline_script_bodies(index: LoadedPage) -> None:
    """C3: shell.html's inline module script is now static/js/shell.js."""
    scripts = index.page.locator("script").all()
    for script in scripts:
        if script.get_attribute("src") is None:
            assert script.inner_text().strip() == ""


def test_shell_script_is_requested_as_its_own_file(index: LoadedPage) -> None:
    """C3: proves shell.js was actually fetched, not just referenced."""
    assert any(url.endswith("/static/js/shell.js") for url in index.activity.requested_urls)


def test_shell_page_logs_no_console_errors(index: LoadedPage) -> None:
    """C4/C8: console.error output, and uncaught exceptions (a broken module
    import surfaces as a Playwright pageerror, not a console message)."""
    assert index.activity.console_errors == []
    assert index.activity.page_errors == []


def test_shell_page_has_no_bad_responses(index: LoadedPage) -> None:
    """C4."""
    assert index.activity.bad_responses == []


def test_mission_panel_shows_m1_not_a_later_mission(index: LoadedPage) -> None:
    """F-010 C1/C2: the panel is hardcoded to M-1 until mission loading (M5)
    arrives -- no mission-2 or mission-3 text, and no fit talk (M-1 has none).
    Goes red if the M-3 demo copy comes back."""
    body_text = index.page.inner_text("body")
    assert "M-1" in body_text
    assert "First Light" in body_text
    for forbidden in ("M-2", "M-3", "The Unknown", "run a fit"):
        assert forbidden not in body_text


def test_mission_pager_has_nothing_to_page_to(index: LoadedPage) -> None:
    """F-010 C3: only M-1 exists, so both pager buttons are disabled but
    still present with their classes for D-015's CSS to style."""
    page = index.page
    back = page.locator("#pager-back")
    forward = page.locator("#pager-forward")
    assert back.get_attribute("class") == "mission-panel__pager"
    assert forward.get_attribute("class") == "mission-panel__pager"
    assert back.is_disabled()
    assert forward.is_disabled()
