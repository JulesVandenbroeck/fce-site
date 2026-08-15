# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

_none_

## Ready

### B-002 — FastAPI app factory and a served index route
- **Scope:** `src/fce_web/app.py`, `src/fce_web/routes/__init__.py`,
  `src/fce_web/routes/pages.py`, `tests/test_app.py`
- **Accept:** `create_app()` returns a FastAPI instance; `GET /` returns 200 and HTML;
  static files mounted at `/static`; Jinja2 environment configured against
  `src/fce_web/templates/`; tested via `TestClient`, no live server needed
- **Depends on:** B-001
- **Branch / PR:** `task/b-002-app-factory` — not yet opened

### B-003 — Playwright harness and a screenshot helper
- **Scope:** `pyproject.toml` (dev extra), `tests/e2e/__init__.py`,
  `tests/e2e/conftest.py`, `tests/e2e/test_smoke.py`, `scripts/screenshot.py`
- **Accept:** Playwright installs via pip (no npm); a fixture boots the app on an ephemeral
  port and tears it down; one e2e test asserts `/` renders with zero console errors;
  `scripts/screenshot.py <route>` writes PNGs at 1440/1024/768 and prints the paths.
  This is the tool the reviewer and design role depend on, so it must work unattended.
- **Depends on:** B-002
- **Branch / PR:** `task/b-003-playwright-harness` — not yet opened

## Blocked

_none_ — the baseline blocker cleared 2026-08-15: `main` is at `bc8c7d9` with the workflow
and B-001's output, and `origin/main` matches. Task branches can be cut from it.

## Done

### B-001 — Python package skeleton, packaging, and a green test suite
- **Scope:** `pyproject.toml`, `.flake8`, `.gitignore`, `src/fce_web/__init__.py`,
  `tests/__init__.py`, `tests/test_skeleton.py`
- **Accept:** all five criteria met and independently re-verified by review
- **Depends on:** nothing
- **Branch / PR:** none — **B-001 predates the branch-per-task policy** (added
  2026-08-15, `.claude/orchestrator/CLAUDE.md` §4). Its files were written directly in the
  working tree. B-002 is the first task to go through branch → PR → review → merge.
- **Status:** **done** (1 cycle, no rework)
- **Review:** 0 required, 0 suggested-major, 2 suggested-minor → backlogged
- **Notes:** venv at `.venv/bin/python` (Ubuntu system Python is PEP 668
  externally-managed) — later back-end tasks must use it, not `python3`. Python 3.12.3.
  `tests/` is a package, so `tests/e2e/` needs its own `__init__.py`. Reviewer
  mutation-tested all 8 tests: none are no-ops.
