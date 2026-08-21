# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

### D-008 — CVD-safe node palette, and the checker claim that certifies it
- **Scope:** `docs/design-explorations/tokens.css` (the eight `--node-*` fills),
  `docs/design-explorations/verify.py`, `docs/design-explorations/palette_search.py`,
  `docs/design-explorations/beamline.css` (the `.palette__add::before` swatch only).
- **Accept:** **cumulative — every floor below holds simultaneously, and cycle 3 adds to this
  list rather than replacing it (§5.3).** All 28 `--node-*` pairs clear a stated ΔE floor
  under Machado-simulated protanopia, deuteranopia and tritanopia *and* under normal vision;
  white-on-fill ≥ 4.5:1 under all three simulations; the three named picker swatches
  distinguishable at 9×9 px; `check_beamline_pairwise_luminance` measures what its docstring
  claims; every claim in the docstring checked by the code beneath it. Floors stated with the
  feasibility arithmetic done **before** they are imposed.
- **Depends on:** D-004 (done, `bac2f62`). **Must run before D-005 and D-006** — both consume
  `tokens.css` read-only, so this is a contract task (§2), not a styling task.
- **Branch / PR:** `task/d-008-cvd-palette` — #7
- **Status:** cycle 2 complete. **Cycle 3 is a re-specification, not a cycle** (§5.4): the
  criterion has been non-cumulative three times running, which is a defect in my brief rather
  than in the coder's work, so it does not count against the §5.7 limit.
- **Review:** cycle 1 — 2 required, 2 suggested-major, 3 suggested-minor. Cycle 2 — 1
  required, 1 suggested-major, 3 suggested-minor. `verify.py` section count: **26** — a fall
  below this is `Required` (§5.3).
- **History:** [`archive/design.md` § Post-mortems](archive/design.md) — three cycles, three
  metrics, each replacing its predecessor. This entry is the origin of the cumulative-criteria
  rule and the worked example behind §2's criterion contract.

## Ready

_none_

## Blocked

### D-005 — Node-graph style B: Bench
- **Scope:** `docs/design-explorations/` — create `bench.{html,css,js}`; append a `--bench`
  section to `verify.py`. `tokens.css` is **read-only** here.
- **Accept:** as D-004, with the model and gestures inverted — Bench persists `{x, y}` per
  node on a free canvas, **drag-to-connect accepted, click-to-connect refused**. Same
  64/13/51 enumeration, same inventory denominators, same three-width sweep.
- **Depends on:** D-004 (**done**, merged `bac2f62`) and **D-008** — the hues and the checker
  harness come from D-004, but D-004 merged with its palette still failing under protanopia and
  deuteranopia, and `tokens.css` is read-only here. D-008 must land first or Bench is built on
  fills that are about to move.

### D-006 — Node-graph style C: Board
- **Scope:** `docs/design-explorations/` — create `board.{html,css,js}`; append a `--board`
  section to `verify.py`. `tokens.css` read-only.
- **Accept:** Board persists `{column, slotIndex}` in typed columns and accepts **both**
  gestures plus keyboard connection. Same 64/13/51 enumeration and sweeps. The plot lives
  *inside* the graph as the terminal node, so it must budget for D-003's fixed intrinsic
  **650×460** figure and be shown doing so at 768.
- **Depends on:** D-004 (**done**, merged `bac2f62`) and **D-008**, for the same reason as
  D-005 — `tokens.css` is read-only here and D-008 changes it.

### D-007 — Comparison index and the recommendation
- **Scope:** `docs/design-explorations/index.html`, `README.md`, plus a two-line superseded
  note at the top of `docs/wireframes/README.md`. No page files, no `tokens.css`, no
  `verify.py`.
- **Accept:** the index links all three styles and states, per style, what the graph
  persists and which gesture connects; the README states a recommendation with reasoning
  and names what each option gives up. **This is the checkpoint the user reads to choose.**
- **Depends on:** D-004, D-005, D-006.

#### Why this is four tasks and not one
The single-task version was 12 files and three interactive prototypes — well past the
orchestrator manual's own splitting test (§2, "more than about three files, suspect it is
really two tasks"). D-003 took four cycles at half the size, and the first D-004 attempt
never got far enough to show the big shape works. Split costs an extra PR or two and buys
much tighter review loops. `tokens.css` and `verify.py` are extended by D-004 and read-only
or append-only thereafter, so the shared files have exactly one author.

