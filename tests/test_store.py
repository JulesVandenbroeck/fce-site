"""Tests for fce_web.store: the checks that must go red if privacy/isolation break.

``env`` is an explicit mapping pointing FCE_HOME at a tmp dir -- never process-env
mutation (``.claude/shared/CLAUDE.md`` §6), matching how the rest of the app threads env.
"""
import sqlite3

import pytest

from fce_web import store


@pytest.fixture
def env(tmp_path):
    return {"FCE_HOME": str(tmp_path)}


def test_join_rejects_unknown_class_and_bad_nickname(env):
    with pytest.raises(ValueError):
        store.join("NOSUCH", "alice", env=env)

    code = store.create_class(env=env)
    with pytest.raises(ValueError):
        store.join(code, "a b!", env=env)  # space and ! not allowed


def test_join_is_idempotent(env):
    code = store.create_class(env=env)
    store.join(code, "alice", env=env)
    store.join(code, "alice", env=env)  # must not raise
    with sqlite3.connect(store._db_path(env)) as conn:
        n = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    assert n == 1


def test_purge_removes_every_row(env):
    code = store.create_class(env=env)
    store.join(code, "alice", env=env)
    store.record_completion(code, "alice", "m-1", "{}", env=env)

    counts = store.purge_class(code, env=env)
    assert counts == {"classes": 1, "students": 1, "completions": 1}

    with sqlite3.connect(store._db_path(env)) as conn:
        for table in ("classes", "students", "completions"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0

    assert not store.class_exists(code, env=env)
    with pytest.raises(ValueError):
        store.purge_class(code, env=env)


def test_completed_missions_and_cli_roundtrip(env, capsys):
    from fce_web.store import _main

    assert _main(["create-class"], env=env) == 0
    code = capsys.readouterr().out.strip()

    store.join(code, "bob", env=env)
    store.record_completion(code, "bob", "m-1", "{}", env=env)
    assert store.completed_missions(code, "bob", env=env) == ["m-1"]

    assert _main(["purge", code], env=env) == 0
    assert _main(["purge", code], env=env) == 1  # already gone
