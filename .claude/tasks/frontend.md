# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

### F-006 — The merged `Observable` node interior
- **Scope:** `static/js/graph.js`, `tests/e2e/test_graph.py` (`shell.html` was in scope and
  proved unnecessary)
- **Accept:** C1-C7 in the plan. **Total checks: 7.**
- **Depends on:** F-005 (merged `b7fdfdf`). Wave 3.
- **Branch / PR:** `task/f-006-observable-interior` — #38, head `8cb14ab`
- **Status:** **in review (cycle 2)**, head `892171b`. Gate reproduced in the primary checkout:
  `671 passed`, flake8 0, `tests/e2e/` **54** nodeids; scope exactly the two files. No hook refusal.
- **Review (cycle 1):** `findings=5, scope=pass, verdict=rework` — PR #38 comment `5631301455`.
  670 / flake8 0 / 16 reproduced; C1/C2/C3/C6 mutation-verified. **F1 blocks:** Enter on the
  summary drops focus to `<body>` (bring-to-front `appendChild` moves the focused element).
  F2 tautological C5 meta-test. F3 per-mode panel fields reach no `config` — delete unless a
  C1-C7 text requires them. F4 subtitle says "not configured" while config is ObsGlobal.
  **F5 against me: C4 (styled footprint) moved to D-015** — not dropped, relocated.
  checks 7 -> **10** (C8 focus kept, C9 subtitle matches config, C10 no discarded control,
  C11 meta-test deleted; C4 counted as moved).
- **Why there is no PR, and what the next session must do first:** the coder was refused by
  the `rtk`/worktree-isolation hook at `git add`/`commit`/`push` time — `checkout -b` and
  `rev-parse` succeeded, the mutating commands did not. It **stopped and reported rather than
  routing around it**, which is the 2026-09-08 ruling working as intended. I committed its
  diff verbatim to preserve it (nothing was edited by me; the commit message records this)
  and **deliberately did not open the PR**: the body must carry C1-C7 and the coder's own
  verification transcript, and §4 rule 3 forbids me writing it. **Re-dispatch F-006 to open
  the PR from the existing branch**, then review normally.
- **What it built:** native `<details>`/`<summary>` grow-in-place toggle, a native radio
  `<fieldset>` with the four modes, one mode panel each ported from `observable.html`,
  `growNode()` resizing the foreignObject to measured content height, bring-to-front on open
  by DOM reorder (SVG has no z-index), and `config: {mode}` in the exported `data-graph`.
  Six new e2e tests including the C5 meta-test that mutates away the accessible name.
- **C4 is honestly unmet and says so:** this app has no node CSS until D-015, so the measured
  footprints (`ObsGlobal` 276x160, `ObsObject` 277x160, `ObsVectorSum` 368x160, `ObsCustom`
  400x160, collapsed 107x160) are **not** comparable to D-013's styled 328x300 / 301.5 /
  290.5 / 237 / 80.5. They confirm the mechanism and the mode *ranking* only. A reviewer
  should treat the styled contract as D-015's to satisfy, not this task's.

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