**Run these serially, not in parallel.** D-005 and D-006 both append to `verify.py`; two
coders in flight would collide on it, and the manual's §3 worktree rule only protects the
branch, not the merge.

#### The three, pushed apart on what the graph persists
The one axis CSS cannot swap, and the thing that later lands in `POST /api/run`:

- **A · Beamline** — auto-laid rail, ordered edge list only, click-to-connect, colour on
  node chrome. Best 768 story; gives up all arrangement agency.
- **B · Bench** — free canvas, `{x, y}`, drag-to-connect, colour on the wires. Its real
  cost is not the drag — the plot inspector always occludes the graph, so cut and
  consequence are never co-visible. Framed as the *sandbox-mode candidate*.
- **C · Board** — typed columns with slots, `{column, slotIndex}`, both gestures plus
  keyboard, colour on the columns. **Recommended:** the only one where the shape of the
  page changes per mission (columns appear as missions unlock) and the only one where the
  plot lives inside the graph as the terminal node.

#### What D-003 hands all four, and it is not just a file to import
- The figure is a **fixed intrinsic 650×460** CSS px (widened from 480 when the legend moved
  outside the axes). Every layout must budget for that; it does not reflow.
- `tokens.css` is the input to D-002 — **harvest the cycle-4 `--tab10-x2`/`--tab10-x3`
  values, not cycle 3's, which were wrong.** `--ink-45` is 2.60:1 and not text-safe.
- Four verification rules earned across D-001's and D-003's seven cycles: name the
  verification *method* in the criterion; mutation-test every new assertion; list
  deviations, never count them; and check parity by rendering the reference, never by
  reading the code. `verify.py` now carries a lint for the third.
- Two markup patterns **not** to copy: the `role="tablist"` with no arrow-key handling, and
  per-item tab stops (D-003 has 40 individually focusable bins).


### D-002 — Design token foundation
- **Scope:** `src/fce_web/static/css/tokens.css`, `src/fce_web/static/fonts/`
- **Accept:** every colour, spacing, type-scale, radius, and timing value defined as a
  custom property; the palette committed with measured AA contrast ratios documented in the
  file; self-hosted woff2 fonts, no CDN; a chosen serif and mono that are explicitly not
  Inter/Roboto/system-ui/Space Grotesk
- **Depends on:** ~~D-001 and the user's D-001 layout decision~~ — **blocker changed
  2026-08-16.** Now blocked on the user's choice among Beamline / Bench / Board — presented
  at the **D-007** checkpoint (2026-08-18: the D-004 checkpoint moved there when D-004 was
  split into D-004/005/006/007), with `docs/design-explorations/tokens.css` as its input
  rather than a blank page. Left pointing at the old blocker it would read as waiting on
  something extinct.
- **New scope pressure from the pivot:** the palette must now carry node-type hues, sample
  identity, and lock state — not just paper, ink and one accent. AA must be measured for
  labels sitting *on* saturated fills, not only on paper.
- **Owed from D-001:** the wireframe contrast ratios were measured against wireframe white,
  because no paper colour exists yet. AA must be re-measured against the real paper token.
- **Owed from D-003:** `--ink-45` composites to 2.60:1 against paper and fails AA if ever
  used for text; it is currently unused. Do not inherit it unstated. And take the **corrected**
  tab10 values — cycle 3 shipped `#ff7f0e`/`#2ca02c`, which are `tab10(0),(1),(2)` unresampled
  and wrong; cycle 4 corrected them to `#8c564b`/`#17becf`.
- **Branch / PR:** not yet opened

## Done

Full entries — scope, criteria, and the cycle-by-cycle review record — are in
[`archive/design.md`](archive/design.md). Read it only when a task's history is actually in
question. Every design task so far has closed on an override or at the loop limit; if you are
about to write a design criterion, the archive is where that pattern is documented.

- **D-004** — Beamline node graph, shared node palette and checker — `task/d-004-node-graphs` #6,
  merged `bac2f62` (3 cycles, **§5 loop limit; 2 suggested-major still open → became D-008**)
- **D-003** — Interactive plot component at reference parity — `task/d-003-plot-component` #5,
  merged `99ec8f3` (4 cycles, 3 reviews, merged on the user's explicit override)
- **D-001** — Wireframe exploration: mission screen and recipe builder —
  `task/d-001-wireframes-clean` #2, merged `b580729` (4 cycles, **1 required still open**;
  superseded by the 2026-08-16 node-graph pivot)
