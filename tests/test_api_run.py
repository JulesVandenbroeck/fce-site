"""Tests for ``POST /api/run`` and ``GET /api/run/{id}/result`` (task B-021).

Drives the real app through ``fastapi.testclient.TestClient`` (no live
server, no network) against the committed fixture dataset, the same way
``tests/test_jobs.py`` drives ``JobRegistry`` directly.
"""
from __future__ import annotations

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
             "config": {"mode": "ObsVectorSum", "expr": "(l1.p4 + l2.p4).mass", "label": "m(l1,l2)"}},
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


def _poll_result(client, run_id, timeout=60.0):
    deadline = time.monotonic() + timeout
    while True:
        resp = client.get(f"/api/run/{run_id}/result")
        if resp.status_code != 202:
            return resp
        if time.monotonic() > deadline:
            raise AssertionError(f"run {run_id} did not finish within {timeout}s")
        time.sleep(0.02)


# ---- submit returns a run id before the run completes ----
# Neither original check here could fail even if `POST /api/run` blocked
# until the run finished. Block `run_analysis` on an `Event` the test
# controls so the result is observably still "running" right after the
# response comes back.

def test_submit_returns_a_run_id_immediately(client, monkeypatch):
    real_run_analysis = jobs_module.run_analysis
    started = threading.Event()
    release = threading.Event()

    def blocking(config, ctx, env):
        started.set()
        release.wait(timeout=5)
        return real_run_analysis(config, ctx, env)

    monkeypatch.setattr(jobs_module, "run_analysis", blocking)

    resp = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "runId" in body and isinstance(body["runId"], str)
    assert body["cacheHit"] is False
    assert started.wait(timeout=5), "run_analysis was never called"

    still_running = client.get(f"/api/run/{body['runId']}/result")
    assert still_running.status_code == 202
    assert still_running.json()["status"] == "running"

    release.set()
    resp2 = _poll_result(client, body["runId"])
    assert resp2.json()["status"] == "done"


# ---- an invalid graph is a 4xx carrying B-020's message ----

def test_invalid_graph_is_a_400_with_graph_error_message(client):
    bad_graph = {"nodes": [{"id": "ds1", "kind": "DataSource", "config": {}}], "edges": []}
    resp = client.post("/api/run", json={"missionId": "M-1", "graph": bad_graph})
    assert resp.status_code == 400
    body = resp.json()
    assert "DataSource" in body["error"]
    assert body["nodeId"] == "ds1"


# ---- B-026: a bad Observable/Selection expression is a 400 naming its node,
# not a run that starts and fails later.

def _graph_with_bad_observable_expr():
    graph = _graph()
    graph["nodes"][2]["config"]["expr"] = "__import__('os')"
    return graph


def _graph_with_bad_selection_expr():
    graph = _graph()
    graph["nodes"][1]["config"]["exprs"] = ["__import__('os')"]
    return graph


def test_bad_observable_expr_is_a_400_naming_its_node(client):
    resp = client.post("/api/run", json={"missionId": "M-1", "graph": _graph_with_bad_observable_expr()})
    assert resp.status_code == 400
    assert resp.json()["nodeId"] == "obs1"


def test_bad_selection_expr_is_a_400_naming_its_node(client):
    resp = client.post("/api/run", json={"missionId": "M-1", "graph": _graph_with_bad_selection_expr()})
    assert resp.status_code == 400
    assert resp.json()["nodeId"] == "sel1"


# ---- result is fetchable by id, "running" while in flight, 404 unknown ----

def test_unknown_run_id_is_404(client):
    resp = client.get("/api/run/does-not-exist/result")
    assert resp.status_code == 404


def test_result_reaches_done_with_the_histogram_payload(client):
    run_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    resp = _poll_result(client, run_id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "done"
    assert body["cacheHit"] is False
    assert body["meta"]["mission"] == "M-1"
    assert body["data"] is not None
    assert len(body["edges"]) == 51  # 50 bins
    # The fixture dataset's actual MC samples, independently known from
    # tests/fixtures/datasets/IDEA/91GeV/*.root -- guards against `samples`
    # silently going empty (see driver.py's `active_samples`).
    assert [s["name"] for s in body["samples"]] == ["X1", "X2", "X3"]
    assert body["objective"]["missionId"] == "M-1"
    assert isinstance(body["objective"]["met"], bool)


# ---- B-032/C1: an unknown missionId is a 400, nothing is submitted ----

def test_unknown_mission_id_is_a_400(client):
    resp = client.post("/api/run", json={"missionId": "no-such-mission", "graph": _graph()})
    assert resp.status_code == 400
    body = resp.json()
    assert "no-such-mission" in body["error"]
    assert body["nodeId"] is None


# ---- B-032/C3: the server is the gate on the mission's palette, not just
# the browser -- an Observable mode the mission does not offer is a 400
# naming that node, even though the mode itself is a real, valid mode. ----

def test_locked_observable_mode_is_a_400_naming_its_node(client):
    graph = _graph()
    graph["nodes"][2]["config"]["mode"] = "ObsCustom"  # M-1 only offers ObsVectorSum
    resp = client.post("/api/run", json={"missionId": "M-1", "graph": graph})
    assert resp.status_code == 400
    assert resp.json()["nodeId"] == "obs1"


# ---- B-032/C4/C6: the objective is evaluated per job, from that job's own
# mission -- never copied from the job whose result a cache hit reused. M-1
# and M-2 share a dataset and palette, so the identical graph digests to the
# same cache entry under both; M-1's objective is peak_position (met on this
# fixture/graph) and M-2's is 'none' (never met) -- a registry that read the
# objective off the *cached* job instead of the *requesting* job's own
# mission would report M-2 as met too.

def test_objective_is_per_job_not_copied_from_the_cached_job(client):
    first = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()
    first_result = _poll_result(client, first["runId"]).json()
    assert first_result["objective"]["met"] is True, first_result["objective"]

    second = client.post("/api/run", json={"missionId": "M-2", "graph": _graph()})
    assert second.json()["cacheHit"] is True
    second_result = _poll_result(client, second.json()["runId"]).json()
    assert second_result["objective"] == {
        "missionId": "M-2", "met": False, "value": None,
        "message": "This mission has no automatic objective yet.",
    }


# ---- a repeated submission is a visible cache hit ----

def test_repeated_submission_reports_a_cache_hit(client):
    first_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
    _poll_result(client, first_id)

    second = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()})
    assert second.json()["cacheHit"] is True
    result = client.get(f"/api/run/{second.json()['runId']}/result")
    assert result.json()["status"] == "done"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
