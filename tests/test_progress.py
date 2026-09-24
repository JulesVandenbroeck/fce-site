"""Tests for join, cookie, progress and completion recording (task B-034).

One end-to-end check that goes red if progression breaks -- join, run M-1's
default chain to a met objective, see M-2 unlock and persist across a fresh
client re-joining the same pair, then purge and see the old cookie is no
longer joined. Plus: running a locked mission is a 400.
"""
from __future__ import annotations

import os
import shutil
import time

import pytest
from fastapi.testclient import TestClient

from fce_web import store
from fce_web.app import create_app

FIXTURE_ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(FIXTURE_ROOT, "fixtures", "datasets", "IDEA", "91GeV")


def _graph():
    """The default M-1 chain: `>= 2 leptons`, dilepton invariant mass, whose
    peak lands within M-1's `objective.tolerance` of 91.19 GeV on the fixture
    (the same graph `tests/test_api_run.py` uses)."""
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
            {"id": "hist1", "kind": "Histogram", "config": {"bins": "50", "min": "60.0", "max": "120.0"}},
        ],
        "edges": [["mult1", "sel1"], ["sel1", "obs1"], ["obs1", "hist1"]],
    }


@pytest.fixture()
def env(tmp_path):
    """An explicit env mapping (never process env, `.claude/shared/CLAUDE.md` §6)
    pointing at a tmp `FCE_HOME` seeded with the fixture dataset."""
    shutil.copytree(DATASET_DIR, tmp_path / "datasets" / "IDEA" / "91GeV")
    return {"FCE_HOME": str(tmp_path)}


def _poll_result(client, run_id, timeout=60.0):
    deadline = time.monotonic() + timeout
    while True:
        resp = client.get(f"/api/run/{run_id}/result")
        if resp.status_code != 202:
            return resp
        if time.monotonic() > deadline:
            raise AssertionError(f"run {run_id} did not finish within {timeout}s")
        time.sleep(0.02)


def test_join_run_unlock_progress_persists_and_purge_clears_it(env) -> None:
    code = store.create_class(env=env)

    with TestClient(create_app(env=env)) as client:
        joined = client.post("/api/join", json={"classCode": code, "nickname": "quarkqueen"})
        assert joined.status_code == 200
        assert joined.json()["student"] == {"classCode": code, "nickname": "quarkqueen"}
        assert [m["state"] for m in joined.json()["missions"]] == ["open", "locked"]

        # A mission not yet unlocked is a 400, naming no single node.
        locked_run = client.post("/api/run", json={"missionId": "M-2", "graph": _graph()})
        assert locked_run.status_code == 400
        assert locked_run.json()["nodeId"] is None

        # The default M-1 chain meets the objective and opens M-2.
        run_id = client.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
        result = _poll_result(client, run_id).json()
        assert result["objective"]["met"] is True
        assert result["objective"]["unlocked"] == "M-2"

        # Re-fetching /result again does not double-record (idempotent) --
        # completed_missions still lists M-1 exactly once.
        _poll_result(client, run_id)
        assert store.completed_missions(code, "quarkqueen", env=env) == ["M-1"]

        progress = client.get("/api/progress").json()
        assert {m["id"]: m["state"] for m in progress["missions"]} == {"M-1": "done", "M-2": "open"}

    # A fresh client, re-joining the same pair, sees identical progress.
    with TestClient(create_app(env=env)) as client2:
        rejoined = client2.post("/api/join", json={"classCode": code, "nickname": "quarkqueen"})
        assert {m["id"]: m["state"] for m in rejoined.json()["missions"]} == {"M-1": "done", "M-2": "open"}

        # A forged cookie -- a real class code with a nickname nobody ever
        # joined under -- is anonymous everywhere: `/api/progress`'s student
        # is null, and an M-2 run (locked for an anonymous requester) is a
        # 400, never a 500 (C10/F1).
        with TestClient(create_app(env=env)) as forger:
            forger.cookies.set("fce_student", f"{code}:impostor")
            forged_progress = forger.get("/api/progress")
            assert forged_progress.json()["student"] is None
            forged_run = forger.post("/api/run", json={"missionId": "M-2", "graph": _graph()})
            assert forged_run.status_code == 400
            assert forged_run.json()["nodeId"] is None

        store.purge_class(code, env=env)

        # The old cookie names a class that no longer exists -- not joined.
        after_purge = client2.get("/api/progress")
        assert after_purge.json()["student"] is None

    # F7: the student's class is purged after submit but before the run's
    # objective is checked -- record_completion's FK must not fire a 500;
    # `/result` still returns 200, nothing recorded, unlocked stays null.
    code3 = store.create_class(env=env)
    with TestClient(create_app(env=env)) as client3:
        client3.post("/api/join", json={"classCode": code3, "nickname": "purgee"})
        run_id3 = client3.post("/api/run", json={"missionId": "M-1", "graph": _graph()}).json()["runId"]
        store.purge_class(code3, env=env)
        result3 = _poll_result(client3, run_id3)
        assert result3.status_code == 200
        assert result3.json()["objective"]["unlocked"] is None
        assert store.completed_missions(code3, "purgee", env=env) == []
