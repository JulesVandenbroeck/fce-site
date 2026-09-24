# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

### F-023 — browser sends the real mission id (stacked on B-032)
- **Scope:** `templates/shell.html` (`:82` `data-mission-id`)
- **Accept:** id is `M-1`; e2e suite re-run on B-032 + this; remaining reds reported, not fixed
- **Branch / PR:** `task/f-023-mission-id` → base `task/b-032-run-missions`
- **Status:** dispatched (cycle 1)

## Ready

_none — the canvas port (N12/N13/N14) is decomposed but not dispatched; see `design.md`
`## Decisions in force` §8-9 and the note below._

## Blocked

M5 plan: [`docs/plan-m5-missions.md`](../../docs/plan-m5-missions.md).
- **F-020** — join form (class code + nickname) — blocked on B-034.
- **F-021** — mission panel/pager from server data; locked kinds/modes inert "opens in M-n" — blocked on B-034; scout Q3 first.
- **F-022** — objective outcome after a run (margin note / completion + unlock) — blocked on F-021.

## Done

Full entries are in [`archive/frontend.md`](archive/frontend.md). Read it only when a task's
history is actually in question.

- **F-019** — trimmed duplicated focus-timing comment in `test_graph.py` (N32) — #71, `4a9a198`, 1 cycle, clean gate (`findings=0, scope=pass, verdict=approve`). Floor 739 unchanged.
- **F-018** — frontend backlog sweep (N6, N11, N20, N21, N22, N24, N31) — #69, `427a0f2`, 1 cycle, clean gate (`findings=1, scope=pass, verdict=approve`). Suite floor **738** (−1 folded loop, +1 pointercancel check). N24 de-flaked by waiting for summary focus (20/20). `wirePan` tears down on `lostpointercapture`, mutation-proven. F1 (7-line comment → 1) → N32.
- **F-016** — canvas pan (left-drag + keyboard) and zoom 50-200% with one Fit affordance — #67, `1075a03`, **1 cycle across 2 handoffs + 1 stacked design task (D-023 #64)**, clean gate (`findings=2, scope=pass, verdict=approve`). checks=11. Suite floor **737**. Closes N13 and N23.
  The `scrollLeft` no-op was two things: no scroll range (fixed by D-022) and a test that dragged toward the clamped origin. Then the zoom buttons had no CSS and sat under the palette, which D-023 fixed. C5 and C11 are mutation-proven. F1 (N24 flake, maybe now timing-sensitive) appended to N24. F2 (`wirePan` has no `pointercancel` handling) → N31. The `.canvas-wrap::after` spacer is now redundant → D-024.
- **F-017** — `d0` labelled "impact parameter significance (d0)", no unit, range preset [-50, 50] (99.09% of fixture values) — #66, `8f89578`, 1 cycle, clean gate (`findings=0, scope=pass, verdict=approve`). User ruling 2026-09-23. Suite floor **730**. Closes N1.
- **F-015** — full-bleed canvas, overlay panels, results drawer at the bottom edge — #62, `dc2337f`, **1 cycle + 1 re-spec (mine)**, clean gate (`findings=5, scope=pass, verdict=approve`). checks=7. Suite floor **726** (721 + 5).
  **Carries backlog N12 and N14.** No CSS by design — D-022 styles it. `#run-control`/`#results` moved out of `#canvas-region` into `<section id="drawer">`;
  the drawer is a **third `wireToggle` call**, not a second mechanism (`shell.js:31` is the only definition, called three times — verified by the reviewer).
  `.shell` → `.frame`; `graph.js`'s `CANVAS_W/CANVAS_H` and the `704x512` viewBox deliberately untouched, because N13 is **F-016**.
  **The re-spec was mine:** C6 demanded no regression while my file scope forbade editing the one file the restructure necessarily breaks. Scope amended
  to add `tests/e2e/test_graph.py`, checks 6 → 7. The coder stopped at the boundary and reported rather than routing around it.
  **C7 kept the instrument strong rather than buying green:** `scroll_into_view_if_needed()` plus a fresh `bounding_box()` at each use, the raw
  `page.mouse` path untouched. The real cause was not the one I guessed — unstyled, the palette sits **below** the canvas in flow, so a `.click()`
  elsewhere in the same test scrolls the page and staled a box captured earlier. Reviewer confirmed neither test was weakened, and reproduced the
  `onMove`-stub mutation independently: `(16, 16) != (16, 16)`.
  **The reviewer mutated five separate things in a disposable copy outside the repo** — C1, C2, C3, C7 and `graph.js:229`'s re-clamp — every one red, every one restored.
  F1, F2, F3, F5 backlogged as **N20-N23**; **F3 (nested region landmarks) is carried into F-016's dispatch**, not merely filed, because it is an accessibility regression this PR introduced.
  **F4 is not this PR's and is now N24:** `test_observable_mode_is_config_not_identity` is flaky on `main` too (~1 in 10 file-level runs).
  **History:** [`archive/frontend.md`](archive/frontend.md)
