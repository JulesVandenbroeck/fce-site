# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

### F-006 — The merged `Observable` node interior
- **Scope:** `static/js/graph.js`, `templates/shell.html` (node markup, no CSS),
  `tests/e2e/test_graph.py`
- **Accept:** C1-C7 in the plan. One `Observable` node, four modes, **`observable.html`
  (D-013) is the source — `interiors.html` (D-009) is superseded and using it is a defect**;
  the node grows in place, no flyout; mode is `config` not identity, `kind` stays
  `Observable` in the exported model; D-013's footprint contract reported, not invented;
  a keyboard/accessible-name check **that can go red**; floor >= 664, flake8 0, e2e count
  reported (47 at F-005).
- **Depends on:** F-005 (merged `b7fdfdf`). Wave 3.
- **Branch / PR:** `task/f-006-observable-interior` — not yet opened
- **Status:** dispatched (cycle 1), `isolation: worktree`

## Ready

_none — D-015 follows F-006, F-007 follows F-006 plus B-022._

## Blocked

### F-003 — Prove the four woff2 are actually served
- **Depends on:** **D-015** — the first task to apply `font-family: var(--font-body)` to a real
  selector in `src/fce_web/static/css/`. That task now exists; full entry below under
  `## Deferred`, unchanged. Wave 4.
### F-007 — Serialise, submit, stream, show progress
- **Depends on:** F-005, F-006, B-020, B-021, B-022. Wave 5.
### F-008 — The interactive SVG histogram
- **Depends on:** B-019, F-007. Ports `plot.js`; legend toggle, PNG export, cutflow and Z gauge
  are explicitly out of scope by the user's 2026-09-07 ruling. Wave 5.

## Done

Full entries are in [`archive/frontend.md`](archive/frontend.md). Read it only when a task's
history is actually in question.

- **F-005** — port the Bench canvas — #36, `b7fdfdf`, 2 cycles, clean gate
  (`findings=1, verdict=approve`; F10 backlogged). checks=10. Suite floor → **664**;
  `tests/e2e/` 45 → **47** nodeids. Ships `static/js/graph.js` and the canvas markup:
  four-kind palette, pointer place/drag/connect, **a full keyboard path**, and a client
  legality table the reviewer verified against `graph.py` behaviourally — all 16 ordered
  pairs driven through the real keyboard path, `mismatches: []`.
  **Contract for F-007, verbatim in PR #36's body:** the exported graph model is
  `nodes` as a **list** of `{id, kind, x, y}` and `edges` as `[fromId, toId]` pairs.
  Cycle 1 published it keyed by id — **my error, corrected at
  `docs/plan-m3-vertical-slice.md:494`**; `build_run_config` (`graph.py:338`) reads a list,
  and `_parse_nodes` ignores the ride-along `x`/`y`.
  **The cycle-1 defect worth remembering:** no duplicate-edge guard, and the server does not
  reject one — `build_run_config` emitted **two identical `HistogramConfig`s**, so a student
  double-pressing would silently run and plot the analysis twice. Now guarded at the client
  and mutation-verified red on both keyboard and pointer.
  Cycle 2 also deleted ~40 lines of speculative markup (`node__links`, `.port--absent`
  spacers, a `node--flash` reflow hack, a spawn stagger, a duplicated drag teardown).
  **F-006 and D-015 are released by this merge.**
- **F-004** — ported the three-region shell into the app — #32, `30cceb3`, 2 cycles, clean gate
  (`findings=2, verdict=approve`). checks=8 (C8 added on cycle 2 for uncaught page errors).
  Suite floor → **615**; `tests/e2e/` 27 → **37** nodeids. Ships `templates/shell.html` (included
  from `index.html`) and `static/js/shell.js`, **59 lines — the two toggles and nothing else**;
  cycle 2 deleted ~115 lines of dead payload builder, untested exemplar node cards and duplicated
  mission text. No CSS, by design — D-015 styles it.
  **Contract for D-015, verbatim in PR #32's body:** the region class / `data-state` table, which
  the reviewer checked against the shipped markup. `#palette` is `aria-labelledby="palette-title"`,
  `#mission-panel` is `aria-label="Mission"`, `#canvas-region` is `aria-label="Analysis canvas
  region"`, `#canvas-wrap` carries only `class` and `id`, `#nodes-layer` is empty, and collapsing
  sets the **`hidden`** attribute on `#palette-list`/`#mission-panel-body` as well as
  `data-state` — so design may hide them with any CSS technique without stranding keyboard focus.
  Also introduces an `sr-only` class needing a visually-hidden rule. F8/F9 backlogged.
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
