# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

_none_

## Ready

### B-003 — Playwright harness and a screenshot helper
- **Scope:** `pyproject.toml` (dev extra), `tests/e2e/__init__.py`,
  `tests/e2e/conftest.py`, `tests/e2e/test_smoke.py`, `scripts/screenshot.py`
- **Accept:** Playwright installs via pip (no npm); a fixture boots the app on an ephemeral
  port and tears it down; one e2e test asserts `/` renders with zero console errors;
  `scripts/screenshot.py <route>` writes PNGs at 1440/1024/768 and prints the paths.
  This is the tool the reviewer and design role depend on, so it must work unattended.
- **Added 2026-08-16, from the B-002 review:** the e2e smoke test must also assert **zero
  requests to non-local hosts**. The unit-level sweep in `tests/test_app.py` cannot see
  inside CSS, so `@import url(https://fonts.googleapis.com/…)` — the likeliest future §3
  breach, arriving with D-002's stylesheets — would pass it. A browser-level assertion
  catches whatever the page actually fetches, which is the guarantee shared §3 needs.
- **Depends on:** B-002 (**done**, merged `ff801fa`)
- **Branch / PR:** `task/b-003-playwright-harness` — not yet opened

## Blocked

_none_

## Done — most recent first

### B-002 — FastAPI app factory and a served index route
- **Scope:** `src/fce_web/app.py`, `src/fce_web/routes/__init__.py`,
  `src/fce_web/routes/pages.py`, `tests/test_app.py`
- **Accept:** `create_app()` returns a FastAPI instance; `GET /` returns 200 with
  `text/html`, rendering `templates/index.html` with `title`; `StaticFiles` mounted at
  `/static` from `src/fce_web/static/` with `name="static"`, so `GET /static/js/app.js`
  returns 200; `Jinja2Templates` configured against `src/fce_web/templates/`; tested via
  `TestClient`, no live server needed
- **Depends on:** B-001 (done) and F-001 (**done**, merged `176f7d5`) — `templates/` and
  `static/` are front-end owned (shared §4) and now exist on `main`
- **Contract from F-001, not negotiable:** render `index.html` with exactly
  `{"title": <str>}` — the templates use `StrictUndefined`-clean single-variable context and
  reference static assets as the literal path `/static/js/app.js`, so the mount must be at
  `/static` from `src/fce_web/static/` or the page 404s its own script.
- **Branch / PR:** `task/b-002-app-factory` — #3
- **Status:** **done** (2 cycles) — merged as `ff801fa`. Verified on `main` after merging:
  26 tests pass, `/` → 200 HTML, `/static/js/app.js` → 200 JS, `/docs` and `/redoc` → 404.
- **Review, cycle 2:** 0 required, 0 suggested-major, 1 suggested-minor → backlogged (the
  external-host sweep does not cover static CSS; partly mitigated by the assertion added to
  B-003). The reviewer re-verified the fix against a live socket, probed the static mount
  for traversal and directory listing (all 404), mutation-tested both guards, and checked
  the cycle-1 overrule by opening `backlog.md` rather than taking it on trust — concluding
  that fixing it in scope would itself have been a `Required` scope finding.
- **Cycle 2 resolution:** required finding fixed — `docs_url=None, redoc_url=None`, which
  also removed a fourth remote-asset route the review had not spotted,
  `/docs/oauth2-redirect` (registered only when `docs_url` is set). `/openapi.json` kept
  deliberately: its body contains no absolute URL, so it breaches nothing in §3 — the
  offence was the two HTML pages that *render* the schema — and it is the machine-readable
  check that `docs/api.md` matches the routes that actually exist. Making the API surface
  non-enumerable is an API-policy call, not a §3 fix, so it was not made unilaterally →
  backlogged. Suggested-major overruled in writing → recorded in `backlog.md`.
  Suggested-minor left untouched as instructed, to keep the diff about the one required
  change.
- **Review, cycle 1:** 1 required, 1 suggested-major, 1 suggested-minor.
  - *Required* — `create_app()` left FastAPI's default `/docs` and `/redoc` enabled, and
    those pages pull Swagger UI and ReDoc from `cdn.jsdelivr.net` plus a Google-hosted font.
    That is a CDN link, a remote script and a runtime external font — three of the hard
    prohibitions in shared §3 — on an app whose whole point is to run in a classroom with no
    internet. Verified live by the reviewer, not inferred. Fix is inside scope:
    `docs_url=None, redoc_url=None`.
  - *Suggested-major* — the built wheel ships no `templates/` or `static/`, so under a
    non-editable install `create_app()` raises at the mount. Real, and already recorded in
    the backlog from the F-001 review; the fix needs `package-data`, which this task's
    `pyproject.toml` scope ("only add httpx") excludes. Expected resolution: coder overrules
    it as belonging to a follow-up packaging task.
  - *Suggested-minor* → backlogged (the module-state guard enumerates types, so it is
    allow-by-default).
- **Dependency sign-off:** `httpx` added to the `dev` extra **only**, approved by the user
  2026-08-15 (`TestClient` requires it). Test tooling; it must never become a runtime
  dependency. This is the first exercise of the new-dependency gate — record future ones
  the same way.

### B-001 — Python package skeleton, packaging, and a green test suite
- **Scope:** `pyproject.toml`, `.flake8`, `.gitignore`, `src/fce_web/__init__.py`,
  `tests/__init__.py`, `tests/test_skeleton.py`
- **Accept:** all five criteria met and independently re-verified by review
- **Depends on:** nothing
- **Branch / PR:** none — **B-001 predates the branch-per-task policy** (added
  2026-08-15, `.claude/orchestrator/CLAUDE.md` §4). Its files were written directly in the
  working tree. B-002 is the first back-end task to go through branch → PR → review →
  merge.
- **Status:** **done** (1 cycle, no rework)
- **Review:** 0 required, 0 suggested-major, 2 suggested-minor → backlogged
- **Notes:** venv at `.venv/bin/python` (Ubuntu system Python is PEP 668
  externally-managed) — later back-end tasks must use it, not `python3`. Python 3.12.3.
  `tests/` is a package, so `tests/e2e/` needs its own `__init__.py`. Reviewer
  mutation-tested all 8 tests: none are no-ops.
