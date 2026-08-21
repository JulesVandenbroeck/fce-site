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
- **Status:** **cycle-3 FIXES dispatched 2026-08-21 (second attempt — the first died on the
  session limit).** Reconciled against git before re-dispatching: branch `d008-cycle3fix-work`
  head is still `6954e65`, equal to PR #7's head, so the crashed agent committed nothing — **but
  it left ~135 insertions uncommitted** across all three in-scope files in its worktree
  `.claude/worktrees/agent-a655b1189e1e79a9f`. That work is intact and the re-dispatch's first
  instruction is to commit it as WIP before touching anything, with `git checkout --` and
  `git reset --hard` named as forbidden. This is the §6 hazard that has already destroyed
  uncommitted work once on this project.
  Earlier: cycle 3 delivered `6954e65`, §5.1 gate PASSED. Crash recovery worked exactly as
  instructed — `5079355` is the WIP-commit-first, `6954e65` the completion. Nothing lost.
- **THE RE-SPECIFICATION WORKED. Both floors hold simultaneously for the first time.** Verified
  by me in a clean worktree, not taken from the PR body:

  | | min CVD ΔE | worst normal-vision ΔE |
  |---|---|---|
  | D-004 c3 | 3.20 | 12.81 |
  | D-008 c1 | 2.62 | 13.11 |
  | D-008 c2 | **7.18** | **7.44** ← the regression |
  | **D-008 c3** | **5.95** | **14.30** |

  Normal-vision separation is now above **every** previous palette, including the 12.81 nobody
  had complained about. CVD margin came down 7.18 → 5.95 to buy it, still well above the 4.0
  floor. Other gates: chroma 58.8 ≤ 62, darkness 0.0656 ≥ 0.06, white-on-fill 4.94 ≥ 4.5 (up
  from c1's 4.64), node-vs-reserved 13.44. Diagnostic min hue gap **23.2°**, against the 17.4°
  that made two node kinds the same dark green in cycle 2.
  Anti-substitution commands hold: `grep 'context only'` empty, `grep -c 'section('` = **29**
  (required > 28), `verify.py --all` 469 lines / **0 FAIL** / exit 0, all 8 hexes reproduced
  exactly by `--report`. The sweep table reproduces **digit for digit**.
- **Cycle-3 review: 3 required, 3 suggested-major, 2 suggested-minor. NOT clean; cycle 3
  (the real one) dispatched. Cycle count is now 3 of 3 — §5.7 limit.** All three required are
  the same class: *a stated claim the code does not enforce* — the defect this task exists to
  remove — and **all three were introduced by this cycle's own work**, so §5.4 clause 3 applies
  and it is a cycle, not another re-specification.
  (1) `cam02ucs_deltaE`'s docstring asserts clamping is conservative "so no verdict is made
  more permissive"; 4000 random pairs give **107 reading more separated clamped**, worst excess
  **+2.32 ΔE**. Palette unaffected (≤ +0.005 on the committed 132). (2) a comment names
  `NORMAL_VISION_DELTA_E_FLOOR`, which does not exist. (3) both files claim the two floor
  constants are "cross-checked"; **lowering either alone is undetected by every command in the
  PR body.**
- **THE FINDING I COULD NOT HAVE MADE, and it is the important one.** `--node-data` `#8d5548`
  sits at CAM02-UCS hue **33.8°**; `--vermillion` sits at **30.2°**. A 3.6° gap makes the Data
  node a desaturated vermillion, which design manual §2 reserves so "red means the physics did
  something" — visible at 1440 px, where the Data node body and the vermillion `LOGGED` stamp
  read as one hue family. `--node-obs-custom` brackets it from the other side at 3.2°.
  **The ΔE gate passes it comfortably at 17.3, so ΔE alone is blind to it** — and the hue
  diagnostic at `verify.py:3294-3304` is computed *only among the eight fills*, never against
  `RESERVED_COLOR_TOKENS`. This is cycle 1's vermillion finding reappearing in **normal vision**
  because the new normal-vision floor pushed hues around, and no gate existed to see it.
  Cycle 3 adds the missing gate and delegates the nudge-or-overrule judgement to the coder,
  with an explicit instruction not to re-run the search.
- **USER RULING 2026-08-21: ship the committed palette; do not extend the T-ladder.** So the
  reviewer's suggested-major 1 is discharged by *accurate wording*, not by more search — the
  files must say plainly that 14 is a floor chosen at the top of a ladder rather than a
  discovered ceiling, and that the palette clears it by 0.30.
- **My remaining defect, recorded because the ruling settles it rather than erases it.**
  The T-ladder I specified topped out at 14, and **the selected row is not binding**: it
  achieves min-normal **18.382** against its own T=14 constraint. So "largest feasible T" means
  "top rung I wrote down", not "the ceiling". Worse, the full-budget re-run of that row spends
  its extra budget pushing CVD up and lets normal fall back toward the constraint —
  reduced-budget T=14 row was **5.091 CVD / 18.382 normal**, the committed full-budget palette
  is **5.948 CVD / 14.304 normal**. **Neither dominates**, so this is a position on the
  frontier rather than a free improvement, which is why it is the user's call and not mine
  (§7). The non-monotonic "infeasible" verdicts on rows 8–13.11 are a reduced-budget
  convergence artifact — those T values *are* feasible, since the T=14 solution satisfies them
  — and the coder disclosed this rather than smoothing it.
- **What the re-specification changes, and the one thing scout caught before I shipped it
  wrong.** The obvious repair — fold normal vision in as a fourth condition inside the existing
  `min` — **reproduces the bug.** `objective(x)` at `palette_search.py:346` returns
  `-de_worst.min() + penalty` (`:380`) over `CVD_TYPES` (`:362`). The CVD pairs are the harder
  ones, so they bind the minimum and normal vision is pulled up only to the CVD ceiling and no
  further. That is exactly cycle 2's result: normal 7.44 sitting just above CVD 7.18. A single
  `min` over four conditions is not a cumulative criterion, it is one criterion with a wider
  index. **Normal vision gets its own floor, not a seat in the same min.**
- **The floor is discovered by command, not asserted by me** (§2, feasibility before
  imposition). Nobody knows whether a high normal-vision floor and the CVD ΔE 4.0 floor are
  jointly reachable: cycle 1 hit normal 13.11 / CVD 2.62, cycle 2 hit normal 7.44 / CVD 7.18,
  neither hit both. So `palette_search.py --sweep` maximises min-CVD ΔE over the 132 CVD
  pair×condition values subject to min-normal-vision node-node ΔE ≥ T, for
  T ∈ {0, 8, 10, 12, 13.11, 14}; T=0 is the control that reproduces cycle 2. **Selection rule:
  the largest T whose achieved min-CVD ΔE ≥ 4.0.** Deterministic, so the reviewer can
  re-derive which row should have been committed. **A documented infeasibility result is a
  successful outcome and will not be sent back.**
- **Anti-substitution is now two commands, not a sentence.** `grep -n 'context only'` must
  return nothing — cycle 2 did not delete its predecessor's check, it relabelled
  `verify.py:2949` "normal vision (context only, not checked here)", which is the same thing
  wearing a hat, one entry below where I had already written that lesson down. And
  `grep -c 'section(' verify.py` must exceed **28**.
- **Review:** cycle 1 — 2 required, 2 suggested-major, 3 suggested-minor. Cycle 2 — 1
  required, 1 suggested-major, 3 suggested-minor. Suggested-minor (c), the stale
  `check_beamline_pairwise_luminance` name, is **backlogged** and explicitly excluded from
  cycle 3; (a) and (b) fold in as criterion 6/9, both being "a stated constraint is not
  actually checked" — the same class as the required finding.
- **`verify.py` check count: 29 `section(` and 44 `line(` at head `6954e65`**, both
  enumerated by the cycle-3 reviewer, not estimated. (Was 28 at `9480cac`, enumerated by scout.)
  The reviews' "N/N sections PASS" counts sections that *ran*, which is the smaller number; the
  grep is the durable one. **A fall below 29 / 44 is `Required` (§5.3).** The cycle-3-fix dispatch
  requires `section(` ≥ **31**, because it adds two gates: the clamping-bound gate (required 1)
  and the fill-vs-reserved hue gate (suggested-major 2).
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
