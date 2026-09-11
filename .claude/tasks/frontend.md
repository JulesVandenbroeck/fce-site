# Front-end tasks

Owned by `frontend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `F-nnn`, allocated in order and never reused.

---

## In progress

_none._

## Ready

Order: F-010, then F-009, then F-003 (serialised — same page). F-007 waits for the user's wave-5 go-ahead.

### F-010 — Mission panel shows mission 3's text instead of mission 1's
- **Found by the user, 2026-09-11** (PDF of `main` at `8f094a6`): the panel reads "M-3 · The Unknown — A signal
  sample is hiding in the data. Find cuts that expose it and run a fit." — carried over from the D-010
  exploration's demo copy. Mission 3 is **blocked** (X4/X5 unidentified, shared §5: no mission-3 content), and
  M3 runs mission 1's dataset. Also claims a fit, which M3 does not build.
- **Scope:** `src/fce_web/templates/shell.html` (mission panel text only), `tests/e2e/test_shell.py`
- **Accept:** the panel shows **M-1 · First Light** with brief §3's M-1 objective in plain student English
  (`docs/design-brief.md:86-91`); no M-2/M-3 text anywhere in the rendered page; the pager does not offer
  missions that do not exist yet. Hardcoded is fine — mission loading is M5.
- **Depends on:** nothing — D-015 merged `0eded93`. Serialise with F-009.
- **Branch / PR:** `task/f-010-mission-one-text` — #40
- **Status:** in review (cycle 1) — head `cff7e54`, gate passed (679 / flake8 0). checks=5.

### F-009 — An opened node is re-clamped onto the canvas by its measured size
- **Scope:** `src/fce_web/static/js/graph.js`, `tests/e2e/test_graph.py`
- **Accept:** after `growNode()` resizes an opened node, it is moved so its measured box lies fully inside
  the canvas (vertical and horizontal); dragging an opened node clamps by its live size, not `NODE_W`/`NODE_H`.
  Carries D-015's C12 vertical half (PR #39 cycle-2 review F6). Proven in Playwright at the bottom edge.
- **Depends on:** D-015 — merged `0eded93`. Wave 3 fix, before F-007.

### F-003 — Prove the four woff2 are actually served
- **Depends on:** D-015 — merged `0eded93`. Full entry under `## Deferred`.


## Blocked

### F-007 — Serialise, submit, stream, show progress
- **Depends on:** F-005, F-006, B-020, B-021, B-022 (all merged) — **the user's wave-5 go-ahead**. Wave 5.
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
