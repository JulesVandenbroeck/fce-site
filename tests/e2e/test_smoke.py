"""Smoke tests: what a real browser does with the real server.

The last group tests the harness itself. A test server that picked a fixed
port would fail whenever a colleague, a stale process, or a second run of this
suite already held it, and one that outlived its ``with`` block would leak a
listening socket per failure -- so both properties are asserted rather than
assumed.
"""

import json
import socket
import threading
from urllib.parse import urlsplit

import pytest

from scripts.screenshot import HOST, SERVER_THREAD_NAME, serve_app
from tests.e2e.conftest import LoadedPage, off_origin_requests

#: Seconds to wait when probing a port that should no longer be listening.
CONNECT_TIMEOUT = 2.0

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
