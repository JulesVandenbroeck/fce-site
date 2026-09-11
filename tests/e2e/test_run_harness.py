"""End-to-end proof that a run submitted to ``live_server`` executes against
the committed fixture dataset in a hermetic tmp ``FCE_HOME`` (task B-023) --
never a developer's real ``~/.fce``.

Drives the JSON API directly (``httpx``, already a dev dependency), rather
than the browser -- F-007/F-008 exercise the same endpoints from the page;
this test's job is only to prove the harness itself is hermetic.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

from tests.test_api_run import _graph


def test_run_executes_hermetically_against_the_fixture_dataset(live_server):
    # `_e2e_process_fce_home` (tests/e2e/conftest.py, autouse) points
    # FCE_HOME at a tmp dir seeded only with the fixture dataset -- never
    # the real `~/.fce` -- for exactly the duration of this test.
    fce_home = Path(os.environ["FCE_HOME"])

    resp = httpx.post(f"{live_server}/api/run", json={"missionId": "M-1", "graph": _graph()})
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["runId"]

    frames = []
    with httpx.stream("GET", f"{live_server}/api/run/{run_id}/events", timeout=60.0) as stream:
        for line in stream.iter_lines():
            if not line.startswith("data: "):
                continue
            frame = json.loads(line[len("data: "):])
            frames.append(frame)
            if frame["type"] == "done":
                break
    assert frames and frames[-1] == {"type": "done", "status": "done", "runId": run_id}

    result = httpx.get(f"{live_server}/api/run/{run_id}/result", timeout=10.0)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "done"

    counts = {s["name"]: s["counts"] for s in body["samples"]}["X1"]
    edges = body["edges"]
    peak_bin = max(range(len(counts)), key=lambda i: counts[i])
    peak_centre = (edges[peak_bin] + edges[peak_bin + 1]) / 2
    assert abs(peak_centre - 91.19) <= 3.0, peak_centre

    # The run's output landed under the tmp FCE_HOME, not the real ~/.fce.
    assert (fce_home / "output" / "hist0_X1.root").exists()
