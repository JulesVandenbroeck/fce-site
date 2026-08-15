# Backlog

Two things land here:

1. **Suggested-minor** review findings — always, automatically. They never block a task.
   Group them by area; the orchestrator raises a single cleanup task per area once a group
   is worth sweeping.
2. **Suggested-major** findings the coder overruled on the grounds that they belong to a
   different future task. Record the coder's argument alongside, so the decision is
   auditable later.

Entries carry the task ID they came from, so context is recoverable.

---

## Backend

- **`.flake8` `exclude` omits `.venv`.** `.flake8:16`. The list replaces flake8's defaults,
  so a bare `flake8 .` from the repo root reports ~40,000 errors, all from `.venv/`. The
  specified `flake8 src/ tests/` is clean so nothing is blocked today, but CI or a
  pre-commit hook running `flake8 .` would be unusable. Fix: add `.venv, venv` to the
  exclude line. _(from B-001 review)_
- **PyYAML is only a transitive dependency.** `pyproject.toml:27`. `import yaml` works
  today solely because `pyhf` pulls it in. `missions.py` will need it directly per shared
  §7 — declare it explicitly rather than inheriting it by accident. _(from B-001 review)_
- **No `README.md`.** Packaging metadata has no long description, and the repo has no entry
  point for a human arriving cold. _(from B-001)_
- **No CI workflow.** `.flake8` excludes `.github`, implying one is expected. A workflow
  running `pytest` + `flake8` on push would catch regressions the reviewer currently
  catches by hand. Depends on the `.venv` exclude fix above. _(from B-001)_
- **Dependencies unpinned, no lock file.** Fine now, but a scientific-Python stack drifts.
  Worth resolving before classroom deployment so a teacher's install matches the tested
  one. _(from B-001)_

## Frontend

_none_

## Design

_none_

## Cross-cutting

- **Dark colour variant.** V1 commits to light only — the lab-notebook aesthetic is a light
  object and a badly-done dark mode is worse than none. A "darkroom" variant is a candidate
  once the light system is settled. _(from the design direction decision, not a review)_
