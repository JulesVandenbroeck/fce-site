# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## Decisions in force

**The M1 ruling, 2026-09-01.** The style is **Bench** — free canvas, drag-to-connect,
persisting `{id, x, y}` per node (`docs/design-explorations/bench.html:289-292`). D-007
recommended **Board**; the user overruled it. `docs/design-explorations/README.md` still says
"Recommended: Board" and is now a historical document — D-009 carries the note that says so.

The five comments the user attached to that ruling. These are what a dispatch is *given*, not
told about. All five are also written into `docs/design-brief.md` §2 and §4, which is the
version a coder reads.

1. **No `DataSource` in the palette.** V1 is 91 GeV only and each mission declares its dataset,
   so the node would have exactly one legal value. Future energies are future missions, not a
   chooser. → brief §4. **Its "seven kinds" is superseded by ruling 7 below — the palette is
   four.**
2. **Node interiors are re-thought from scratch.** The reference tool's fixed property grid is
   the one part of its UI not inherited. How a cut is expressed, how an observable is
   configured, must be designed for a 15–18-year-old. Legible beats complete. → **D-009**.
3. **The canvas is the logbook.** A completed mission's graph is frozen where it stands and
   **boxed**, labelled with the mission it closed; the next mission is built beside it on the
   same canvas. It accumulates, it does not clear. → **D-011**.
4. **A run is never silent *and never passive*.** The user's word was **interaction**: a
   progress bar is not enough, the student should still have something to *do* while the run
   is in flight, not only something to look at. Intended vehicle: event displays of the data
   as it is read.
   **Deferred to M6 on the user's ruling** — M3 ships the bar, deliberately. → **D-012**.
5. **Three regions, one permanent.** The graph canvas is always present; "Add a Node" is on the
   **left** and **collapses**; the mission panel is on the **right**, **expands**, and pages
   back to previous missions. → **D-010**.

**The interiors ruling, 2026-09-02.** Two decisions off the D-009 checkpoint.

6. **Inline grow, not the flyout inspector.** The node card itself grows in place when opened;
   there is no separate hinged panel. D-009's page recommended the flyout and the user overruled
   it, the same shape as the D-007/Bench overrule. **Consequence D-010 must design around, and it
   is the flyout's argument turned live:** a node now has **two** footprints, not one, so palette
   width is sized against the *opened* card; and on Bench's free canvas an opened node can overlap
   whatever is placed beneath it, which a canvas persisting free `{id, x, y}` has no mechanism to
   prevent. That overlap is now D-010's problem to solve, not a reason to have picked differently.

7. **One `Observable` node with a mode toggle, not four `Obs*` nodes.** The palette is **four**
   kinds: `Multiplicity`, `Selection`, `Observable`, `Histogram`. `ObsGlobal` / `ObsObject` /
   `ObsVectorSum` / `ObsCustom` become a mode *inside* the node. → brief §4, written 2026-09-02.
   **Why it is structurally free, enumerated not assumed** (`scout`, 2026-09-02): all four
   subtypes have identical legal connections — `Observable* → Histogram` and nothing else, which
   is why the brief's allowlist already writes them as one row. No legal graph changes.
   The mode is `config`, not identity: **the run payload resolves it to the engine subtype at
   submit**, exactly as `DataSource` is synthesised at submit. The student's graph and the
   engine's graph are now deliberately different in two places, not one. `ObsVectorSum` is the
   mission-2 unlock, so **an unlock must now read inside a node**, not as a new palette entry.

**Consequence for M3, recorded so it is not rediscovered:** the engine's allowlist still makes
`DataSource` the root of every chain. With it out of the palette, the **run payload synthesises
one at submit** from the mission's declared dataset. The student's graph and the engine's graph
are no longer the same object. The engine is not modified. Also in `backend.md`
`## Contracts in force`; `docs/api.md:29-34` still marks `POST /api/run` undefined.

---

