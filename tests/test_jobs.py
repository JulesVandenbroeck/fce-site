"""Tests for ``fce_web.jobs.JobRegistry`` (task B-021).

Runs the real engine against the committed fixture dataset
(``tests/fixtures/datasets/IDEA/91GeV``), the same way
``tests/test_fixture_dataset.py`` does: ``FCE_HOME`` points at a tmp
directory, never the committed fixture tree.
"""
from __future__ import annotations

import os
import shutil
import threading
import time

import pytest

import fce_web.jobs as jobs_module
from fce_web.graph import GraphError
from fce_web.jobs import Job, JobRegistry
from fce_web.runs import RunContext

FIXTURE_ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(FIXTURE_ROOT, "fixtures", "datasets", "IDEA", "91GeV")


def _graph(min_mass="60.0", max_mass="120.0"):
    """A minimal legal graph: `>= 2 leptons`, dilepton invariant mass."""
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
def registry(tmp_path, monkeypatch):
    """A registry pointed at a tmp ``FCE_HOME`` seeded with a copy of the
    fixture dataset -- never the committed fixture tree (``docs`` note in
    ``tests/test_fixture_dataset.py``: ``run_physics_loop``'s own
    cache/output resolves ``get_fce_home()`` with no argument, i.e. the real
    process environment, regardless of the ``env`` dict passed to
    ``run_analysis`` -- so both must point at the same tmp directory).
    """
    monkeypatch.setenv("FCE_HOME", str(tmp_path))
    shutil.copytree(DATASET_DIR, tmp_path / "datasets" / "IDEA" / "91GeV")
    return JobRegistry(env={"FCE_HOME": str(tmp_path)})


def _block_run_analysis(monkeypatch):
    """Monkeypatch ``fce_web.jobs.run_analysis`` to block until the test
    releases it -- the seam a check needs to observe a job mid-flight
    instead of asserting on a status that would also pass if ``submit``
    blocked."""
    real_run_analysis = jobs_module.run_analysis
    started = threading.Event()
    release = threading.Event()

    def blocking(config, ctx, env):
        started.set()
        release.wait(timeout=5)
        return real_run_analysis(config, ctx, env)

    monkeypatch.setattr(jobs_module, "run_analysis", blocking)
    return started, release


def _drain_to_sentinel(events, timeout=5.0):
    """Read *events* until the terminal ``{"type": "done", ...}`` sentinel,
    returning it. Progress/log/phase items land in the queue ahead of it on
    a real run, so a caller after only the sentinel must drain, not read
    the first item."""
    while True:
        item = events.get(timeout=timeout)
        if item["type"] == "done":
            return item


def _wait_done(registry, run_id, timeout=60.0):
    job = registry.get(run_id)
    deadline = time.monotonic() + timeout
    while job.status == "running":
        if time.monotonic() > deadline:
            raise AssertionError(f"job {run_id} did not finish within {timeout}s")
        time.sleep(0.02)
    return job


# ---- submit returns before the run completes, and it actually runs ----
# `assert job.status in ("running", "done")` cannot fail even if `submit`
# blocked until the run finished -- it accepts both outcomes. Block
# `run_analysis` on an `Event` the test controls so the job is observably
# still "running" *after* `submit` has returned, which a blocking `submit`
# could not produce.

def test_submit_returns_before_the_run_completes(registry, monkeypatch):
    started, release = _block_run_analysis(monkeypatch)

    job = registry.submit(_graph(), mission_id="M-1")
    assert started.wait(timeout=5), "run_analysis was never called"
    assert job.status == "running"

    release.set()
    finished = _wait_done(registry, job.id)
    assert finished.status == "done", finished.error
    assert finished.payload["data"] is not None
    assert finished.payload["meta"]["mission"] == "M-1"


# ---- an invalid graph never starts a run ----

def test_invalid_graph_raises_before_any_job_exists(registry):
    bad_graph = {"nodes": [{"id": "ds1", "kind": "DataSource", "config": {}}], "edges": []}
    with pytest.raises(GraphError):
        registry.submit(bad_graph, mission_id="M-1")
    assert registry._jobs == {}


# ---- two concurrent runs keep separate state ----

def test_two_concurrent_runs_keep_separate_state(registry):
    job_a = registry.submit(_graph(min_mass="60.0", max_mass="120.0"), mission_id="A")
    job_b = registry.submit(_graph(min_mass="0.0", max_mass="200.0"), mission_id="B")
    assert job_a.id != job_b.id

    finished_a = _wait_done(registry, job_a.id)
    finished_b = _wait_done(registry, job_b.id)

    assert finished_a.status == "done", finished_a.error
    assert finished_b.status == "done", finished_b.error
    assert finished_a.payload["meta"]["mission"] == "A"
    assert finished_b.payload["meta"]["mission"] == "B"
    # Different bin ranges -> different edges; neither run's histogram leaked
    # into the other's job.
    assert finished_a.payload["edges"] != finished_b.payload["edges"]


