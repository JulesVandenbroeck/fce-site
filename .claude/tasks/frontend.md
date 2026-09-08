# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

### F-004 — Port the three-region shell into the app
- **Scope:** `src/fce_web/templates/` (the shell template, `base.html`),
  `src/fce_web/static/js/shell.js`, `tests/e2e/test_shell.py`
- **Accept:** C1-C7 in the plan. Three regions per the 2026-09-01 ruling (canvas always
  present, palette left/collapsible, mission panel right/expandable); collapse and expand
  keyboard-operable; `shell.html:90-310`'s inline script becomes a module file; zero inline
  `style=`; `PageActivity.console_errors == []` and `bad_responses == []`.
- **Depends on:** nothing. **Blocks F-005 and D-015.**
- **Branch / PR:** `task/f-004-shell-port` — not yet opened
- **Status:** in progress (cycle 1) — **re-dispatched 2026-09-08**. The first dispatch died
  producing nothing: branch sat at `main` (`39d73db`) with a clean worktree, no remote, no PR.
  Confirmed against git, so **cycle 1 restarts from zero — this is not cycle 2.** Criteria
  C1-C7 live in `docs/plan-m3-vertical-slice.md` `### F-004` (:377); the coder copies them into the
  PR body, which must also list the region class names and `data-state` attributes D-015 consumes.
- **Worktree:** `.claude/worktrees/agent-ac37115050f4366c3`, reused from the dead dispatch — the
  branch is checked out there, so a fresh `worktree add` would fail. The coder is told not to.
- **Note:** writes **no CSS** — the page is expected to look unstyled. D-015 styles it in wave 3.
  If a new route is needed, stop and report: `routes/pages.py` is backend's.

## Ready

_none — F-004 is in progress; everything else is blocked behind it or behind M3 wave 2._
Plan: [`docs/plan-m3-vertical-slice.md`](../../docs/plan-m3-vertical-slice.md).

## Blocked

### F-003 — Prove the four woff2 are actually served
- **Depends on:** **D-015** — the first task to apply `font-family: var(--font-body)` to a real
  selector in `src/fce_web/static/css/`. That task now exists; full entry below under
  `## Deferred`, unchanged. Wave 4.
### F-005 — Port the Bench canvas
- **Depends on:** F-004. Consumes B-020's payload shape read-only. Wave 2.
### F-006 — The merged `Observable` node interior
- **Depends on:** F-005. Ports **`observable.html`** (D-013), *not* `interiors.html` (D-009,
  superseded by the 2026-09-02 one-node ruling). Wave 3.
### F-007 — Serialise, submit, stream, show progress
- **Depends on:** F-005, F-006, B-020, B-021, B-022. Wave 5.
### F-008 — The interactive SVG histogram
- **Depends on:** B-019, F-007. Ports `plot.js`; legend toggle, PNG export, cutflow and Z gauge
  are explicitly out of scope by the user's 2026-09-07 ruling. Wave 5.

## Done

Full entries are in [`archive/frontend.md`](archive/frontend.md). Read it only when a task's
history is actually in question.

- **F-002** — linked `tokens.css` into `base.html` — #30, `78c0b3c`, 1 cycle + 1 re-spec,
  clean gate (`findings=2, verdict=approve`). checks=6, **5 live + C2 retired** (subsumed by
  C3+C4, proven by the reviewer's mutation; retired in the PR body, not erased). Suite floor
  → **596**; `tests/e2e/` 25 → 27 nodeids. The load-bearing check is
  `test_tokens_stylesheet_is_applied`: `--font-body` read off `:root` at runtime, shown red
  under a mutated `href`. **The four woff2 remain unexercised — see F-003, not a gap in this
  task.** F2 (my file scope contradicted the ownership table) → the user's 2026-09-07 ruling,
  now in `shared/CLAUDE.md` §4.
- **F-001** — Minimal page shell: base layout and index template — `task/f-001-page-shell` #1,
  merged `176f7d5` (1 cycle, no rework)

## Deferred

### F-003 — Prove the four woff2 are actually served
- **Why:** F-002 links `tokens.css` but cannot exercise the fonts — `tokens.css` applies
  `font-family` to nothing, so no face is ever fetched, and "no font 404s" passes vacuously.
  The four files under `src/fce_web/static/fonts/` have therefore **never been served**, and
  their `src:` URLs are all relative (`url("../fonts/<name>.woff2")` at `tokens.css:54, :62,
  :70, :78`), resolving against `/static/css/` — so they work only if the sheet is served from
  that exact path. Nothing has tested that.
- **Accept:** loading a page whose CSS actually uses `var(--font-body)` and `var(--font-mono)`
  requests all four woff2 and every one returns 200. Falsifiability shown by breaking one
  `src:` path and watching the named test go red. **The check must assert the four are
  requested, not merely that nothing failed** — the vacuity is the whole point of this task.
- **Depends on:** the first design task that applies `font-family: var(--font-body)` to a real
  selector in `src/fce_web/static/css/`. No such task exists yet; it arrives with the app's
  first main stylesheet, which is M6 work or whenever M3 needs one.
- **Branch / PR:** not yet opened
