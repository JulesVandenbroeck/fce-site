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
   so the node would have exactly one legal value. The palette is **seven** kinds:
   `Multiplicity`, `Selection`, the four `Obs*`, `Histogram`. Future energies are future
   missions, not a chooser. → brief §4.
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

**Consequence for M3, recorded so it is not rediscovered:** the engine's allowlist still makes
`DataSource` the root of every chain. With it out of the palette, the **run payload synthesises
one at submit** from the mission's declared dataset. The student's graph and the engine's graph
are no longer the same object. The engine is not modified. Also in `backend.md`
`## Contracts in force`; `docs/api.md:29-34` still marks `POST /api/run` undefined.

---

## In progress

**Both dispatched 2026-09-01, one worktree each, `effort: high`.** They share no files: D-002
owns `src/fce_web/static/**` plus append-only sections in `verify.py`; D-009 owns the new
`interiors.*` files plus a 3-line README note, and is forbidden `verify.py` and `tokens.css`.
All counts below were enumerated by `scout` at `9495696`, not inherited from the entries.

### D-002 — Design token foundation
- **Scope:** `src/fce_web/static/css/tokens.css` (NEW), `src/fce_web/static/fonts/` (NEW),
  `docs/design-explorations/verify.py` (append-only)
- **Accept:** C1 token declarations only, zero non-custom-property declarations outside
  `@font-face`; C2 documented AA ratios computed not asserted, text pairs >=4.5:1, `--ink-45`
  labelled non-text-safe; C3 self-hosted woff2, every `src:` resolves on disk, no network
  reference; C4 a serif and a mono, none of Inter/Roboto/system-ui/Space Grotesk; C5 seven
  node hues + sample identity + lock state, D-008's six floors re-verified; C6 `verify.py`
  counts rise, `board-lane-fill` still the only red, diff confined. **checks=6.** C2 and C5
  are mutation-gated.
- **CONTRACT TASK** — `tokens.css` is consumed read-only by D-010, F-002 and every later
  design task. Raise the reviewer's *effort*, not its model (§3). Do not merge with an open
  finding against the token set; D-004 did and it cost D-008.
- **Enumerated:** input `docs/design-explorations/tokens.css` is 308 lines / 46 properties;
  `--tab10-x1/2/3` = `#1f77b4`/`#8c564b`/`#17becf` at :74-76 (the CORRECTED pair, not
  `#ff7f0e`/`#2ca02c`); `--ink-45: rgba(43,38,32,0.45)` at :42, composites 2.60:1, fails AA;
  ten `--node-*` tokens exist but only **seven** are palette hues now. `verify.py` floors
  **69** / **233**. Neither target file exists yet — this creates them.
- **Feasibility (§2), stated so it is not re-derived:** D-008's six floors were measured over
  EIGHT fills; seven are retained. Removing a member from a set can only raise or hold a
  pairwise minimum, so all six stay reachable by harvesting D-008's committed values. The
  dispatch forbids a new palette search.
- **Depends on:** ~~the M1 style choice~~ — settled 2026-09-01, Bench.
- **Branch / PR:** `task/d-002-tokens` — not yet opened
- **Status:** cycle 1, dispatched 2026-09-01
- **History:** [`archive/design.md`](archive/design.md)

### D-009 — Node interiors: how a cut and an observable are actually configured
- **Scope:** `docs/design-explorations/interiors.html`, `interiors.css`, `interiors_verify.py`
  (all NEW), plus <=3 insertions / 0 deletions at the top of `README.md`. Forbidden:
  `tokens.css`, `verify.py`, and every existing page file.
- **Accept:** C1 >=2 options, exactly one recommended; C2 all seven kinds per option, zero
  `DataSource`; C3 collapsed AND opened per (option, kind), rendered heights strictly
  ordered; C4 the `Selection` interior holds both a guided form and raw expression entry,
  both keyboard-reachable, neither `disabled` nor `aria-hidden`; C5 no inline `style=`, no
  network, no build step; C6 no colour defined outside `var(--…)`; C7 README note <=3/0;
  C8 diff confined to the four files. **checks=8.** C1-C4 mutation-gated.
- **A checkpoint task** — same shape as D-004-D-007. The user reads the page and rules.
- **Enumerated:** `README.md` is 81 lines, `**Recommended:** Board` at line 14 — the note goes
  above it. `bench.html` is 727 lines; `buildNodeEl` at :380-460; a node today holds exactly
  ONE configurable property, `subtitle` at :410, value `"not configured yet"` — so this is the
  first interior, not a refinement. `persistUI()` at :289-292 is what any interior must
  eventually serialise into. `bench.html:64-71` still renders EIGHT palette buttons including
  `DataSource`; that page is historical and out of scope, the new page ships seven.
- **Depends on:** nothing. **Blocks D-010** — node size decides the palette width.
- **Branch / PR:** `task/d-009-node-interiors` — not yet opened
- **Status:** cycle 1, dispatched 2026-09-01
- **History:** none yet — first cycle.

## Ready

_none — both released tasks are in flight._

## Blocked

### D-010 — The three-region page shell
- **Scope:** the shell layout for the Bench canvas — CSS only; the markup it needs is a frontend
  task raised off the back of this one.
- **Accept:** the graph canvas is always present and never covered; "Add a Node" sits left and
  collapses; the mission panel sits right, expands, and pages back to previous missions.
  Collapse/expand state is `ui` state (brief §4) — it never enters the run payload.
- **Depends on:** **D-009.** Node size and the number of controls inside a node decide how wide
  the palette has to be and what "collapsed" can mean; designing the shell first would fix the
  wrong dimension.
- **Branch / PR:** not yet opened

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
