"""B-035/C2: ``python -m fce_web`` must never log a client's address.

Starts the real launcher as a subprocess on a free loopback port, makes one request, and
asserts the client's address (uvicorn's access-log format is ``<ip>:<port> - "GET ..."``)
never appears in what it printed. Goes red the moment ``access_log=False`` is dropped from
``fce_web.__main__``.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_launcher_prints_no_client_address(tmp_path):
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "fce_web", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "FCE_HOME": str(tmp_path)},
    )
    served = False
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/openapi.json", timeout=1)
                served = True
                break
            except Exception:
                if proc.poll() is not None:
                    break
                time.sleep(0.2)
    finally:
        proc.terminate()
        try:
            output, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()

    assert served, f"launcher never answered a request; output:\n{output}"

    # An access-log line looks like: 127.0.0.1:54321 - "GET /openapi.json HTTP/1.1" 200 OK
    # The startup banner also contains "127.0.0.1:<port>" (the bind address, not a client),
    # so check for the request line specifically.
    assert '- "GET' not in output, output