# ---- no module-level mutable state -- two registries share nothing ----

def test_two_registries_share_nothing(registry, tmp_path, monkeypatch):
    other = JobRegistry(env={"FCE_HOME": str(tmp_path)})
    job = registry.submit(_graph(), mission_id="M-1")
    assert other.get(job.id) is None
    assert other._jobs == {}
    assert other._cache == {}


# ---- a repeated submission is a visible cache hit ----
# A cache hit reused `cached.payload` by reference, `meta.mission` and
# all -- a second mission submitting the same cuts saw the first mission's
# id. The `third` submission below, under a different mission id, is the
# check that would fail on that bug.

def test_repeated_submission_is_a_cache_hit(registry):
    first = registry.submit(_graph(), mission_id="M-1")
    _wait_done(registry, first.id)

    second = registry.submit(_graph(), mission_id="M-1")
    assert second.cache_hit is True
    assert second.status == "done"
    assert second.id != first.id
    assert second.payload == registry.get(first.id).payload

    third = registry.submit(_graph(), mission_id="M-2")
    assert third.cache_hit is True
    assert third.payload["meta"]["mission"] == "M-2"
    assert registry.get(first.id).payload["meta"]["mission"] == "M-1"


# ---- cancellation reaches a queued job, not just a running one ----

def test_cancelling_a_queued_job_reaches_cancelled_status(registry, monkeypatch):
    started, release = _block_run_analysis(monkeypatch)

    job_a = registry.submit(_graph(min_mass="60.0", max_mass="120.0"), mission_id="A")
    assert started.wait(timeout=5)  # job_a now holds `_run_lock`

    job_b = registry.submit(_graph(min_mass="0.0", max_mass="200.0"), mission_id="B")
    job_b.ctx.cancel.set()  # cancelled while still queued behind job_a
    release.set()

    finished_a = _wait_done(registry, job_a.id)
    finished_b = _wait_done(registry, job_b.id)
    assert finished_a.status == "done", finished_a.error
    assert finished_b.status == "cancelled"
    assert _drain_to_sentinel(finished_b.events) == {"type": "done", "status": "cancelled"}


# ---- the events queue B-022 will drain ----

def test_events_queue_carries_progress_then_one_terminal_sentinel(registry):
    job = registry.submit(_graph(), mission_id="M-1")
    finished = _wait_done(registry, job.id)
    assert finished.status == "done", finished.error

    items = []
    while True:
        item = finished.events.get(timeout=1)
        items.append(item)
        if item["type"] == "done":
            break

    assert any(item["type"] == "progress" for item in items)
    assert items[-1] == {"type": "done", "status": "done"}
    assert sum(1 for item in items if item["type"] == "done") == 1


def test_cache_hit_events_queue_holds_only_the_sentinel(registry):
    first = registry.submit(_graph(), mission_id="M-1")
    _wait_done(registry, first.id)

    second = registry.submit(_graph(), mission_id="M-1")
    assert second.cache_hit is True
    assert second.events.get(timeout=1) == {"type": "done", "status": "done"}
    assert second.events.empty()


# ---- an unexpected (non-PayloadError) exception must still terminate ----

def test_unexpected_exception_building_payload_still_reaches_terminal_status(registry, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(jobs_module, "build_histogram_payload", boom)

    job = registry.submit(_graph(), mission_id="M-1")
    finished = _wait_done(registry, job.id, timeout=10.0)
    assert finished.status == "error"
    assert finished.error == "boom"
    assert _drain_to_sentinel(finished.events) == {"type": "done", "status": "error"}


# ---- _evict_over_cap drops the oldest non-"running" job, keeps every
# "running" job, and stops once nothing evictable is left ----

def test_evict_over_cap_keeps_running_jobs_and_caps_the_rest():
    reg = JobRegistry()
    for i in range(jobs_module._MAX_JOBS + 2):
        status = "running" if i < 5 else "done"
        job = Job(id=str(i), mission_id="M-1", ctx=RunContext(), status=status)
        reg._jobs[job.id] = job

    reg._evict_over_cap()

    assert len(reg._jobs) == jobs_module._MAX_JOBS
    assert all(reg._jobs[str(i)].status == "running" for i in range(5))


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
