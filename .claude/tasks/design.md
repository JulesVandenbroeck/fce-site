# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

### D-005 — Node-graph style B: Bench
- **Scope:** `docs/design-explorations/` — create `bench.{html,css,js}`; append a `--bench`
  section to `verify.py`. `tokens.css` is **read-only** here.
- **Accept:** as D-004, with the model and gestures inverted — Bench persists `{x, y}` per
  node on a free canvas, **drag-to-connect accepted, click-to-connect refused**. Same
  64/13/51 enumeration, same inventory denominators, same three-width sweep.
- **Depends on:** ~~D-004~~ (merged `bac2f62`) and ~~D-008~~ — **UNBLOCKED 2026-08-21**, D-008
  merged `2d0de23` on a clean gate. `tokens.css`'s eight `--node-*` fills are now final and
  read-only here; build against them. Note `--node-data` is `#966746`, **not** D-004's `#8d5548`
  — anything harvested from the D-004 era is stale.
- **Branch / PR:** `task/d-005-bench` — dispatched 2026-08-31, worktree isolation. PR not yet opened.
- **Status:** cycle 1 in flight with `design-coder`.


## Ready

### D-006 — Node-graph style C: Board
- **Scope:** `docs/design-explorations/` — create `board.{html,css,js}`; append a `--board`
  section to `verify.py`. `tokens.css` read-only.
- **Accept:** Board persists `{column, slotIndex}` in typed columns and accepts **both**
  gestures plus keyboard connection. Same 64/13/51 enumeration and sweeps. The plot lives
  *inside* the graph as the terminal node, so it must budget for D-003's fixed intrinsic
  **650×460** figure and be shown doing so at 768.
- **Depends on:** ~~D-004~~ (merged `bac2f62`) and ~~D-008~~ — **UNBLOCKED 2026-08-21**, D-008
  merged `2d0de23`. Same note as D-005: the fills are final, and `--node-data` is `#966746`.

**Run D-005 then D-006, serially — never in parallel.** Both append a new section to
`verify.py`; two coders in flight would collide on it, and the worktree rule protects the
branch, not the merge.


## Blocked

### D-007 — Comparison index and the recommendation
- **Scope:** `docs/design-explorations/index.html`, `README.md`, plus a two-line superseded
  note at the top of `docs/wireframes/README.md`. No page files, no `tokens.css`, no
  `verify.py`.
- **Accept:** the index links all three styles and states, per style, what the graph
  persists and which gesture connects; the README states a recommendation with reasoning
  and names what each option gives up. **This is the checkpoint the user reads to choose.**
- **Depends on:** D-004, D-005, D-006.

#### Constraints all four node-graph tasks inherit

**Run D-005 and D-006 serially, never in parallel** — both append to `verify.py`, and the §3
worktree rule protects the branch, not the merge.

The one axis CSS cannot swap is **what the graph persists**, and it is what later lands in
`POST /api/run`: **A · Beamline** ordered edge list only; **B · Bench** `{x, y}`;
**C · Board** `{column, slotIndex}` — recommended, and the only one where the plot lives inside
the graph as the terminal node.

What D-003 hands all four:

- The figure is a **fixed intrinsic 650×460** CSS px. It does not reflow; budget for it.
- Harvest the **cycle-4** `--tab10-x2`/`--tab10-x3` values, not cycle 3's, which were wrong.
  `--ink-45` is 2.60:1 and not text-safe.
- Four verification rules earned over seven cycles: name the verification *method* in the
  criterion; mutation-test every new assertion; list deviations, never count them; check parity
  by rendering the reference, never by reading the code.
- Two markup patterns **not** to copy: `role="tablist"` with no arrow-key handling, and per-item
  tab stops (D-003 has 40 individually focusable bins).

Why this is four tasks and not one, and the fuller case for each style:
[`archive/design.md`](archive/design.md).

### D-002 — Design token foundation
- **Scope:** `src/fce_web/static/css/tokens.css`, `src/fce_web/static/fonts/`
- **Accept:** C1 every colour, spacing, type-scale, radius and timing value is a custom property;
  C2 the palette committed with measured AA ratios documented in the file — measured against the
  real paper token, and for labels sitting *on* saturated fills, not only on paper; C3 self-hosted
  woff2, no CDN; C4 a serif and a mono that are explicitly not Inter/Roboto/system-ui/Space
  Grotesk. checks=4.
- **Depends on:** the user's choice among Beamline / Bench / Board, presented at the **D-007**
  checkpoint, with `docs/design-explorations/tokens.css` as its input rather than a blank page.
- **Owed forward:** the palette must now carry node-type hues, sample identity and lock state.
  `--ink-45` composites to 2.60:1 and fails AA for text — do not inherit it unstated. Take the
  **corrected** tab10 values (`#8c564b`/`#17becf`), not cycle 3's `#ff7f0e`/`#2ca02c`.
- **Branch / PR:** not yet opened
- **History:** [`archive/design.md`](archive/design.md)

## Done

One line per task. Full entries in [`archive/design.md`](archive/design.md). Every design task so
far has closed on an override or at the loop limit except D-008; if you are about to write a
design criterion, the archive is where that pattern is documented.

- **D-008** — CVD-safe node palette + the checker claim — #7, `2d0de23`, 3 cycles + 1 re-spec,
  **first design task to close on a clean gate**. `verify.py` at 31 sections / 48 assertions.
- **D-004** — Beamline node graph, shared palette and checker — #6, `bac2f62`, 3 cycles,
  §5.7 limit; 2 open → **D-008**.
- **D-003** — interactive plot component at reference parity — #5, `99ec8f3`, 4 cycles, merged on
  the user's explicit override.
- **D-001** — wireframes: mission screen and recipe builder — #2, `b580729`, 4 cycles, 1 open;
  superseded by the 2026-08-16 node-graph pivot.

## Floors in force

- D-008's six simultaneous palette floors: min CVD ΔE **5.129** (≥4.0), normal-vision node-node
  **14.170** (≥14.0), node-vs-reserved **13.442** (≥4.0), white-on-fill **4.595:1** (≥4.5),
  fill-vs-reserved hue gap **14.1°** (≥12.0°), clamping excess **+0.0051** (≤0.01).
- `verify.py`: **31** sections / **48** assertions. A fall in either count is `Required`.