#!/usr/bin/env python3
"""Boot the app and photograph one of its routes at three widths.

Serving helpers live here, and the pytest end-to-end harness imports them
(``tests/e2e/conftest.py``), so there is exactly one implementation of
"start the real application on an ephemeral port".
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import uvicorn

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


class ChromiumUnavailableError(RuntimeError):
    """Raised when Playwright cannot start Chromium."""


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
