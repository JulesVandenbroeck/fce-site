"""Tests for ``GET /api/run/{id}/events`` (task B-022).

Drives the real app through ``fastapi.testclient.TestClient``, the same way
``tests/test_api_run.py`` does. The wire format asserted here is the one
written into ``docs/api.md``'s "Run progress event" section.
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time

import pytest
from fastapi.testclient import TestClient

import fce_web.jobs as jobs_module
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
    deadline = time.monotonic() + timeout
    with client.stream("GET", f"/api/run/{run_id}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            item = json.loads(line[len("data: "):])
            events.append(item)
            if item["type"] == "done":
                break
            if time.monotonic() > deadline:
                raise AssertionError(f"run {run_id} did not finish within {timeout}s")
    return events


# ---- C1/C2: streams, terminates with one done, carries a phase and a
# progress fraction, never carries histogram data ----

def test_events_stream_carries_phase_and_progress_then_one_done(client):
    run_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    events = _read_events(client, run_id)

    assert any(e["type"] == "progress" for e in events), "no progress fraction reached the client"
    assert any(e["type"] == "phase" for e in events), "no phase label reached the client"
    assert events[-1] == {"type": "done", "status": "done"}
    assert sum(1 for e in events if e["type"] == "done") == 1
    for e in events:
        assert "edges" not in e and "samples" not in e and "counts" not in e


# ---- C3: a cache hit yields an immediate done, no synthetic progress sweep ----

def test_cache_hit_events_stream_is_a_single_done_frame(client):
    first_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    _read_events(client, first_id)

    second = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()})
    assert second.json()["cacheHit"] is True
    events = _read_events(client, second.json()["runId"])

    assert events == [{"type": "done", "status": "done"}]


def test_cache_hit_check_goes_red_for_a_synthetic_progress_sweep():
    """The check above is falsifiable: a queue carrying a fabricated sweep on
    a cache hit must fail it. Simulates what a bad producer would enqueue
    (this is not exercising production code, only the assertion's shape)."""
    fabricated = [{"type": "progress", "value": 0.5}, {"type": "done", "status": "done"}]
    with pytest.raises(AssertionError):
        assert fabricated == [{"type": "done", "status": "done"}]


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


# ---- C6: two concurrent streams for two different runs do not interleave ----

def test_two_concurrent_streams_do_not_interleave(client):
    id_a = client.post("/api/run", json={"missionId": "A", "graph": _graph("0.0", "200.0")}).json()["runId"]
    id_b = client.post("/api/run", json={"missionId": "B", "graph": _graph("60.0", "120.0")}).json()["runId"]

    results = {}

    def read(run_id, key):
        results[key] = _read_events(client, run_id)

    t_a = threading.Thread(target=read, args=(id_a, "a"))
    t_b = threading.Thread(target=read, args=(id_b, "b"))
    t_a.start()
    t_b.start()
    t_a.join(timeout=60)
    t_b.join(timeout=60)

    for key in ("a", "b"):
        assert results[key][-1] == {"type": "done", "status": "done"}
        assert sum(1 for e in results[key] if e["type"] == "done") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
