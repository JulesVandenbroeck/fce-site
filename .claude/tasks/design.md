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

**D-009 merged 2026-09-02 (#22, `948e6ec`). D-002 is the only design task in flight, and its
2026-09-01 dispatch was lost — see below.** Counts below were enumerated by `scout` at
`9495696`, not inherited from the entries.

### D-002 — Design token foundation
- **Scope:** `src/fce_web/static/css/tokens.css` (NEW), `src/fce_web/static/fonts/` (NEW),
  `docs/design-explorations/verify.py` (append-only)
- **Accept:** C1 token declarations only, zero non-custom-property declarations outside
  `@font-face`; C2 documented AA ratios computed not asserted, text pairs >=4.5:1, `--ink-45`
  labelled non-text-safe; C3 self-hosted woff2, every `src:` resolves on disk, no network
  reference; C4 a serif and a mono, none of Inter/Roboto/system-ui/Space Grotesk; C5 **FOUR**
  node hues + sample identity + lock state, D-008's six floors re-verified; C6 `verify.py`
  counts rise, `board-lane-fill` still the only red, diff confined. **checks=6.** C2 and C5
  are mutation-gated.
- **CONTRACT TASK** — `tokens.css` is consumed read-only by D-010, F-002 and every later
  design task. Raise the reviewer's *effort*, not its model (§3). Do not merge with an open
  finding against the token set; D-004 did and it cost D-008.
- **Enumerated** (`scout`, re-run 2026-09-02 after the interiors ruling): input
  `docs/design-explorations/tokens.css` is 308 lines / 46 properties;
  `--tab10-x1/2/3` = `#1f77b4`/`#8c564b`/`#17becf` at :74-76 (the CORRECTED pair, not
  `#ff7f0e`/`#2ca02c`); `--ink-45: rgba(43,38,32,0.45)` at :42, composites 2.60:1, fails AA.
  **`--node-*` is NINE properties at :277-285, not ten** — eight fills plus
  `--node-label-on-fill: #ffffff` at :285. The entry's earlier "ten" was a count nobody
  enumerated. Under ruling 7 only **four** are palette hues: `--node-multiplicity` `#706b30`
  (:278), `--node-selection` `#1c5611` (:279), `--node-histogram` `#4846a5` (:284), and **one**
  Observable hue to be chosen from the four existing `--node-obs-*` at :280-283 (`#2a6b64` /
  `#306baf` / `#6a387c` / `#993a5a`). `--node-data` `#966746` (:277) styles a node the student
  never places. `verify.py` floors **69** / **233**. Neither target file exists yet.
- **Feasibility of the NEW C5, stated so it is not re-derived:** D-008's six floors were measured
  over EIGHT fills; **four** are retained. Removing a member from a set can only raise or hold a
  pairwise minimum, so every one of the six floors stays reachable by harvesting D-008's
  committed values — the same argument that held at seven, only stronger. The dispatch forbids a
  new palette search.
- **Depends on:** ~~the M1 style choice~~ — settled 2026-09-01, Bench.
- **Branch / PR:** `task/d-002-tokens` — **branch exists at `9495696` with ZERO commits, no PR.**
- **Status:** **cycle 1, re-dispatched 2026-09-02**, own worktree, Opus. The 2026-09-01 dispatch
  was LOST — reconciled against git: the branch was created at `9495696` and never written to, no
  handoff, no anchor. This is still cycle 1. The dispatch carries the re-spec'd C5 (four hues),
  the corrected nine-not-ten `--node-*` count, the harvest-don't-search instruction with D-008's
  six floors and their published values, and the warning that `verify.py --all` exits 1 on `main`
  by design with `board-lane-fill` as the intended red.
- **History:** [`archive/design.md`](archive/design.md)

## Ready

_none — both released tasks are in flight._

## Blocked

### D-010 — The three-region page shell
- **Scope:** the shell layout for the Bench canvas — CSS only; the markup it needs is a frontend
  task raised off the back of this one.
- **Accept:** the graph canvas is always present and never covered; "Add a Node" sits left and
  collapses; the mission panel sits right, expands, and pages back to previous missions.
  Collapse/expand state is `ui` state (brief §4) — it never enters the run payload.
- **Depends on:** ~~D-009~~ merged 2026-09-02, ~~the user's interiors ruling~~ made 2026-09-02
  (**inline grow**, four-kind palette). Now depends on **D-013** — the merged `Observable`
  interior does not exist in any page yet, and it is the widest node, so it is what sets palette
  width. Design the shell against a node with two footprints; see `## Decisions in force` 6.
- **Branch / PR:** not yet opened

### D-013 — The merged `Observable` node interior
- **Scope:** the single `Observable` node interior with a four-way mode toggle, in the
  **inline-grow** treatment, as a new option on the D-009 exploration page. Raised 2026-09-02 out
  of the interiors ruling (`## Decisions in force` 7).
- **Why:** D-009 shipped four separate `Obs*` interiors and the ruling collapses them into one.
  That merged node exists in no page, and it is the **widest** node in the palette —
  `ObsVectorSum`'s mode alone carries three checkboxes and a select — so it is what D-010 must
  size the palette against. The other three kinds (`Multiplicity`, `Selection`, `Histogram`) ship
  as delivered and are not re-opened.
- **Accept:** one `Observable` node, collapsed and opened, all four modes reachable, each mode's
  controls as D-009 already designed them (`interiors.html`, inline-grow option: ObsGlobal
  :498-527, ObsObject :530-568, ObsVectorSum :571-607, ObsCustom :610-636); the mode control
  keyboard-operable; opened height measured and reported per mode, because that number is
  D-010's input. Mutation-gated, same shape as D-009's C9/C10.
- **Depends on:** nothing. **Blocks D-010.**
- **Branch / PR:** `task/d-013-observable-interior` — not yet opened
- **Status:** cycle 1, dispatched 2026-09-02, own worktree. **checks=8**, C1-C4 mutation-gated.
  Ships as a NEW page (`observable.html/.css/_verify.py`) rather than a third option on
  `interiors.html` — D-009 is merged and its C2 asserts both options' kind sets are exactly the
  seven, so appending there would have required reopening a passing check to add a page that
  contradicts it. C5 exists solely to hand D-010 the tallest opened mode height.

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
- `verify.py` on `main` at `0aee604`: **65** registered sections, **265** passing assertion
  lines. `grep -c 'all_results.append'` = **69**; `grep -c 'results.append\|line('` = **233**.
  A fall in either is `Required`. Superseded historical figure: 46 / 149 / 121 non-bench at
  `4720179`, whose 149 was measured by an unrecorded command and does not reproduce.
- D-008's six simultaneous palette floors: min CVD ΔE **5.129** (≥4.0), normal-vision node-node
  **14.170** (≥14.0), node-vs-reserved **13.442** (≥4.0), white-on-fill **4.595:1** (≥4.5),
  fill-vs-reserved hue gap **14.1°** (≥12.0°), clamping excess **+0.0051** (≤0.01). Asserted
  inside three registered sections, not six.
- **Do not re-derive:** `.board-wrap { overflow-x: hidden }` does *not* break a scroll-reachability
  check — `overflow: hidden` stays programmatically scrollable via `scrollLeft`. Established by
  D-006's cycle-2 reviewer.
