"""Smoke tests: what a real browser does with the real server.

The later groups test the harness itself, because the reviewer and the design
role depend on it running unattended. A test server that picked a fixed port
would fail whenever a colleague, a stale process, or a second run of this
suite already held it, and one that outlived its ``with`` block would leak a
listening socket per failure -- so both properties are asserted rather than
assumed. The screenshot tool is driven the way its callers drive it: as a
command line, in a subprocess, from an unrelated working directory.
"""

import http.server
import json
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Error as PlaywrightError, Page

from scripts.screenshot import (
    HOST,
    SERVER_THREAD_NAME,
    WIDTHS,
    ChromiumUnavailableError,
    RouteNotServedError,
    _goto_or_raise,
    launch_chromium,
    resolve_output_dir,
    serve_app,
)
from tests.e2e.conftest import REPO_ROOT, LoadedPage, off_origin_requests

#: Seconds to wait when probing a port that should no longer be listening.
CONNECT_TIMEOUT = 2.0

#: The screenshot tool, invoked by path exactly as a person would invoke it.
SCREENSHOT_SCRIPT = REPO_ROOT / "scripts" / "screenshot.py"

#: Generous ceiling for one scripted run: boot, launch Chromium, three shots.
SCRIPT_TIMEOUT = 180.0

#: First eight bytes of any PNG file.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: A host reserved by RFC 2606 to never resolve, used to prove the off-origin
#: check fires. Chromium reports the attempt whether or not it can be made, so
#: this works on a machine with no route off the LAN -- which is the machine
#: the whole project targets.
OFF_ORIGIN_PROBE = "https://blocked.invalid/probe.png"


def test_index_page_shows_its_heading(index: LoadedPage) -> None:
    """Chromium renders the landing page, not an error page or a blank body."""
    assert index.page.locator("h1").inner_text().strip() == "FCE-site"


def test_index_page_logs_no_console_errors(index: LoadedPage) -> None:
    """Nothing the page loads writes an error to the console."""
    assert index.activity.console_errors == []


def test_index_page_raises_no_page_errors(index: LoadedPage) -> None:
    """No script on the page throws an uncaught exception."""
    assert index.activity.page_errors == []


def test_index_page_requests_its_own_document(index: LoadedPage) -> None:
    """The request collector saw the navigation, so an empty offender list means something."""
    assert f"{index.base_url}/" in index.activity.requested_urls


def test_index_page_requests_nothing_off_origin(index: LoadedPage) -> None:
    """Every URL the browser fetched belongs to the test server (§3: no CDNs, no remote fonts)."""
    assert off_origin_requests(index.activity.requested_urls, index.base_url) == []


def test_off_origin_requests_are_reported_when_one_happens(index: LoadedPage) -> None:
    """Guard: a request to another host is caught, however the page came to make it."""
    with index.page.expect_request(OFF_ORIGIN_PROBE):
        index.page.evaluate(f"new Image().src = {json.dumps(OFF_ORIGIN_PROBE)}")
    assert off_origin_requests(index.activity.requested_urls, index.base_url) == [OFF_ORIGIN_PROBE]


def test_console_errors_are_collected_when_one_happens(index: LoadedPage) -> None:
    """Guard: the console collector reports a real error, so a green run means something."""
    with index.page.expect_console_message(lambda message: message.type == "error"):
        index.page.evaluate("console.error('deliberate console error')")
    assert index.activity.console_errors == ["deliberate console error"]


def test_page_errors_are_collected_when_one_happens(index: LoadedPage) -> None:
    """Guard: the uncaught-exception collector reports a real throw."""
    with index.page.expect_event("pageerror"):
        index.page.evaluate("setTimeout(() => { throw new Error('deliberate page error') })")
    assert [error for error in index.activity.page_errors if "deliberate page error" in error]


def test_serve_app_binds_a_port_chosen_by_the_kernel() -> None:
    """Two servers can run at once, which a hardcoded port could never allow."""
    with serve_app() as first, serve_app() as second:
        assert urlsplit(first).port != urlsplit(second).port