- **F-014** — a re-collapsed node returns to its collapsed height — #61, `06e4108`, **1 cycle + 1 gate return that was mine, not the coder's**, clean gate (`findings=0, scope=pass, verdict=approve`). checks=3. Suite floor **721** (720 + 1).
  **Closes backlog N15.** One line of code plus a why-comment, in the single function all five `growNode(id)` call sites route through.
  **The root cause was not the obvious one, and scout's ground truth predicted that:** nothing sets an inline style, and `wireInteriorToggle` already
  calls the *same* `growNode` on open and close. `.node` is `height: 100%` of its `foreignObject` (`canvas.css:26-27`), so `growNode`'s
  `div.scrollHeight` read reported the div's own still-expanded box back rather than the shrunk interior's content height. The fix resets the
  `foreignObject` to its `NODE_H` floor *before* measuring, forcing the shorter interior to overflow it. A measurement bug, not a stale value.
  **The reviewer strengthened C2 beyond what the PR ran:** besides deleting the reset line (RED, no shrink at all), it mutated the measured height
  `+7` so the node shrinks but not all the way, and the equality assertion went red on its own (`assert 111.0 == 104.0`). The check fails both ways that matter.
  **My gate return was a false alarm and cost one round trip** — see the entry in `archive/frontend.md` and backlog **N19**. `adcb6e3` never moved.
  **History:** [`archive/frontend.md`](archive/frontend.md)
- **F-013** — backlog cleanup sweep, frontend — #57, `9c72521`, 2 cycles, clean gate (`findings=1, scope=pass, verdict=approve`).
  **Suite floor 729 → 728** (`test_mission_pager_has_nothing_to_page_to`, folded into its sibling and shown
  *stronger* by mutation, not merely shorter). `shell.js` 59 → 45 lines; `wireToggle` merged from two near-identical
  wirings. **Cycle 1's F1:** the sweep deleted `measuredSize`'s unreachable guard but left the twin `if (fo)` on the
  same lookup four lines below — the one outcome a task about deleting unreachable guards must not produce; cycle 2
  hoisted the lookup after verifying all three callers. F2 was mine (unpushed bookkeeping on the branch point).
  F4 (the expanded-state chevron is written twice, in template and JS, unguarded — `aria-hidden` decoration, no
  functional consequence) backlogged.
- **F-012** — Multiplicity and Histogram interiors, range presets — #53, `82ce11c`, 2 cycles, clean gate (`findings=0, scope=pass, verdict=approve`; c1 F1-F5 all fixed).
  Suite floor **718**. Default Histogram range 0-150 GeV **ratified by the user 2026-09-17**; mission-1 modal bin 90.0-93.0 GeV. New class for D-018: `.mult-group` (fieldset per object kind). Blank count -> `null` -> server 400.
- **F-011** — Observable and Selection interiors + `expr.js` (**CONTRACT TASK**) — #50, `e5a8bff`, 2 cycles + 1 re-spec (mine: scope omitted `test_graph.py`),
  clean gate (`findings=0, scope=pass, verdict=approve`). Suite floor **717** (715 + 2) on the merge, reproduced by me pre-merge.
  **Vocabulary table verbatim in PR #50's body — F-012 and D-018 consume it read-only.** graph.js holds no expression strings.
  Classes for D-018: `.obs-panel`, `.obs-panel__opt`, `.selection-rows`, `.selection-row`, `.selection-add`, `.selection-remove`.
  Server-side limit noted by review: `ALLOWED_ATTRS` is not per-object. My bookkeeping `020261b` rode the branch (unpushed main).
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
