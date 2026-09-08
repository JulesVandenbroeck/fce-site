"""Tests for ``fce_web.jobs.JobRegistry`` (task B-021).

Runs the real engine against the committed fixture dataset
(``tests/fixtures/datasets/IDEA/91GeV``), the same way
``tests/test_fixture_dataset.py`` does: ``FCE_HOME`` points at a tmp
directory, never the committed fixture tree.
"""
from __future__ import annotations

import os
import shutil
import time

import pytest

from fce_web.graph import GraphError
from fce_web.jobs import JobRegistry

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


def _wait_done(registry, run_id, timeout=60.0):
    job = registry.get(run_id)
    deadline = time.monotonic() + timeout
    while job.status == "running":
        if time.monotonic() > deadline:
            raise AssertionError(f"job {run_id} did not finish within {timeout}s")
        time.sleep(0.02)
    return job


# ---- C1: submit returns before the run completes, and it actually runs ----

def test_submit_returns_before_the_run_completes(registry):
    job = registry.submit(_graph(), mission_id="M-1")
    # The run takes long enough to process a ROOT file; the call above did
    # not block for that -- if it had, the job would already be done here.
    assert job.status in ("running", "done")
    finished = _wait_done(registry, job.id)
    assert finished.status == "done", finished.error
    assert finished.payload["data"] is not None
    assert finished.payload["meta"]["mission"] == "M-1"


# ---- C2: an invalid graph never starts a run ----

def test_invalid_graph_raises_before_any_job_exists(registry):
    bad_graph = {"nodes": [{"id": "ds1", "kind": "DataSource", "config": {}}], "edges": []}
    with pytest.raises(GraphError):
        registry.submit(bad_graph, mission_id="M-1")
    assert registry._jobs == {}


# ---- C3: two concurrent runs keep separate state ----

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


# ---- C4: no module-level mutable state -- two registries share nothing ----

def test_two_registries_share_nothing(registry, tmp_path, monkeypatch):
    other = JobRegistry(env={"FCE_HOME": str(tmp_path)})
    job = registry.submit(_graph(), mission_id="M-1")
    assert other.get(job.id) is None
    assert other._jobs == {}
    assert other._cache == {}


# ---- C7: a repeated submission is a visible cache hit ----

def test_repeated_submission_is_a_cache_hit(registry):
    first = registry.submit(_graph(), mission_id="M-1")
    _wait_done(registry, first.id)

    second = registry.submit(_graph(), mission_id="M-1")
    assert second.cache_hit is True
    assert second.status == "done"
    assert second.id != first.id
    assert second.payload == registry.get(first.id).payload


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
