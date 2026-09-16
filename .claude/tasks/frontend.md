# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

### F-007 — Serialise, submit, stream, show progress
- **Branch / PR:** `task/f-007-run-submit-stream` — #46
- **Status:** coder done, all 11 claimed met; **gate + review held until PR #45's review finishes** —
  B-024's central criterion is measured on the shared `~/.fce`, which any concurrent suite disturbs.
- **Contract shipped, verbatim in PR #46's body (C10), consumed read-only by D-016 and F-008:**
  `#run-control`/`#run-button`, and `#results` carrying `#results-status` (aria-live, phase + percent),
  `#results-progress` (native `<progress max=100>`, hidden until the first frame), `#results-note`
  (aria-live, **no `role="alert"`**, no banner class — brief §2), `#results-chart`.
  **F-008 renders into `#results-chart`**, reading its `data-result` attribute or the bubbling
  `fce:result` CustomEvent it dispatches on `done`.
- **`x`/`y` never leave the client** — `run.js` rebuilds each node as `{id, kind, config}`, so a
  drag-then-resubmit is a cache hit. That is stronger than the ride-along the dispatch allowed for.
- **Environment note:** the coder added Chromium r1243 to the shared `~/.cache/ms-playwright`
  (additive, r1234 untouched) — an unpinned `playwright` in a fresh worktree venv resolved higher.
- **Depends on:** F-005, F-006, B-020, B-021, B-022, B-023 (all merged); go-ahead given 2026-09-11. Wave 5.
- **C1/C2 deviate from the plan text by my ruling, 2026-09-16.** `docs/plan-m3-vertical-slice.md:720-727`
  asks for `{nodes, edges, ui{}}` with layout confined to `ui`. Enumerated by `scout`: nothing reads a
  `ui` key — `build_run_config` reads only `nodes`/`edges` (`graph.py:349-350`), `docs/api.md:34-50`
  documents only those, and `graph.js:93-101` already rides `x`/`y` on each node where `_parse_nodes`
  ignores them. The `ui` wrapper would need a backend change for no behavioural gain. C1/C2 state the
  same property against what shipped; C2 proves it by drag-then-resubmit landing a cache hit.
- **C10 is the contract clause:** the PR body must carry the results-region markup verbatim, the way
  F-004's PR #32 did. **D-016 and F-008 consume it read-only.**

## Ready

**Wave 5 go-ahead given by the user, 2026-09-11.** F-007 dispatched 2026-09-16 → F-008 → D-016, serialised on the page.

## Blocked
### F-008 — The interactive SVG histogram
- **Depends on:** B-019, F-007. Ports `plot.js`; legend toggle, PNG export, cutflow and Z gauge
  are explicitly out of scope by the user's 2026-09-07 ruling. Wave 5.

## Done

Full entries are in [`archive/frontend.md`](archive/frontend.md). Read it only when a task's
history is actually in question.

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