def test_serve_app_frees_the_port_even_when_the_body_raises() -> None:
    """A failing test leaves no listening socket behind."""
    captured: dict[str, int | None] = {}
    with pytest.raises(RuntimeError, match="deliberate"):
        with serve_app() as base_url:
            captured["port"] = urlsplit(base_url).port
            raise RuntimeError("deliberate failure inside the harness")

    port = captured["port"]
    assert port is not None
    with pytest.raises(OSError):
        socket.create_connection((HOST, port), timeout=CONNECT_TIMEOUT).close()


def test_serve_app_stops_the_server_thread_even_when_the_body_raises() -> None:
    """A failing test leaves no server thread running either."""
    before = _server_threads()
    with pytest.raises(RuntimeError, match="deliberate"):
        with serve_app():
            raise RuntimeError("deliberate failure inside the harness")

    assert _server_threads() == before


def _server_threads() -> set[threading.Thread]:
    """Return the live server threads, by the name ``serve_app`` gives them."""
    return {thread for thread in threading.enumerate() if thread.name == SERVER_THREAD_NAME}


#: How long the ``/hang`` handler holds the connection open for. Comfortably
#: longer than any timeout a test below passes to ``_goto_or_raise``, so the
#: request is still outstanding when that timeout fires; short enough that a
#: daemon thread left running past the end of a test does not linger.
STUCK_FETCH_HOLD_SECONDS = 5.0


class _StuckFetchHandler(http.server.BaseHTTPRequestHandler):
    """Serves a page whose own script starts a ``fetch()`` it never lets finish.

    This is the review's own repro for the navigation-timeout guard: the
    document at ``/`` loads immediately -- ``wait_until="load"`` would be
    satisfied at once -- but the request its inline script starts against
    ``/hang`` never completes, so ``networkidle`` specifically never fires.
    """

    def do_GET(self) -> None:
        if self.path == "/hang":
            time.sleep(STUCK_FETCH_HOLD_SECONDS)
            return
        body = b"<!doctype html><title>stuck</title><script>fetch('/hang')</script>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass  # Keep test output free of one line per request.


