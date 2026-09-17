# Backlog

Swept 2026-09-17. Everything before the sweep, verbatim, lives in
[`archive/backlog-2026-09-17.md`](archive/backlog-2026-09-17.md) — cite items from there by
their original tag (`B-022 F14`, `D-016 F2`, …). Nothing was deleted.

The sweep split the old list three ways:

1. **Useful** — below. Real product or robustness work; each wants its own task when its
   milestone comes up. Not dispatched.
2. **Cleanup** — handed to **B-029 / F-013 / D-019** (one per role, see the role lists).
3. **Dropped** — closed by later work, superseded, or history only. Listed at the bottom with the reason.

Count: `grep -c '^- \*\*' .claude/tasks/backlog.md`. Add new findings under `## New`.

---

## Useful — raise as tasks when their milestone comes up

- **U1 Installable for a classroom** (backend; **needs user sign-off on dependencies**). A wheel
  omits `templates/`, `static/`, `content/` (B-001/F-001/B-002, confirmed three times); PyYAML is
  only transitive (M5's `missions.py` needs it); dependencies unpinned; **a fresh venv fails
  collection** because unpinned `fastapi` pulls a `starlette` whose `TestClient` wants `httpx2`
  (B-027 note, B-002). Before any teacher installs this.
- **U2 Per-job output directory** (backend, before M5 classroom use). `analytical_loop.py` writes
  `output/hist{plot_idx}_{sample}.root` keyed on `plot_idx` only, so `JobRegistry._run_lock`
  serialises every student's run. Per-job dir → drop the lock. _(B-021)_
- **U3 Vectorise `and`/`or` in `safe_eval`** (backend). `l1.pt > 20 and l2.pt > 10` — the most
  common student shape — silently falls off the vectorised path. Rewrite `BoolOp` to `&`/`|`.
  Speed only, no number changes. _(M2 planning)_
- **U4 `fit.method` surfaced** (backend + frontend, when M5 shows μ/Z). `run_fit` returns `(mu, sig)`
  from three different methods (HistFactory MLE, counting ratio, `s/√b` after a swallowed pyhf
  failure) under the same names. A `s/√b` must not be shown as a fitted signal strength.
- **U5 Module-level-state guard → default-deny** (backend). `tests/test_app.py`'s scan enumerates
  forbidden types, so a module-level `threading.Lock()` or registry object passes. Allow only
  inert types. This guards the project's founding defect. _(B-002)_
- **U6 CI** (backend, optional). pytest + flake8 on push. Needs `.venv` in `.flake8` exclude (in
  B-029). Know that `test_real_end_to_end_run_exercises_the_real_run_physics_loop` skips without
  `~/.fce/datasets`, and `_make_unwritable` skips under root. _(B-001, B-011, B-005)_
- **U7 Accessibility chrome** (frontend, M6). Skip link, `<header>/<nav>/<footer>` landmarks once
  there is chrome, `aria-live` on run progress/results if F-007 did not already add it, offline
  HTML validation in e2e. _(F-001)_
- **U8 Design ideas for M5/M6** (design). Face-down locked cards to show gating (mission unlocks
  now read *inside* a node); a per-cut "events kept: N of M" preview before running; mission 1 as a
  stepped Focus Stage, full spread from mission 2 — playtest, don't assume. _(D-001)_
- **U9 Dark "darkroom" variant** (design, post-M6). Light only for V1.
- **U10 Constraints to attach to future tasks** — not tasks themselves:
  - if M5+ wants `**` in expressions, bound the exponent; never re-admit it unbounded (B-006);
  - whoever vendors `cutflow_plotter`: `ImportError` inside it reads as "deferred", and a plot
    failure discards a finished `RunResult` (B-009 c2);
  - `--frozen-x2` 3.12:1 and `--syst-grey` 3.24:1 on `--paper` clear 3:1 by <0.25 — warming
    `--paper` breaks both (D-002);
  - at 1024/768 `.canvas-region` h-scroll can put the leftmost node out of reach for coordinate
    clicks in e2e (D-018);
  - `safe_eval` reports the canonical `__class__` escape with the `Call` message, not the
    underscore one — reorder checks if student-facing error copy is ever reworked (B-006).

## New

_none._

---

## Dropped in the sweep, and why

- **All `docs/wireframes/` items** (D-001) — superseded 2026-08-16; the directory is a record.
- **All `docs/design-explorations/` items** (D-003, D-004, D-005, D-007, D-008, D-009, D-010, D-013,
  D-002 m5/m6, `check_no_fabricated_identifiers`) — exploration pages are historical; the shipped
  app is in `src/`. Their lessons are already in the manuals.
- **PR-body-only corrections** (B-007, B-012 m2, B-024 F4, D-004, D-005 m7/m8, D-009 m4, D-013 m4) —
  merged PR bodies are history.
- **`get_fce_home()` ignoring `env`** (B-011 c2, B-018, B-023 candidate) — closed by B-024.
- **B-015 m2** (observable exprs not gated) — closed by B-026, which compiles Selection/Observable
  expressions at submit.
- **F-004 F8, D-010 m3** (pagers do nothing) — closed by F-010 + D-017.
- **B-018 fixture readability** — closed by B-025. **F-007 F11** — closed by D-016.
- **B-005 monkeypatch lesson, `comm -23` instrument** — already promoted into the manuals.
- **B-003 test restructuring** (conftest helper move, stuck-navigation wiring test,
  `NavigationStuckError`), **B-002 external-host sweep** (mitigated by B-003's e2e request check),
  **B-013 m1 conftest `__debug__` guard**, **B-012 m6**, **B-007 perturbed-doc test** — churn with
  no defect behind it; ponytail says no.
- **`--node-observable` token** (D-013) — check folded into D-019; drop if it exists.
