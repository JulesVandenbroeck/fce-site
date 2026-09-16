# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

### F-011 — Observable and Selection interiors + the expression module (**CONTRACT TASK**)
- **Scope:** new `static/js/expr.js`, `static/js/graph.js`, `static/js/run.js`, new `tests/e2e/test_interiors.py`, **+ `tests/e2e/test_graph.py` (re-spec, mine: C1 supersedes 3 F-006 assertions my scope forbade)**
- **Accept:** C1-C7 in dispatch; expression table verbatim in PR body; plan `docs/plan-m4-recipe-builder.md`
- **Depends on:** Q1 (answered)
- **Branch / PR:** `task/f-011-interiors` — #50
- **Status:** re-spec (not a cycle) — scope widened to `test_graph.py`; coder at 700/703

## Ready

_none — D-016 is next and is design's; see `design.md`._

## Blocked

_none._

## Done

Full entries are in [`archive/frontend.md`](archive/frontend.md). Read it only when a task's
history is actually in question.

- **F-008** — the interactive SVG histogram — #47, `7472675`, 2 cycles, clean gate
  (`findings=1, verdict=approve`; F9, one garbled sentence in the D-016 contract prose, folded into
  D-016's dispatch instead of another cycle). checks=11. Suite floor → **697**; `tests/e2e/` **74**.
  Ships `static/js/chart.js` (503 lines, ported from `docs/design-explorations/plot.js`) and one
  `<script>` line. **C7 closed the milestone: modal bin `90.0-91.2 GeV`, centre 90.6 GeV, read off the
  drawn figure in the running app** — reproduced in three independent worktrees.
  **C2 deviated by my ruling** — data enters by F-007's `fce:result`/`data-result` contract, never a
  second fetch. **C3 is honest:** `weightsSquared` is `null`, so no MC stat band is drawn and the
  omission is named with the field; only the systematics hatch and pseudo-data sqrt(N) bars appear.
  Static legend ported, `renderCutflowFigure` left behind.
  **The count fell 698 → 697 / 75 → 74 and that was a strengthening, checked not assumed:** two reveal
  tests merged into one asserting `band_normal == band_reduced` directly, which goes red under a 1px
  offset applied to the reduced-motion page only — a mutation the replaced pair could not catch.
  **Contract for D-016 is verbatim in PR #47's body**, re-enumerated against the emitted classes by the
  reviewer line by line.
- **F-007** — serialise, submit, stream, show progress — #46, `1fdb8e6`, **2 cycles + 1 re-spec (mine) + 1
  pre-merge pass**, clean gate (`findings=3, scope=pass, verdict=approve`). checks=15. Suite floor → **691**;
  `tests/e2e/` 64 → **68** nodeids. Ships `static/js/run.js` and the `#run-control`/`#results` markup —
  **the first time a student can run an analysis from the browser.** No CSS by design; D-016 styles it.
  **Contract for F-008 and D-016 is verbatim in PR #46's body** and was diffed element-by-element against
  the shipped markup by the reviewer.
  **The cycle-1 lesson, and it is mine:** both criteria that gated the properties that matter were
  instruments that could not observe them. C2's "drag, resubmit, expect a cache hit" tests a *server*
  property — randomising `x`/`y` per submission kept it green; C4 shipped with no check and stayed green
  when **both** SSE status writes were deleted. C12/C13 replace them and are red under exactly those
  mutations. §2's blind-instrument failure, twice in one dispatch.
  **And the instrument beat the app once more:** cycle 1 reported the real page never showing live
  progress. It does — a `MutationObserver` on the live server recorded
  `Locating datasets… → Reading events… → … 90% → … 100% → Done → Run complete.`; cycle 1's 20ms polling
  was too coarse to see it. I had ruled the property stood and must not be restated to match the
  instrument, which is the only reason it was not weakened.
  **`disabled` is never used on `#run-button`** — it drops keyboard focus to `<body>` mid-run.
  `aria-disabled` plus a re-entry guard instead, so **D-016 must style the busy state itself** (F13).
  F11 backlogged (`#results` 26px wide at 1440, D-016's).
- **F-009** — opened node clamped by its measured size — #42, `ad36dd9`, 1 cycle, clean gate (`findings=4, verdict=approve`;
  F1-F4 cleanups backlogged, ~−16 lines). checks=5. Suite floor → **681**. `moveNodeTo` clamps by live box; `growNode`
  re-clamps. Two tests, each mutation-verified against its own path. Closes D-015's C12 vertical half.
- **F-003** — the four woff2 proven served — #41, `1f9d344`, 1 cycle, clean gate (`findings=2, verdict=approve`;
  F1/F2 readability nits backlogged). checks=5. Suite floor → **680**. Roman + mono 500 are painted by the page;
  italic + mono 400 are forced with `document.fonts.load` because nothing renders them yet. Red on 404, abort, no forcing.
- **F-010** — mission panel shows M-1, not M-3 — #40, `57a42a5`, 1 cycle, clean gate (`findings=2, verdict=approve`).
  checks=5. Suite floor → **679**. Pagers `disabled`, classes kept. F1 (two tests where one asked) backlogged;
  F2 (disabled pagers look live) → **D-017**. Reviewer also saw the right panel cut off at 768 → D-017 C2.
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
- **F-006** — the merged `Observable` node interior — #38, `eb4f420`, 2 cycles + 1 PR-only
  dispatch, clean gate (`findings=3, verdict=approve`). Suite floor → **671**; `tests/e2e/` 47 → **54**.
  Native `<details>` grow-in-place, four-radio mode toggle, `config: {mode}` in `data-graph`, focus
  kept on the summary across bring-to-front. Per-mode fields **deleted** (they reached no config) —
  wiring them is future work. **C4 moved to D-015.** F6 (bring-to-front reorders Tab) → D-015 note;
  F7/F8 backlogged.
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

_none — F-003 closed; its deferred entry is in the archive._
