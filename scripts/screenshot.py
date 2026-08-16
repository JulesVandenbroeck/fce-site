#!/usr/bin/env python3
"""Boot the app and photograph one of its routes at three widths.

Run it with a route and nothing else::

    python scripts/screenshot.py /
    python scripts/screenshot.py /missions/1 --out ~/shots

It starts the real application on a port the kernel picks, drives a headless
Chromium against it, writes one full-page PNG per width, prints their absolute
paths, and shuts everything down. No server needs to be running first, and no
argument beyond the route is needed -- the design role and the reviewer run
this unattended.

Images default to a fresh temp directory and may never be written inside the
checkout: no PNG is ever committed to this repository.

The serving helpers live here rather than in the test tree because the pytest
end-to-end harness imports them (``tests/e2e/conftest.py``): one
implementation of "start the real application on an ephemeral port", exercised
by both callers.
"""

from __future__ import annotations

import argparse
import re
import socket
import sys
import tempfile
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import uvicorn
from playwright.sync_api import (
    Browser,
    Error as PlaywrightError,
    Page,
    Playwright,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from fce_web.app import create_app

#: Loopback only. The harness must never expose a test server to the LAN.
HOST = "127.0.0.1"

#: Seconds to wait for the server to report itself started before giving up.
STARTUP_TIMEOUT = 20.0

#: Seconds to wait for the server thread to unwind after shutdown is asked for.
SHUTDOWN_TIMEOUT = 10.0

#: Polling interval while waiting for startup.
POLL_INTERVAL = 0.02

#: Name given to the thread running the server, so a leaked one is
#: identifiable in ``threading.enumerate()`` rather than anonymous.
SERVER_THREAD_NAME = "fce-e2e-server"

#: Viewport widths, in CSS pixels: a laptop, a small laptop, and a tablet in
#: portrait. Chosen to straddle the layout breakpoints the design role works
#: to, so one run shows how a page reflows rather than only how it looks.
WIDTHS = (1440, 1024, 768)

#: Viewport height. Only the starting height -- every capture is full-page, so
#: a taller page produces a taller image.
VIEWPORT_HEIGHT = 900

#: Milliseconds a navigation is given to reach ``networkidle`` before it is
#: treated as stuck rather than merely slow. Playwright's own default -- named
#: here so the failure message can state it, rather than a person reading a
#: bare ``TimeoutError`` having to know what Playwright would have waited for.
NAVIGATION_TIMEOUT_MS = 30_000

#: Prefix for the generated output directory, so stray runs are recognisable
#: in the system temp directory.
OUTPUT_DIR_PREFIX = "fce-screenshots-"

#: The checkout, ``scripts/`` being directly inside it. Nothing may be written
#: here: PNGs are build output and are never committed.
REPO_ROOT = Path(__file__).resolve().parents[1]

#: What to tell someone whose machine has no browser. Playwright ships none by
#: default, and on a machine where its default directory is not writable the
#: download silently lands somewhere the run cannot find, so name both halves.
CHROMIUM_MISSING_HINT = (
    "Chromium is not available to Playwright. Install it with:\n"
    "    python -m playwright install chromium\n"
    "If the default browser directory is not writable, choose one and set it for "
    "both that command and every run:\n"
    '    export PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/ms-playwright"'
)


class ScreenshotError(RuntimeError):
    """A failure worth reporting to the person who ran the tool."""


class ChromiumUnavailableError(ScreenshotError):
    """Raised when Playwright cannot start Chromium."""


class OutputDirectoryError(ScreenshotError):
    """Raised when the requested output directory may not be written to."""


class RouteNotServedError(ScreenshotError):
    """Raised when the app does not serve the requested route."""


@contextmanager
def serve_app(startup_timeout: float = STARTUP_TIMEOUT) -> Iterator[str]:
    """Run the real application on an ephemeral port; yield its base URL.

    The port is chosen by the kernel (``bind`` to port 0) and read back from
    the bound socket, so concurrent harnesses never collide and nothing
    depends on a port being free.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((HOST, 0))
        port = sock.getsockname()[1]
        config = uvicorn.Config(create_app(), log_level="warning", access_log=False)
        server = uvicorn.Server(config)
        thread = threading.Thread(
            target=server.run,
            kwargs={"sockets": [sock]},
            name=SERVER_THREAD_NAME,
            daemon=True,
        )
        thread.start()
        try:
            _wait_until_started(server, thread, startup_timeout)
            yield f"http://{HOST}:{port}"
        finally:
            server.should_exit = True
            thread.join(timeout=SHUTDOWN_TIMEOUT)
    finally:
        sock.close()


def _wait_until_started(
    server: uvicorn.Server, thread: threading.Thread, timeout: float
) -> None:
    """Block until ``server`` accepts connections, or fail loudly."""
    deadline = time.monotonic() + timeout
    while not server.started:
        if not thread.is_alive():
            raise RuntimeError("the server thread exited before the application started")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"the application did not start within {timeout:g}s")
        time.sleep(POLL_INTERVAL)


def launch_chromium(playwright: Playwright) -> Browser:
    """Return a headless Chromium, or fail with instructions for installing one.

    Playwright raises a generic error for a missing browser, which reads as a
    broken harness rather than as a one-line fix. Anyone can be told the
    command.
    """
    try:
        return playwright.chromium.launch()
    except PlaywrightError as exc:
        raise ChromiumUnavailableError(f"{CHROMIUM_MISSING_HINT}\n\nPlaywright said: {exc}") from exc


def resolve_output_dir(requested: str | None) -> Path:
    """Return the directory to write images into, creating it if needed.

    ``None`` means "somewhere temporary". A path inside the checkout is
    refused outright: PNGs are build output, and one committed by accident is
    a repository nobody wants to clone.
    """
    if requested is None:
        return Path(tempfile.mkdtemp(prefix=OUTPUT_DIR_PREFIX))

    output_dir = Path(requested).expanduser().resolve()
    if output_dir == REPO_ROOT or REPO_ROOT in output_dir.parents:
        raise OutputDirectoryError(
            f"refusing to write screenshots into the repository at {REPO_ROOT}: "
            "images are build output and must not be committed. Leave --out off to use a "
            "temp directory, or point it somewhere outside the checkout."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def image_name(route: str, width: int) -> str:
    """Return the file name for ``route`` at ``width``.

    ``/`` becomes ``index``; anything else is flattened to letters, digits and
    hyphens, so a route with a slash or a query string still yields a sane
    file name.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", route).strip("-").lower() or "index"
    return f"{slug}-{width}.png"


def _goto_or_raise(page: Page, url: str, timeout_ms: float) -> Response | None:
    """Navigate ``page`` to ``url``; turn a stuck load into the tool's own words.

    ``networkidle`` never fires while something on the page keeps a request
    open -- a long ``fetch()``, an SSE stream, a WebSocket that never closes.
    Left unguarded, that surfaces after ``timeout_ms`` as a bare Playwright
    ``TimeoutError`` -- no PNG, no explanation, and every caller of this tool
    catches only ``ScreenshotError``. Converting it here keeps that promise:
    a stuck page is reported the same way a 404 or a missing browser is.
    """
    try:
        return page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError as exc:
        raise RouteNotServedError(
            f"{url} did not settle within {timeout_ms / 1000:g}s -- is something on the page "
            "holding a request open?"
        ) from exc


def capture(route: str, output_dir: Path, widths: Sequence[int] = WIDTHS) -> list[Path]:
    """Photograph ``route`` at each width and return the files written.

    One page per width rather than one page resized: a fresh page re-runs the
    layout from scratch, which is what a student's browser does and what the
    design role needs to see.
    """
    written: list[Path] = []
    with serve_app() as base_url, sync_playwright() as playwright:
        url = f"{base_url}/{route.lstrip('/')}"
        browser = launch_chromium(playwright)
        try:
            for width in widths:
                page = browser.new_page(viewport={"width": width, "height": VIEWPORT_HEIGHT})
                try:
                    response = _goto_or_raise(page, url, NAVIGATION_TIMEOUT_MS)
                    if response is None or not response.ok:
                        status = "no response" if response is None else response.status
                        raise RouteNotServedError(
                            f"{url} returned {status}, so there is nothing worth photographing"
                        )
                    destination = output_dir / image_name(route, width)
                    page.screenshot(path=destination, full_page=True)
                    written.append(destination)
                finally:
                    page.close()
        finally:
            browser.close()
    return written


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool; return the process exit status."""
    args = _parse_args(argv)
    try:
        output_dir = resolve_output_dir(args.out)
        written = capture(args.route, output_dir)
    except ScreenshotError as exc:
        print(exc, file=sys.stderr)
        return 1

    for path in written:
        print(path)
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        description="Boot the app and write full-page screenshots of one route.",
    )
    parser.add_argument("route", help="route to photograph, e.g. / or /missions/1")
    parser.add_argument(
        "--out",
        default=None,
        metavar="DIR",
        help="directory to write into; defaults to a fresh temp directory. "
             "Must be outside the repository.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
