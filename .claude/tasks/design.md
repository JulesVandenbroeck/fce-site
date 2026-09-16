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

### D-016 — Results region and chart styling
- **Scope:** `static/css/chart.css` (new), `static/css/shell.css`, one `<link>` in `base.html`
  (the D-015 precedent), class attributes only in `shell.html`.
- **Branch / PR:** `task/d-016-results-chart-styling` — #48, gate reproduced (697 passed, flake8 0), in review (cycle 1)
- **Status:** **handed off (cycle 1)** at the session's usage limit, 2026-09-16, ~1 minute after dispatch.
  **No branch, no commit, no CSS written** — confirmed against git, not taken on trust. Handoff:
  [`handoff/d-016-design-1.md`](../handoff/d-016-design-1.md), 113 lines, copied into the primary checkout
  from the agent's worktree (worktree isolation refused it the primary path). **Re-dispatch from the
  criteria in this entry and the dispatch, not from the handoff** — the handoff's value is the reading it
  already did and the one open question below. checks=13 (C1-C13).
- **The open question it raised before stopping, and it is worth answering first.** The dispatch tells the
  coder to fix C1 by constraining `.chart-figure` with `overflow-x: auto` and not touching
  `.canvas-region`'s direction. The agent read the widths and doubts a **row** layout is structurally
  viable at all: `.canvas-region` has ~752px at 1440, and `.canvas-wrap` alone takes 704px, leaving ~48px
  for `#run-control` + `#results` beside it. That would explain F-007's F11 (`#results` rendering ~26px
  wide) as a symptom of the same cause rather than a separate gap. **It had not yet measured this in a
  browser** — that was its next step, and it is the right next step. If the measurement holds, my
  prescribed fix is wrong and the region needs to stack rather than sit beside the canvas; the criterion
  is C1's `elementFromPoint` property, which does not care which way it is solved. Re-dispatch should say
  so explicitly rather than repeat `overflow-x: auto` as if it were settled.
- **Its worktree is reusable:** `.claude/worktrees/agent-a1a7be38838a932a5`, clean, no venv yet.
- **Re-dispatched 2026-09-16 (session 2), fresh `isolation: "worktree"`, effort high.** The original
  dispatch's verbatim C1-C13 was never written to disk; **criteria reissued** in the new dispatch and are
  verbatim in its PR body once opened. C1 canvas not displaced (elementFromPoint, mechanism free, measure
  row-vs-stack first) · C2 figure fixed 650x460, no page h-scroll 1440/1024/768 · C3 sample colour
  identical band/legend via `--frozen-x*` · C4 `.hist-band` fill-opacity 0.8 · C5 `.legend-frame` not
  black · C6 `.bin-hit` focus ring ≥3:1 · C7 reveal forwards, unarmed = settled · C8
  `#run-button[aria-disabled=true]` busy style · C9 `.results__note` quiet note, AA · C10 tokens only,
  computed styles enumerated · C11 light ground, AA text, no `--ink-45` text · C12 `verify.py` unmodified,
  scope by `main...HEAD` · C13 suite ≥697, flake8 0, F-007 F11 closed.
- **Depends on:** F-007 `1fdb8e6`, F-008 `7472675` — both merged. **Last task in M3; checkpoint 2 follows.**
- **At the §2 ceiling deliberately, and I am recording the choice.** 13 criteria is past the five-bullet
  splitting test. Splitting it would mean two serialised tasks on the same page and two review passes over
  tightly coupled rules — the figure's fixed 650x460 is exactly what breaks the region's layout, so the
  layout half and the paint half cannot be judged apart. If it cycles twice, split it rather than pushing
  for a third.
- **C1 is a live defect on `main`, not a cosmetic gap.** Once the chart renders, node `n1`'s handle centre
  moves off `.node__title` onto a `.palette__add` button at 1280x720. Mechanism traced by PR #47's
  reviewer: `shell.css:183-204`'s `.canvas-region { display: flex }` + `.canvas-wrap { margin: auto }`
  loses its free space to a 650px `.chart-figure` sibling. F-008's test drags `n4` to route around it.
- **Facts given, enumerated by `scout`, not remembered:** sample identity colours already exist as
  `--frozen-x1/x2/x3` (`tokens.css:169-171`) — `--tab10-*` at `:188-190` are for static-export parity and
  are not the interactive renderer's. `base.html:9-12` links four stylesheets in order. The 19 classes
  `chart.js` emits are listed in the dispatch.
- **`verify.py` is not this task's instrument** — it lives in `docs/design-explorations/`, guards the
  exploration pages, and none of its 81 sections touch the chart, results region or run control. The
  dispatch asks for a standalone Playwright script reading **computed styles and rendered geometry**,
  pasted into the PR body and not committed. If those guards should become permanent, that is a task for
  whoever owns the file they would live in — design owns no test file.
- **Carried in from F-008's review, all in the dispatch:** `.legend-frame` paints as a solid black block
  (a filled rect with no `fill`, drawn before its own swatches); `.hist-band` needs the `fill-opacity`
  0.8 that F-008 removed from the JS; `.bin-hit` needs a visible focus ring for 50 focusable targets;
  the reveal must settle with `animation-fill-mode: forwards` because `.reveal-armed` is added once and
  never removed. **F9 from PR #47 — one garbled sentence stating that last point — is corrected here
  rather than costing a cycle.**
- **C8 carries F-007's accessibility consequence:** `#run-button` gave up the `disabled` attribute to keep
  keyboard focus mid-run, so the browser's free busy affordance is gone and this CSS rule is the only one.

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
