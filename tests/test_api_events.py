"""Tests for ``GET /api/run/{id}/events`` (task B-022).

Drives the real app through ``fastapi.testclient.TestClient``, the same way
``tests/test_api_run.py`` does. The wire format asserted here is the one
written into ``docs/api.md``'s "Run progress event" section.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import threading
import time

import pytest
from fastapi.testclient import TestClient

import fce_web.jobs as jobs_module
import fce_web.routes.api as api_module
from fce_web.app import create_app

FIXTURE_ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(FIXTURE_ROOT, "fixtures", "datasets", "IDEA", "91GeV")


def _graph(min_mass="60.0", max_mass="120.0"):
    return {
        "nodes": [
            {
                "id": "mult1", "kind": "Multiplicity",
                "config": {"nlep": 2, "op_lep": ">=", "njets": 0, "op_jet": ">=",
                           "ltype": "Any", "nphot": 0, "op_phot": ">="},
            },
            {"id": "sel1", "kind": "Selection", "config": {"name": "sel1", "exprs": ["l1.pt > 20"]}},
            {"id": "obs1", "kind": "Observable",
             "config": {"mode": "ObsCustom", "expr": "(l1.p4 + l2.p4).mass", "label": "m(l1,l2)"}},
            {"id": "hist1", "kind": "Histogram", "config": {"bins": "50", "min": min_mass, "max": max_mass}},
        ],
        "edges": [["mult1", "sel1"], ["sel1", "obs1"], ["obs1", "hist1"]],
    }


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FCE_HOME", str(tmp_path))
    shutil.copytree(DATASET_DIR, tmp_path / "datasets" / "IDEA" / "91GeV")
    with TestClient(create_app(env={"FCE_HOME": str(tmp_path)})) as c:
        yield c


def _read_events(client, run_id, timeout=60.0):
    """Every SSE frame for *run_id*, decoded, up to and including "done"."""
    events = []
    with client.stream("GET", f"/api/run/{run_id}/events", timeout=timeout) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            item = json.loads(line[len("data: "):])
            events.append(item)
            if item["type"] == "done":
                break
    return events


# ---- C1/C2: streams, terminates with one done, carries a phase and a
# progress fraction, never carries histogram data ----

def test_events_stream_carries_phase_and_progress_then_one_done(client):
    run_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    events = _read_events(client, run_id)

    assert any(e["type"] == "progress" for e in events), "no progress fraction reached the client"
    assert any(e["type"] == "phase" for e in events), "no phase label reached the client"
    assert events[-1] == {"type": "done", "status": "done", "runId": run_id}
    assert sum(1 for e in events if e["type"] == "done") == 1
    for e in events:
        assert e["runId"] == run_id
        assert "edges" not in e and "samples" not in e and "counts" not in e


# ---- C3: a cache hit yields an immediate done, no synthetic progress sweep ----

def test_cache_hit_events_stream_is_a_single_done_frame(client):
    first_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    _read_events(client, first_id)

    second = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()})
    assert second.json()["cacheHit"] is True
    second_id = second.json()["runId"]
    events = _read_events(client, second_id)

    assert events == [{"type": "done", "status": "done", "runId": second_id}]


# ---- C4: an unknown run id is a 404, not an open stream ----

def test_unknown_run_id_events_is_404_not_a_stream(client):
    resp = client.get("/api/run/does-not-exist/events")
    assert resp.status_code == 404
    assert "error" in resp.json()


# ---- C5: a client dropping mid-run leaks neither the worker thread nor a
# registry entry ----

def test_client_disconnect_mid_stream_leaks_nothing(client, monkeypatch):
    real_run_analysis = jobs_module.run_analysis
    started = threading.Event()
    release = threading.Event()

    def blocking(config, ctx, env):
        started.set()
        release.wait(timeout=5)
        return real_run_analysis(config, ctx, env)

    monkeypatch.setattr(jobs_module, "run_analysis", blocking)

    run_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    assert started.wait(timeout=5)

    registry = client.app.state.jobs
    jobs_before = len(registry._jobs)
    threads_before = threading.active_count()

    with client.stream("GET", f"/api/run/{run_id}/events") as resp:
        next(resp.iter_lines())  # read one frame, then abandon the stream

    deadline = time.monotonic() + 5.0
    while threading.active_count() > threads_before and time.monotonic() < deadline:
        time.sleep(0.05)
    assert threading.active_count() <= threads_before, "the SSE drain left an extra thread running"
    assert len(registry._jobs) == jobs_before, "the SSE endpoint must not touch the job registry"

    release.set()  # let the run finish so nothing is left blocked


async def _collect(agen):
    """Every SSE-formatted frame an async generator yields, decoded."""
    return [json.loads(chunk[len("data: "):]) async for chunk in agen]


def _run_bounded(coro, timeout):
    """Run *coro* to completion on a fresh thread, bounded by *timeout*.
    Returns ``"timed out"`` (and abandons a still-running coroutine, as a
    daemon thread, rather than block the test process) or the result."""
    result = {}

    def run():
        try:
            result["value"] = asyncio.run(coro)
        except BaseException:
            pass  # abandoned past *timeout*; "timed out" is already decided

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return "timed out"
    return result["value"]


class _FakeRequest:
    """Stand-in for ``fastapi.Request`` -- ``_drain`` only ever awaits
    ``request.is_disconnected()``, so this is the whole surface it needs."""

    async def is_disconnected(self) -> bool:
        return False


# ---- C6/C9/C10/C11/C12/C13: production _drain, called directly and bounded
# rather than through TestClient/HTTP, so a defect that removes the status
# short-circuit or crosses two jobs' queues makes these fail fast instead of
# hanging CI. runId is asserted per frame because it is now stamped where
# each frame is produced (fce_web.jobs._make_ctx), not by the reading
# stream, so a crossed queue can never launder itself as the right run. ----

def test_reconnect_after_drain_gets_one_done_frame(client):
    run_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    _read_events(client, run_id)  # first client drains the queue fully, including "done"

    job = client.app.state.jobs.get(run_id)
    result = _run_bounded(_collect(api_module._drain(_FakeRequest(), job)), timeout=5.0)
    assert result != "timed out", "a reconnect after drain must return promptly, not hang"
    assert result == [{"type": "done", "status": "done", "runId": run_id}]


def test_two_concurrent_streams_do_not_interleave(client):
    ids = {"a": client.post("/api/run", json={"missionId": "A", "graph": _graph("0.0", "200.0")}).json()["runId"],
           "b": client.post("/api/run", json={"missionId": "B", "graph": _graph("60.0", "120.0")}).json()["runId"]}
    jobs = {key: client.app.state.jobs.get(run_id) for key, run_id in ids.items()}

    results = {}

    def read(key):
        try:
            results[key] = asyncio.run(_collect(api_module._drain(_FakeRequest(), jobs[key])))
        except BaseException:
            pass  # left unset; the join-timeout assertion below still catches a hang

    t_a = threading.Thread(target=read, args=("a",), daemon=True)
    t_b = threading.Thread(target=read, args=("b",), daemon=True)
    t_a.start()
    t_b.start()
    t_a.join(timeout=15)
    t_b.join(timeout=15)

    assert not t_a.is_alive() and not t_b.is_alive(), "a stream thread is still running after its join timeout"

    for key in ("a", "b"):
        assert key in results, f"stream {key} never completed"
        assert results[key][-1] == {"type": "done", "status": "done", "runId": ids[key]}
        assert sum(1 for e in results[key] if e["type"] == "done") == 1
        for e in results[key]:
            assert e["runId"] == ids[key], f"stream {key} saw a frame for the other run"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