## In progress

### D-021 — The canvas frame, corrected: horizontal pan, grid beyond the sheet, honest load state
- **Scope:** `docs/design-explorations/canvas-frame.{html,css}`, `docs/design-explorations/verify.py`.
  Touches nothing under `src/`.
- **Accept:** C1-C5 in the dispatch — left-drag pans in **both** axes; the page still has no
  horizontal scroll in all 27 probe layouts; the grid fills the canvas viewport at every zoom from
  50% to 200%; the whole pipeline is visible on load with both panels expanded; N17/N18 instrument
  cleanups.
- **Depends on:** D-020 (#59, merged `7043e76`).
- **Branch / PR:** `task/d-021-canvas-frame-pan` — #60
- **Status:** **in review (cycle 2)** — reviewer dispatched 2026-09-22 with PR #60 and nothing else.
  Branch head `85a397e`, pushed; PR body now carries a Cycle 2 section with C11/C12 and their
  PASS-then-RED mutation transcripts. **checks=12** (C1-C10 + C11 F2 probe + C12 F1 grid hit-test);
  probe floor **54 + 1** in a new registered section `canvas-frame-node-extent-monotonic`.
  Cycle 1: `findings=4, scope=fail, verdict=rework` —
  [review](https://github.com/JulesVandenbroeck/fce-site/pull/60#issuecomment-5781891877).
- **Free gate (§5.1) passed, re-run by me in a detached worktree at `85a397e`:** `--canvas-frame`
  both sections PASS, 54 probes plus C11, figures byte-identical to the PR body (`n5` extent
  7848.0x4228.7 inside 9048x5428.66); `--all` red set exactly `{board-lane-fill}`, exit 1.
- **Cycle 2 closed F1, F2, F4; F3 was already fixed.** The coder checked the `moveNode`/`applyZoom`
  recursion trap first and reports it does not hold — `moveNode` reads `sheet.w/h` but never calls
  `applyZoom`, and `applyZoom` never calls `moveNode`. Only `verify.py` changed this cycle (+207/-16);
  `canvas-frame.{html,css}` are unchanged from cycle 1, both mutation experiments reverted before commit.
- **Trap the successor checks first:** `moveNode` (`canvas-frame.html:439-440`) clamps `n.x` to
  `sheet.w - NODE_W`, and `applyZoom` now derives `sheet.w` from node extent. Confirm `moveNode`
  never calls `applyZoom` or the clamp and the sizing are mutually recursive. It does not on a read;
  it was not exercised.
- **Diagnosis (§5.4): a cycle, not a re-specification.** Nothing was dropped, and C6 shipped with a
  command and was met. F2 is against a property no criterion ever gated — clause 3. Same shape as
  B-006's unbounded `ast.Pow`: the dispatch named the root cause ("a node becomes unreachable") and
  the coder fixed the zoom-out direction and stopped one step short of zoom-in.
- **F1/F2 are the rework; F3/F4 are small.** F2: the sheet is recomputed from scratch on every zoom,
  so zooming *in* shrinks it and orphans a node placed at a lower zoom — the same defect reversed.
  F1: C8's guard compared the **SVG element's** rect to the viewport, which is unchanged when the
  paper rects inside it are not — the reviewer painted the backing over 1/3 of the sheet and the
  section still passed while 4 of 5 points hit-tested void.
  F3: the anchor rode the branch — I have copied it into the primary checkout and the branch removes
  it. F4: fixed 250ms sleep in `_canvas_frame_set_state` → `wait_for_selector`.
- **Two cycle-1 mutations did fire, and are worth keeping:** the pan-range assertion goes red with
  `canvas pan range 0x0` when the sheet is forced viewport-sized, and C10's state readback goes red
  with `a chevron did not reach the requested state`.
- **Unrequested deviations the user has not ruled on:** palette expanded width **368 -> 256**, the
  node chain re-laid out to a 212-unit pitch at (700,900), and the page now **opens in Fit rather
  than at 100%**. All three are the C9 mechanism and are argued in the PR body; reversible.
- **Carve-out note:** `.claude/handoff/d-021-design.anchor.md` rode the task branch (worktree
  isolation refused the primary-checkout path). Same shape as B-018's F6. Harmless here, but
  bookkeeping is not supposed to ride a task branch.
- **Carries:** the user's two findings from driving the page 2026-09-22, plus backlog **N16**
  (= PR #59 F1), **N17**, **N18**.
- **Note:** the two user findings and F1 are probably **one** root cause — a canvas surface with no
  horizontal scrollable overflow gives no horizontal pan *and* makes `n4`/`n5` unreachable. Fix at
  the root, not per symptom.
- **History:** [`archive/design.md`](archive/design.md)

## Ready

_none._

## Blocked

D-011/D-012 are unchanged below.
Plan: [`docs/plan-m3-vertical-slice.md`](../../docs/plan-m3-vertical-slice.md).

### D-011 — The completed-mission box on the canvas
- **Scope:** the frozen-and-boxed treatment for a completed mission's graph.
- **Accept:** on completion the graph is frozen in place and boxed, labelled with the mission it
  closed; the next mission is built beside it; the canvas accumulates and never clears. Reads as
  one gesture with §7's stamp and "the logbook fills in", not as a second competing idea.
- **Depends on:** **D-009**, and on **M5** — missions, completion and unlocking do not exist
  before then, so there is nothing to box.
- **Branch / PR:** not yet opened

### D-012 — A run that is never passive: event displays
- **Scope:** whatever shows the data moving while a run is in flight.
- **Accept:** during a run the student has something to watch or do beyond a progress bar;
  intended vehicle is event displays of the data as it is read.
- **Depends on:** **M6, by the user's ruling 2026-09-01.** M3 ships the phase label and bar and
  that is deliberate. Also needs a prior answer to a question nobody has asked yet: **what an
  event display can actually be drawn from in this data** — that investigation is part of this
  task, not a prerequisite raised elsewhere.
- **Branch / PR:** not yet opened

#### Constraints the node-graph tasks established

The one axis CSS cannot swap is **what the graph persists**, and it is what later lands in
`POST /api/run`. **Settled 2026-09-01: Bench, so it is `{id, x, y}` per node plus an edge list**
(`bench.html:289-292`), and the plot lives *outside* the graph in its own results region — the
in-graph terminal plot node was Board's, and Board was not chosen. The other two are recorded
in the archive as history: Beamline persisted an ordered edge list only, Board
`{column, slotIndex}`. What D-003 hands the survivor: the figure is a **fixed intrinsic 650×460** CSS px
and does not reflow; harvest the **cycle-4** `--tab10-x2`/`--tab10-x3` values; `--ink-45` is
2.60:1 and not text-safe. Fuller case for each style: [`archive/design.md`](archive/design.md).

## Done

One line per task. Full entries in [`archive/design.md`](archive/design.md).

- **D-020** — the canvas frame: full-bleed canvas, overlay panels, pan/zoom, bottom results drawer — #59, `7043e76`, 1 cycle, clean gate (`findings=3, scope=pass, verdict=approve`).
  **Checkpoint — awaiting the user's ruling on the recommendation.** Exploration only; nothing under `src/` touched.
  Ships `docs/design-explorations/canvas-frame.{html,css}` + one append-only `verify.py` section,
  `canvas-frame-no-h-scroll` (27 probes, 3 widths x 8 panel/drawer states + post-Run), **mutation-proven red**
  by the reviewer. Red set unchanged: `{board-lane-fill}` on `main` and on the branch, reproduced by me pre-merge.
  83 text runs 0 below AA; 19 focus stops all visible; 0 `style=` attributes; 0 console errors.
  **The four answers the user rules on:** zoom **50-200%**; pan **bounded** to an 1800x1200 sheet (which is what
  buys native keyboard pan and scrollbars); a left-drag **starting on a node still moves that node**, decided by
  where the drag begins rather than by a mode; **one** affordance, **Fit**, not a separate reset-to-100%.
  F1 (the page opens with 3 of 5 nodes under the panels at 1440 — the PR's "moved into the clear band" claim did
  not reproduce), F2 and F3 backlogged as N16-N18. **History:** [`archive/design.md`](archive/design.md).
- **D-019** — backlog cleanup sweep, design — #58, `34f5fc2`, 1 cycle + 1 re-spec (mine: C4 unsatisfiable), clean gate (`findings=1, scope=pass, verdict=approve`).
  Suite floor **729** unchanged — no test file touched. −42 lines, all comment prose plus one dead rule; nothing added.
  `chart.css` + `shell.css` only. **The deleted `.reveal-*{opacity:1;transform:none}` rule was proven a no-op by
  runtime re-injection**, not by reading: the reviewer intercepted the `chart.css` response, restored the rule, drove a
  real run and diffed computed styles in both motion modes — identical, and the instrument discriminates
  (`.reveal-band` reads `none` vs `matrix(...)` across modes, so it was not dead). Two N/A calls both independently
  confirmed: `--node-observable` is live in 4 files, and PR #55's F8 is in `tests/e2e/test_interior_style.py`,
  not this stylesheet. **F8 therefore stays open and is frontend's** — backlog N6.
- **D-018** — styled the four node interiors — #55, `ac97b42`, 2 cycles + 1 re-spec (mine: scope pointed at a check location D-016 never left), clean gate (`findings=1, scope=pass, verdict=approve`).
  Suite floor **729**. `observable.css` only; guard `tests/e2e/test_interior_style.py` (colour/no UA fallback, grown height, no h-scroll at 1440/1024/768). `.node__interior[open]` capped + scrollable, `flex-shrink: 0` load-bearing for `growNode`. Focus rings unguarded by test (C2 one-off). F8 docstring trim backlogged. **Closes M4 coding.**
- **D-016** — results region and chart styling — #48, `bb4f355`, 1 cycle, clean gate (`findings=4, scope=pass, verdict=approve`).
  checks=13. Suite floor **697** unchanged. `.canvas-region` now stacks (column) — a row left ~48px at 1440; F-007 F11 closed
  (`#results` 720px). Focus ring on `.bin-hit` uses `--ink` (graphite-blue fails 3:1 on two fills) — accepted deviation.
  F1 (C1 hit test blind to the row regression — reviewer mutation) + F2-F4 comment/dead-rule cleanups backlogged. **Closes M3 coding.**
- **D-017** — disabled mission pagers look disabled — #44, `8ab7964`, 1 cycle + 1 re-spec (mine: C2 asked to fix an
  unreproducible 768 overflow), clean gate (`findings=1, verdict=approve`; F4 comment trim backlogged). checks=5.
  `:disabled` → cursor default, `--ink-45` (WCAG 1.4.3 inactive exemption), no hover. No layout change.
- **D-015** — the shell, canvas and node stylesheets — #39, `0eded93`, **3 cycles + 1 re-spec + 1 reviewer handoff**,
  clean gate (`findings=1, verdict=approve`; F12 comment trim backlogged). checks=14. Suite floor **677** unchanged.
  Ships `shell.css`, `canvas.css`, `observable.css` + 3 `<link>`s and one `<span>` wrapper. First real use of
  `--font-body` → **releases F-003**. Cycle 3 fixed the user-found collapsed states (list still painted, both
  toggles unreachable) — C6 had gated only h-scroll. C12 vertical half → **F-009**. Releases F-009, F-010.
- **D-014** — closed D-010's open findings: the horizontal-scroll guard — #29, `63a6fd8`,
  2 cycles + 1 re-spec + 1 gate return, clean gate (`findings=5, verdict=approve`, all five
  folded in before merge). checks=6. Ships the real `shell-page-no-h-scroll` section the CSS and
  `verify.py` had cited into thin air, plus a new `shell-canvas-fade-affordance` guard.
  **`shell.html` was never touched** — the whole task landed in `shell.css` + `verify.py`.
  **The reviewer withdrew its own cycle-1 F2**: it had bundled the two `position: relative`
  declarations, and the coder's per-declaration split was correct. `.palette__toggle`'s was dead
  and is deleted; `.mission-panel__toggle`'s is load-bearing (41px of overflow at
  `panel=collapsed`, all three widths) and is kept with the measurement cited in place.
  **D-010's R3 and m7/m8/m9 are all closed; nothing carries forward.**
- **D-010** — the three-region page shell — #25, `a059f34`, 3 cycles, **merged on the user's
  ruling with R3 open** (PR #25 comment). checks=10 (C10 `shell-canvas-text-legible` added by
  cycle 3's M6 fix). Ships `docs/design-explorations/shell.html` + `shell.css`. The M1 ruling's
  comment 5 is now designed; comment 6's two-footprint consequence is solved by a fixed 704x512
  canvas surface with the region scrolling. R3 + m7/m8/m9 → **D-014**.
- **D-002** — design token foundation (**CONTRACT TASK**) — #24, `72d2950`, 3 cycles + 1 re-spec,
  clean gate `0R / 0M / 1m`. checks=10. Ships `src/fce_web/static/css/tokens.css` plus four
  self-hosted woff2 (EB Garamond roman + italic variable, Fira Mono 400/500) and their OFL
  files. **Releases D-010 and F-002.** m6 backlogged; m5 backlogged (the exploration
  `tokens.css` copy diverged).

- **D-013** — the merged `Observable` node interior, inline grow — #23, `309c409`, 2 cycles +
  1 re-spec, clean gate `0R / 0M / 1m`. checks=10. **Hands D-010 its input: the opened node is
  328.0 x 300.0px** (`ObsVectorSum`, tallest of the four modes; ObsCustom 301.5, ObsObject 290.5,
  ObsGlobal 237.0), collapsed 80.5px, measured on `.inode` and now under an assertion that goes
  red if the selector regresses to the `<figure>`. m4 (my dispatch formatting) and m7 (the
  footprint gate is one-sided) backlogged.
- **D-009** — node interiors: flyout inspector vs inline grow (**M1 checkpoint, awaiting the
  user's ruling**) — #22, `948e6ec`, 2 cycles, clean gate `0R / 0M / 1m`. checks=10. Both
  Required and M1 were against the *instrument*, not the design: three checks that structurally
  could not fail (unlabelled controls, `tabindex="-1"`, a zero-height collapsed exemplar all
  certified GREEN). `interiors.html`/`interiors.css` are byte-identical between cycles, so what
  the user rules on is cycle 1's page. **M2 overruled in writing and accepted** — the seven-kind
  palette *is* the M1 ruling (`docs/design-brief.md:159-167`); `bench.html`'s eighth button is
  the superseded artefact. m3, m4 backlogged.
- **D-007** — comparison index and the recommendation (**M1 checkpoint**) — #21, `5839027`,
  2 cycles + 1 re-spec, clean gate `0R / 0M / 3m`. checks=8. It recommended **Board**; the user
  **overruled it and chose Bench, 2026-09-01** — see `## Decisions in force`. m4/m5/m6
  backlogged. Both majors were false cross-document *paraphrases* — C8 gates quotations only,
  which is why the cycle-2 dispatch also required a claim/`file:line` table.
- **D-006** — Board node graph, typed columns, terminal plot node — #20, `0aee604`, 3 cycles,
  final gate `1R / 0M / 0m`. **Merged on the user's ruling with C10 overruled in writing**
  (PR #20 comment `5497106719`). C6's fixed 650×460 plot, M1's "lanes must not read as empty"
  and C10's "the emptiness must not be papered over" are mutually unsatisfiable, and the Data
  lane provably cannot hold a second card — `VALID_CONNECTIONS` chains nothing to a second
  `DataSource`. **C10 was my defect twice:** first trivially satisfiable (the `aria-hidden`
  filler added for M1 became the element satisfying the metric), then unreachable by
  construction once the instrument was made honest. §2's *do the feasibility arithmetic before
  you impose a floor* was never done. checks=11, 10 met. C8/C9 closed D-005's m4 and m9.
- **D-005** — Bench node graph, free canvas, drag-to-connect — #16, `4720179`, 3 cycles,
  `0R / 0M / 4m`. Merged by the user by hand before its cycle-3 review ran — legitimate,
  confirmed 2026-09-01, closed. m4/m9 → D-006 C8/C9. **m7 still open** (the "chips render
  identically" body claim, three cycles uncorrected).
- **D-008** — CVD-safe node palette + the checker claim — #7, `2d0de23`, 3 cycles + 1 re-spec,
  first design task to close on a clean gate.
- **D-004** — Beamline node graph, shared palette and checker — #6, `bac2f62`, 3 cycles,
  §5.7 limit; 2 open → **D-008**.
- **D-003** — interactive plot component at reference parity — #5, `99ec8f3`, 4 cycles, merged on
  the user's explicit override.
- **D-001** — wireframes: mission screen and recipe builder — #2, `b580729`, 4 cycles, 1 open;
  superseded by the 2026-08-16 node-graph pivot.

## Floors in force

- **`verify.py --all` EXITS 1 on `main` as of `0aee604`**, with exactly one known-red section:
  `board-lane-fill`. That is D-006's overruled C10, left registered and red **on purpose** so the
  constraint stays visible if the node model or the plot's sizing ever changes.
  **A future task must not read that as a regression it introduced, and must not delete,
  disable, relabel or downgrade that section to make the run green.**
- **The `all_results.append` / `line()` floors are counted from the AST, not by grep** (D-010
  cycle 2, 2026-09-04). The old `grep -c` counted lines that merely *mention* the string,
  including the counting lines themselves — it reported 86 against 78 real registrations. On
  `task/d-010-page-shell` at `cfd2a1d`: **78** registrations, **213** reporting calls, both by
  `ast.walk`. Do not reinstate a grep floor.
- **`verify.py` on `main` at `63a6fd8`: 81 AST registrations / 217 reporting calls** (D-014).
  The fade affordance is guarded by `shell-canvas-fade-affordance` over **12 layouts**
  (4 palette/panel states x 1440/1024/768); it goes red if a cue is painted where the region
  does not overflow. Superseded: 79 / 215 at `a059f34` (D-010).
  Superseded: `verify.py` on `main` at `72d2950`: **71** registered sections.
  `grep -c 'all_results.append'` = **71**; `grep -c 'results.append\|line('` = **269**.
  A fall in either is `Required`. Superseded: 69 / 233 at `0aee604` (65 sections). Superseded historical figure: 46 / 149 / 121 non-bench at
  `4720179`, whose 149 was measured by an unrecorded command and does not reproduce.
- D-008's six simultaneous palette floors: min CVD ΔE **5.129** (≥4.0), normal-vision node-node
  **14.170** (≥14.0), node-vs-reserved **13.442** (≥4.0), white-on-fill **4.595:1** (≥4.5),
  fill-vs-reserved hue gap **14.1°** (≥12.0°), clamping excess **+0.0051** (≤0.01). Asserted
  inside three registered sections, not six.
- **Do not re-derive:** `.board-wrap { overflow-x: hidden }` does *not* break a scroll-reachability
  check — `overflow: hidden` stays programmatically scrollable via `scrollLeft`. Established by
  D-006's cycle-2 reviewer.
