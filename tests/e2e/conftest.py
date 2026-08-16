"""Fixtures that put a real browser in front of a real server.

One server and one browser per session, a fresh browser context per test.
Contexts are cheap and isolated -- no cookie, no cache entry and no service
worker crosses from one test to the next -- while relaunching Chromium per
test would cost more than the whole suite.

Nothing here skips. A missing browser fails the run with the command that
installs one: a harness that quietly reports success on a machine where it
never ran is worse than no harness, because the next person believes it.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Browser, ConsoleMessage, Error, Page, sync_playwright

#: The checkout. Put on ``sys.path`` so ``scripts/`` is importable however
#: pytest was invoked: the server helper the browser tests need is the same
#: one the screenshot tool uses, and it is defined there.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.screenshot import ChromiumUnavailableError, launch_chromium, serve_app  # noqa: E402

#: URL schemes that carry their payload inside the document and so cannot
#: reach another machine: ``data:`` inlines the bytes, ``blob:`` names an
#: object the page itself created. Everything else -- including ``file:`` and
#: ``ws:`` -- is treated as a trip off the origin and must be justified, not
#: assumed harmless.
NON_NETWORK_SCHEMES = frozenset({"data", "blob"})


@dataclass
class PageActivity:
    """Everything the browser reported while a page was open.

    Filled by event listeners rather than by reading source text: a page can
    fetch a URL that appears in no file the server rendered -- built by a
    script, or pulled in by an ``@import`` inside a stylesheet -- and only the
    browser knows about it.
    """

    console_errors: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    requested_urls: list[str] = field(default_factory=list)


@dataclass
class LoadedPage:
    """A page that has finished loading, and what the browser did loading it."""

    page: Page
    activity: PageActivity
    base_url: str


def observe(page: Page) -> PageActivity:
    """Attach collectors to ``page`` and return the record they fill.

    Must be called before the page is navigated: events fired earlier are
    gone, and a collector wired up too late reports an empty list forever.
    """
    activity = PageActivity()

    def on_console(message: ConsoleMessage) -> None:
        if message.type == "error":
            activity.console_errors.append(message.text)

    def on_page_error(error: Error) -> None:
        activity.page_errors.append(error.message)

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("request", lambda request: activity.requested_urls.append(request.url))
    return activity


def off_origin_requests(urls: list[str], base_url: str) -> list[str]:
    """Return the requested ``urls`` that do not belong to ``base_url``.

    Compared as (scheme, host, port) rather than by prefix, so neither a
    lookalike host nor a different port on the same machine slips through.
    """
    origin = _origin(base_url)
    return [url for url in urls if _origin(url) != origin and urlsplit(url).scheme not in NON_NETWORK_SCHEMES]


def _origin(url: str) -> tuple[str, str | None, int | None]:
    """Return the comparable origin of ``url``."""
    parts = urlsplit(url)
    return parts.scheme, parts.hostname, parts.port


@pytest.fixture(name="live_server", scope="session")
def _live_server() -> Iterator[str]:
    """Serve the real application on an ephemeral port for the whole session."""
    with serve_app() as base_url:
        yield base_url


@pytest.fixture(name="browser", scope="session")
def _browser() -> Iterator[Browser]:
    """Launch one headless Chromium for the whole session.

    ``pytest.fail`` rather than ``pytest.skip``: without a browser these tests
    have not passed, and saying so is the whole point of the fixture.
    """
    with sync_playwright() as playwright:
        try:
            browser = launch_chromium(playwright)
        except ChromiumUnavailableError as exc:
            pytest.fail(str(exc), pytrace=False)
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture(name="page")
def _page(browser: Browser) -> Iterator[Page]:
    """Yield a page in its own context, so no state leaks between tests."""
    context = browser.new_context()
    try:
        yield context.new_page()
    finally:
        context.close()


@pytest.fixture(name="index")
def _index(page: Page, live_server: str) -> LoadedPage:
    """Load ``/`` with collectors attached first, and hand back both."""
    activity = observe(page)
    page.goto(f"{live_server}/", wait_until="networkidle")
    return LoadedPage(page=page, activity=activity, base_url=live_server)
