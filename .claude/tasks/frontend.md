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
- **Branch / PR:** `task/f-004-shell-port` at `66bf893` — **#32, open**
- **Status:** in review (cycle 2) — `code-reviewer` re-dispatched 2026-09-08 with the cycle-1
  review URL and F1-F7. Cycle-2 head `66bf893`. §5.1 gate **PASSED** in `~/fce-gate-f004`:
  `615 passed` (605 floor + 10), flake8 0, `tests/e2e/` 37 nodeids, scope exactly four files.
  Coder reports all seven findings fixed, **none overruled**, with a mutation proof on F1
  (breaking `#palette-toggle`'s id now turns the test RED; it stayed green under exactly that
  mutation on cycle 1). ~115 lines of JS deleted — `shell.js` keeps only the two toggles.
- **Cycle-1 record:** re-dispatched 2026-09-08 with the review URL and F1-F7.
  Cycle 1 gate PASSED; review `findings=7, scope=pass, verdict=rework`
  ([comment](https://github.com/JulesVandenbroeck/fce-site/pull/32#issuecomment-5582424817)).
  **checks 7 → 8**: C8 added for uncaught page errors.
- **Review:** 7 findings, verdict=rework. F1 blocking — `test_shell_page_logs_no_console_errors`
  passes when `shell.js` throws on load, because an uncaught module exception is a Playwright
  `pageerror`, not a console error; the reviewer proved it by breaking an id and watching the
  test stay green. F5/F6/F7 accessibility (unnamed `<aside>` landmarks; a dead `tabindex="0"`
  canvas tab stop; collapsed regions left in the tab order). F2/F3/F4 deletions (~115 lines of
  dead payload builder, untested exemplar node cards, and mission text duplicated between
  template and JS).
- **§5.4 diagnosis — this is a CYCLE, clause 3, and the drafting defect is mine.** Nothing was
  dropped from a prior cycle (clause 1 does not apply), and C4 shipped *with* a command and is
  *met as written* (clause 2 does not apply). F1 is against a property no criterion gated, so it
  counts. But it is §2's *"state the property, not only the method — or the method becomes the
  ceiling"*, the B-006 cycle-2 shape exactly: I wrote the mechanism (`console_errors == []`) and
  got that mechanism and nothing else. C8 now states the property — no uncaught JS error on load
  — and names `page_errors` as one instrument, not as the definition.
- **Cycle-1 gate (still the record):** §5.1 free gate
  **PASSED** in `~/fce-gate-f004` (detached off `origin/task/f-004-shell-port`):
  `606 passed, 0 failed`, `flake8 src/ tests/ scripts/` → 0, `tests/e2e/` **27 → 37** nodeids,
  and `git diff origin/main...HEAD --name-only` returns exactly the four scoped files. Every
  number in the PR body reproduced. PR body carries scope, C1-C7 with IDs and evidence, the
  region/`data-state` table for D-015, and the transcript — §4 rule 3 satisfied.
  **The first dispatch of this task died producing nothing** (branch at `main`, clean worktree,
  no PR); confirmed against git, so **this is cycle 1, not cycle 2.**
- **Worktree:** `.claude/worktrees/agent-ac37115050f4366c3`, reused from the dead dispatch — the
  branch is checked out there, so a fresh `worktree add` would fail. The coder is told not to.
- **Note:** writes **no CSS** — the page is expected to look unstyled. D-015 styles it in wave 3.
- **Deviations accepted at the gate:** shipped as an included partial `shell.html` rather than a
  standalone `mission.html` (the plan left the choice to the coder), `base.html` untouched, and
  the ported script's `window.buildRunPayload` global dropped per shared §6's no-globals rule.
- **For D-015:** the region class names and `data-state` values are in PR #32's body under
  *Region class names and `data-state` values*. It also introduces an `sr-only` class for the
  toggles' screen-reader text, which needs a visually-hidden rule if the CSS has none.

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
