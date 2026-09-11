"""Prove the four self-hosted woff2 fonts are actually requested and served
(F-003). tokens.css declares four @font-face rules, but nothing used
--font-body/--font-mono until D-015 -- so "no font 404s" used to pass because
no face was ever fetched. This proves the fetch, not just the absence of a
404.

Two of the four are painted by the app as it already renders: <h1> and body
text use --font-body (EB Garamond roman), and .mission-panel__code sets
--font-mono at font-weight: 600 (--weight-semibold, inherited from
.mission-panel__label) which Chromium's font matching resolves to the
nearest declared static weight below it, the 500 face. The other two --
EB Garamond italic and Fira Mono 400 -- are not set by any rule in
shell.css/canvas.css/observable.css today, so nothing on the page paints
them; they are forced with document.fonts.load(), which is acceptable per
F-003 C1 for a face nothing paints.
"""

from __future__ import annotations

from playwright.sync_api import Page

#: URL suffix -> human label, for all four @font-face src paths in tokens.css.
FONT_PATHS = {
    "/static/fonts/eb-garamond-roman-var.woff2": "EB Garamond roman",
    "/static/fonts/eb-garamond-italic-var.woff2": "EB Garamond italic",
    "/static/fonts/fira-mono-400.woff2": "Fira Mono 400",
    "/static/fonts/fira-mono-500.woff2": "Fira Mono 500",
}


def test_all_four_fonts_are_requested_and_served(page: Page, live_server: str) -> None:
    """C1/C2: all four woff2 URLs are requested while loading the app, each by
    name, and each response is a 200.
    """
    statuses: dict[str, int] = {}
    page.on(
        "response",
        lambda response: statuses.__setitem__(response.url, response.status)
        if "/static/fonts/" in response.url
        else None,
    )

    page.goto(f"{live_server}/", wait_until="networkidle")
    # Force the two faces nothing currently paints (see module docstring).
    # document.fonts.load() rejects on a failed fetch, which would otherwise
    # abort this evaluate() before the per-font assertions below run and
    # could name the broken font -- swallow that here, the status check
    # catches it.
    page.evaluate(
        """async () => {
            try { await document.fonts.load('italic 400 16px "EB Garamond"'); } catch (e) {}
            try { await document.fonts.load('400 16px "Fira Mono"'); } catch (e) {}
        }"""
    )
    page.wait_for_load_state("networkidle")

    for path, label in FONT_PATHS.items():
        matches = {url: status for url, status in statuses.items() if url.endswith(path)}
        assert matches, f"{label} ({path}) was never requested"
        assert list(matches.values()) == [200] * len(matches), f"{label} ({path}) did not return 200: {matches}"
