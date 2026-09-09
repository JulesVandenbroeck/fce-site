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
    """Every SSE frame for *run_id*, decoded, up to and including "done".

    *timeout* is passed straight to ``client.stream`` (F3): a stalled or
    crossed stream then raises from the client's own read timeout instead of
    blocking ``iter_lines()`` forever, so a defect that wedges the queue
    fails in seconds, not in a 400s CI hang (F2).
    """
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


# ---- C6/C11: two concurrent streams for two different runs do not
# interleave, and each stream's frames carry its own run's id (F4) --
# distinguishing "read its own run" from "read the other's" ----

def test_two_concurrent_streams_do_not_interleave(client):
    ids = {"a": client.post("/api/run", json={"missionId": "A", "graph": _graph("0.0", "200.0")}).json()["runId"],
           "b": client.post("/api/run", json={"missionId": "B", "graph": _graph("60.0", "120.0")}).json()["runId"]}

    results = {}

    def read(run_id, key):
        results[key] = _read_events(client, run_id)

    t_a = threading.Thread(target=read, args=(ids["a"], "a"))
    t_b = threading.Thread(target=read, args=(ids["b"], "b"))
    t_a.start()
    t_b.start()
    t_a.join(timeout=15)
    t_b.join(timeout=15)

    assert not t_a.is_alive() and not t_b.is_alive(), "a stream thread is still running after its join timeout"

    for key in ("a", "b"):
        assert results[key][-1] == {"type": "done", "status": "done", "runId": ids[key]}
        assert sum(1 for e in results[key] if e["type"] == "done") == 1
        for e in results[key]:
            assert e["runId"] == ids[key], f"stream {key} saw a frame for the other run"


# ---- C9: a second client, or the same client reconnecting after the
# queue has already been drained, gets exactly one terminal done frame
# carrying the job's real status and the stream closes -- this is the F1
# defect: without the status short-circuit this hangs forever ----

def test_reconnect_after_drain_gets_one_done_frame(client):
    run_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    _read_events(client, run_id)  # first client drains the queue fully, including "done"

    events = _read_events(client, run_id, timeout=5.0)  # a second/reconnecting client

    assert events == [{"type": "done", "status": "done", "runId": run_id}]


async def _collect(agen):
    """Every SSE-formatted frame an async generator yields, decoded."""
    return [json.loads(chunk[len("data: "):]) async for chunk in agen]


def _run_bounded(coro, timeout):
    """Run *coro* to completion on a fresh thread, bounded by *timeout*.

    Not ``asyncio.run(coro)`` directly on the test thread: pytest may already
    be inside a running event loop by the time this runs (observed under the
    full suite, not in isolation -- ``RuntimeError: asyncio.run() cannot be
    called from a running event loop``), and a coroutine that never returns
    must not be allowed to hang the test process either way. A dedicated
    thread sidesteps both: it never has a loop of its own to collide with,
    and joining it with *timeout* bounds the wait. Returns ``"timed out"``
    or the coroutine's result.
    """
    result = {}

    def run():
        try:
            result["value"] = asyncio.run(coro)
        except BaseException:
            # Deliberately abandoned once *timeout* elapses (the coroutine
            # under test never returns, by construction). Whatever this
            # thread does after that -- including interpreter-shutdown
            # noise from the executor it started -- is uninteresting; the
            # test has already read "timed out" off the join by then.
            pass

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return "timed out"
    return result["value"]


class _FakeRequest:
    """Stand-in for ``fastapi.Request`` -- ``_drain`` only ever calls
    ``await request.is_disconnected()``. Used to unit-test ``_drain``
    directly, bypassing ``starlette.testclient.TestClient``: its transport
    runs the whole ASGI call to completion inside a synchronous
    ``portal.call`` before ``client.stream()`` returns a single byte
    (verified empirically -- httpx's own ``timeout`` kwarg on a stalled
    generator never fires against it, and an abandoned reader thread left
    stuck on it wedges fixture teardown, which is F2's exact failure).
    Running ``_drain`` directly through ``_run_bounded`` has no such trap:
    a defect that would otherwise hang forever surfaces as ``"timed out"``
    within a few seconds instead of wedging the test process.
    """

    async def is_disconnected(self) -> bool:
        return False


def test_reconnect_check_goes_red_without_the_short_circuit(client, monkeypatch):
    """Mutation for C9: rebind ``_drain`` (monkeypatch, no tracked file
    edited) to the pre-fix shape -- straight into the queue loop, no
    ``job.status`` check. A reconnect after drain (an already-empty queue,
    real ``"done"`` status) then never yields anything -- the reviewer's own
    probe reported "no terminal frame after 4s on an already-drained
    queue" -- so the mutated generator must be raced against a timeout
    itself to observe the hang without blocking pytest forever."""
    import queue as queue_mod
    from concurrent.futures import ThreadPoolExecutor

    async def pre_fix_drain(request, job):
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            while True:
                if await request.is_disconnected():
                    return
                try:
                    item = await loop.run_in_executor(pool, job.events.get, True, 0.5)
                except queue_mod.Empty:
                    continue
                yield f"data: {json.dumps(item)}\n\n"
                if item["type"] == "done":
                    return

    monkeypatch.setattr(api_module, "_drain", pre_fix_drain)
    run_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    _read_events(client, run_id)  # drain the real queue fully, including "done"
    job = client.app.state.jobs.get(run_id)

    result = _run_bounded(_collect(pre_fix_drain(_FakeRequest(), job)), timeout=3.0)
    assert result == "timed out", (
        "without the status short-circuit, draining an already-terminal job "
        f"should still block past 3s -- got {result!r} instead, so this no longer reproduces F1"
    )


# ---- C10: a stalled or crossed stream fails fast with a named message,
# rather than hanging -- reproduces the reviewer's M3 mutation shape
# (every stream drains the *first* job's queue), which ran past a 400s
# timeout against a 0.75s baseline before F3's fix. Exercised at the
# ``_drain`` level directly (see ``_FakeRequest``'s docstring for why: the
# HTTP-level equivalent wedges ``TestClient`` fixture teardown itself,
# which is the exact defect F2 named) ----

def test_crossed_queue_shape_fails_fast_not_after_400s(client):
    id_a = client.post("/api/run", json={"missionId": "A", "graph": _graph()}).json()["runId"]
    _read_events(client, id_a)  # drain job A's queue fully, including its "done"

    id_b = client.post("/api/run", json={"missionId": "B", "graph": _graph()}).json()["runId"]
    _read_events(client, id_b)  # let job B finish and drain normally too

    registry = client.app.state.jobs
    job_a, job_b = registry.get(id_a), registry.get(id_b)
    job_b.status = "running"        # force the queue-loop path, not the terminal short-circuit
    job_b.events = job_a.events     # M3: this stream now drains the *other* job's already-empty queue

    start = time.monotonic()
    result = _run_bounded(_collect(api_module._drain(_FakeRequest(), job_b)), timeout=3.0)
    elapsed = time.monotonic() - start
    assert result == "timed out", f"expected a bounded timeout, got {result!r}"
    assert elapsed < 15.0, f"bounding the read took {elapsed:.1f}s -- should fail fast, in seconds, not ~400s"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