@contextmanager
def _stuck_fetch_server() -> Iterator[str]:
    """Serve a page holding an open request, on a port the kernel picks."""
    server = http.server.ThreadingHTTPServer((HOST, 0), _StuckFetchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{HOST}:{server.server_port}/"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_goto_or_raise_reports_a_stuck_page_as_a_screenshot_error(page: Page) -> None:
    """A held-open request is reported in the tool's own words, not Playwright's.

    Without the guard, this is a bare ``playwright._impl._errors.TimeoutError``
    after the full navigation timeout: no PNG, no explanation, and a design
    role staring at a traceback the first time it screenshots a page with a
    run in progress.
    """
    with _stuck_fetch_server() as base_url:
        with pytest.raises(RouteNotServedError, match="did not settle"):
            _goto_or_raise(page, base_url, timeout_ms=500)


def test_goto_or_raise_names_the_url_that_did_not_settle(page: Page) -> None:
    """The failure names which URL got stuck, not just that one did."""
    with _stuck_fetch_server() as base_url:
        with pytest.raises(RouteNotServedError, match=r"^http://127\.0\.0\.1:\d+/ did not settle"):
            _goto_or_raise(page, base_url, timeout_ms=500)


def test_goto_or_raise_returns_the_response_for_a_page_that_settles(page: Page, live_server: str) -> None:
    """The guard is a narrowing, not a rewrite: an ordinary page still succeeds."""
    response = _goto_or_raise(page, f"{live_server}/", timeout_ms=5_000)
    assert response is not None and response.ok


@pytest.fixture(name="screenshot_run", scope="module")
def _screenshot_run(tmp_path_factory: pytest.TempPathFactory) -> "ScriptRun":
    """Run ``scripts/screenshot.py /`` once, and let the tests read the result.

    Invoked from an unrelated working directory: the design role runs this
    from wherever it happens to be standing, so nothing may resolve off cwd.
    """
    output_dir = tmp_path_factory.mktemp("screenshots")
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    completed = subprocess.run(
        [sys.executable, str(SCREENSHOT_SCRIPT), "/", "--out", str(output_dir)],
        capture_output=True,
        text=True,
        cwd=elsewhere,
        timeout=SCRIPT_TIMEOUT,
        check=False,
    )
    return ScriptRun(completed=completed, output_dir=output_dir)


class ScriptRun:
    """One invocation of the screenshot tool, and where it was told to write."""

    def __init__(self, completed: "subprocess.CompletedProcess[str]", output_dir: Path) -> None:
        self.completed = completed
        self.output_dir = output_dir

    @property
    def printed_paths(self) -> list[Path]:
        """The paths the tool printed on stdout, one per line."""
        return [Path(line) for line in self.completed.stdout.split()]


def test_screenshot_script_exits_cleanly(screenshot_run: ScriptRun) -> None:
    """A run with no browser open and no server running succeeds by itself."""
    assert screenshot_run.completed.returncode == 0, screenshot_run.completed.stderr


def test_screenshot_script_prints_an_absolute_path_per_width(screenshot_run: ScriptRun) -> None:
    """Callers read stdout to find the images, so each line is a usable path."""
    printed = screenshot_run.printed_paths
    assert len(printed) == len(WIDTHS)
    assert [path for path in printed if not path.is_absolute()] == []


def test_screenshot_script_writes_a_non_empty_png_per_width(screenshot_run: ScriptRun) -> None:
    """Every printed path is a real PNG with bytes in it."""
    for path in screenshot_run.printed_paths:
        assert path.read_bytes()[:8] == PNG_SIGNATURE, path


def test_screenshot_script_captures_each_requested_width(screenshot_run: ScriptRun) -> None:
    """The images are the widths asked for, read from the PNG header, not the filename."""
    assert sorted(_png_width(path) for path in screenshot_run.printed_paths) == sorted(WIDTHS)


def test_screenshot_script_writes_only_where_it_was_told(screenshot_run: ScriptRun) -> None:
    """Nothing lands outside the requested output directory."""
    for path in screenshot_run.printed_paths:
        assert path.parent == screenshot_run.output_dir


def test_screenshot_output_defaults_outside_the_repository() -> None:
    """With no ``--out``, images go to a temp directory: no PNG may be committed."""
    default = resolve_output_dir(None)
    assert REPO_ROOT not in default.parents and default != REPO_ROOT


def test_screenshot_script_refuses_an_output_directory_inside_the_repository() -> None:
    """An explicit ``--out`` into the checkout is refused, for the same reason."""
    completed = subprocess.run(
        [sys.executable, str(SCREENSHOT_SCRIPT), "/", "--out", str(REPO_ROOT / "docs")],
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT,
        check=False,
    )
    assert completed.returncode != 0
    assert "repository" in completed.stderr


def test_launch_chromium_names_the_install_command_when_it_is_missing() -> None:
    """A missing browser fails loudly and actionably; the suite never skips over it."""
    with pytest.raises(ChromiumUnavailableError, match="playwright install chromium"):
        launch_chromium(_PlaywrightWithoutChromium())


class _PlaywrightWithoutChromium:
    """Stands in for Playwright on a machine where no browser was installed."""

    @property
    def chromium(self) -> "_PlaywrightWithoutChromium":
        return self

    def launch(self, **_: object) -> None:
        raise PlaywrightError("Executable doesn't exist at /nowhere/headless_shell")


def _png_width(path: Path) -> int:
    """Return the pixel width recorded in a PNG's IHDR chunk."""
    return int.from_bytes(path.read_bytes()[16:20], "big")


def test_screenshot_script_reports_a_route_the_app_does_not_serve(tmp_path: Path) -> None:
    """A mistyped route fails loudly rather than yielding a photograph of a 404 page."""
    completed = subprocess.run(
        [sys.executable, str(SCREENSHOT_SCRIPT), "/no-such-route", "--out", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT,
        check=False,
    )
    assert completed.returncode != 0
    assert "404" in completed.stderr
    assert list(tmp_path.iterdir()) == []
