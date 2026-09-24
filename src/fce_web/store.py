"""Persistence for class codes, students and mission completions.

Stdlib ``sqlite3`` only, one file at ``get_fce_home(env)/fce.sqlite3``. No ORM: routes call
the functions below, never write SQL themselves (``.claude/backend/CLAUDE.md`` §5).

Privacy (GDPR -- users are minors, ``.claude/backend/CLAUDE.md`` §5): the schema stores
**only** class code, nickname, mission id, the completing analysis graph and a timestamp.
No real names, no IP addresses, no free text. A teacher-invokable purge deletes a class and
everything under it -- see ``docs/teacher.md``.

*env* is threaded exactly as the rest of the app (``app.py``'s ``create_app(env=...)``,
``paths.get_fce_home(env)``): an optional mapping passed explicitly, never read from or
written to process environment, and nothing cached at module level
(``.claude/shared/CLAUDE.md`` §6 -- no module-level mutable state).
"""
import argparse
import re
import secrets
import sqlite3
import sys
from pathlib import Path
from typing import Mapping, Optional

from fce_web.paths import get_fce_home

_SCHEMA = """
CREATE TABLE IF NOT EXISTS classes (
    code TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS students (
    class_code TEXT NOT NULL REFERENCES classes(code),
    nickname TEXT NOT NULL,
    PRIMARY KEY (class_code, nickname)
);
CREATE TABLE IF NOT EXISTS completions (
    class_code TEXT NOT NULL,
    nickname TEXT NOT NULL,
    mission_id TEXT NOT NULL,
    graph_json TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (class_code, nickname, mission_id),
    FOREIGN KEY (class_code, nickname) REFERENCES students(class_code, nickname)
);
"""

_CODE_ALPHABET = "ACDEFGHJKLMNPQRTUVWXY34679"  # unambiguous: no 0/O, 1/I/l, 2/Z, 5/S, 8/B
_NICKNAME_RE = re.compile(r"^[A-Za-z0-9_-]{2,20}$")


def _db_path(env: Optional[Mapping[str, str]] = None) -> Path:
    return get_fce_home(env) / "fce.sqlite3"


def _connect(env: Optional[Mapping[str, str]] = None) -> sqlite3.Connection:
    """Open a connection with the schema ensured and foreign keys enforced.

    A fresh connection per call, per ``.claude/backend/CLAUDE.md`` §5 ("connection per
    request or a thread-local; sqlite3 connections are not thread-safe").
    """
    conn = sqlite3.connect(_db_path(env))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    return conn


def validate_nickname(nickname: str) -> Optional[str]:
    """Return an error message a 15-year-old understands, or ``None`` if valid."""
    if not _NICKNAME_RE.match(nickname):
        return "Nicknames are 2-20 characters: letters, numbers, _ and - only. No spaces."
    return None


def create_class(env: Optional[Mapping[str, str]] = None) -> str:
    """Create a class with a new random code and return it."""
    with _connect(env) as conn:
        while True:
            code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
            try:
                conn.execute("INSERT INTO classes (code) VALUES (?)", (code,))
            except sqlite3.IntegrityError:
                continue
            return code


def class_exists(code: str, env: Optional[Mapping[str, str]] = None) -> bool:
    """Return whether *code* names a class."""
    with _connect(env) as conn:
        row = conn.execute("SELECT 1 FROM classes WHERE code = ?", (code,)).fetchone()
    return row is not None


def student_exists(code: str, nickname: str, env: Optional[Mapping[str, str]] = None) -> bool:
    """Return whether *nickname* has joined class *code* (B-034 cycle 2, F1) --
    ``class_exists`` alone is not enough: a cookie can name a real class with a
    nickname nobody joined under."""
    with _connect(env) as conn:
        row = conn.execute(
            "SELECT 1 FROM students WHERE class_code = ? AND nickname = ?", (code, nickname)
        ).fetchone()
    return row is not None


def join(code: str, nickname: str, env: Optional[Mapping[str, str]] = None) -> None:
    """Register *nickname* under class *code*. Idempotent for the same pair.

    Raises ``ValueError`` if the class does not exist or the nickname is invalid.
    """
    error = validate_nickname(nickname)
    if error is not None:
        raise ValueError(error)
    if not class_exists(code, env):
        raise ValueError(f"Class code '{code}' does not exist.")
    with _connect(env) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO students (class_code, nickname) VALUES (?, ?)",
            (code, nickname),
        )


def record_completion(
    code: str,
    nickname: str,
    mission_id: str,
    graph_json: str,
    env: Optional[Mapping[str, str]] = None,
) -> None:
    """Record that *nickname* completed *mission_id*. Idempotent per student+mission."""
    with _connect(env) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO completions (class_code, nickname, mission_id, graph_json)"
            " VALUES (?, ?, ?, ?)",
            (code, nickname, mission_id, graph_json),
        )


def completed_missions(code: str, nickname: str, env: Optional[Mapping[str, str]] = None) -> list:
    """Return the list of mission ids *nickname* has completed, in completion order."""
    with _connect(env) as conn:
        rows = conn.execute(
            "SELECT mission_id FROM completions WHERE class_code = ? AND nickname = ?"
            " ORDER BY rowid",
            (code, nickname),
        ).fetchall()
    return [row[0] for row in rows]


def purge_class(code: str, env: Optional[Mapping[str, str]] = None) -> dict:
    """Delete a class and every student/completion row under it.

    Returns a count dict. Raises ``ValueError`` if the class does not exist -- checked by the
    ``classes`` delete itself removing 0 rows, inside the same transaction as the other two
    deletes, so an unknown code rolls back rather than leaving a partial purge.
    """
    with _connect(env) as conn:
        completions = conn.execute(
            "DELETE FROM completions WHERE class_code = ?", (code,)
        ).rowcount
        students = conn.execute(
            "DELETE FROM students WHERE class_code = ?", (code,)
        ).rowcount
        classes = conn.execute(
            "DELETE FROM classes WHERE code = ?", (code,)
        ).rowcount
        if classes == 0:
            raise ValueError(f"Class code '{code}' does not exist.")
    return {"classes": classes, "students": students, "completions": completions}


def _main(argv: Optional[list] = None, env: Optional[Mapping[str, str]] = None) -> int:
    """Teacher CLI: ``python -m fce_web.store create-class|purge <code>``.

    *env* defaults to ``None``, which reads real process environment via
    ``get_fce_home`` -- the one place that is correct, since a CLI genuinely runs in
    the real environment. Tests pass an explicit mapping instead of mutating
    ``os.environ``.
    """
    parser = argparse.ArgumentParser(prog="python -m fce_web.store")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("create-class")
    purge_parser = sub.add_parser("purge")
    purge_parser.add_argument("code")
    args = parser.parse_args(argv)

    if args.command == "create-class":
        print(create_class(env=env))
        return 0

    try:
        counts = purge_class(args.code, env=env)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"Purged class {args.code}: {counts['students']} student(s), "
        f"{counts['completions']} completion(s) removed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
