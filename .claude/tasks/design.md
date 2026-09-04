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

### D-010 — The three-region page shell
- **Scope:** `docs/design-explorations/shell.html`, `shell.css`, `verify.py`
- **Accept:** **checks=10** (was 9; C10 added by cycle 3's M6 fix) — verbatim in PR #25's body. C1 canvas never covered; C2 palette
  collapse gives its width to the canvas only; C3 palette inner width >= 328.0px; C4 an opened
  node is contained and paints above what it overlaps; C5 the pager reads `m3,m2,m1,m2,m3`;
  C6 ui state never enters the run payload; C7 only the shipped `tokens.css`; C8 reduced motion +
  focus walk; C9 the verify.py floors hold and `board-lane-fill` stays the only red; C10 canvas type stays legible (scale >= 0.95, rendered label >= 11.0px) across 4 states x 3 widths.
- **Depends on:** ~~D-009~~, ~~D-013~~, ~~D-002~~ — all merged.
- **Branch / PR:** `task/d-010-page-shell` — **#25**, `6d91a96`
- **Status:** **cycle 2 delivered `cfd2a1d`; §5.1 gate reproduced 2026-09-04 in `~/fce-gate-d010c2`
  — all 9 shell sections PASS, `FAILED sections: ['board-lane-fill']` and nothing else, flake8 0
  across `src/ tests/ scripts/` + `verify.py`, AST floors 78 / 213, diff vs merge base = the 3
  scoped files. Cycle-2 reviewer dispatched.** All six findings reported fixed, none overruled.
  M2 fixed in CSS only — `shell.html` untouched, so no markup or JS moved this cycle: the canvas
  region gets `flex: 1 1 0` + a 384px `min-width` floor, the two side regions yield instead, the
  canvas SVG scales by viewBox rather than cropping, and two breakpoints step the panel down at
  1024 and both regions at 768. **M4's grep floor is retired for an AST count — 78 registrations
  and 213 reporting calls, superseding the self-inflating 86 / 303.** One deviation declared and
  handed to the reviewer to rule on: at <=768 the expanded palette is 192px, below C3's 328px, on
  the argument that no 768 row holds a 368px palette + 320px panel + a canvas above its 384px
  floor. checks stay 9.
  Cycle-1 gate had reproduced (9/9 shell sections PASS,
  `FAILED sections: ['board-lane-fill']`, counts 86/303, diff = the 3 scoped files).
- **Review:** cycle 2 `0R / 2M / 3m`, `verdict=rework`, scope pass, PR #25 comment `5538399914`.
  **Cycle 3 delivered `04849a1`; §5.1 gate reproduced 2026-09-04 — 413 passed, flake8 0, AST
  floors risen 78/213 -> 79/215, all 10 shell sections PASS, `FAILED sections: ['board-lane-fill']`,
  diff = the 3 scoped files. Cycle-3 reviewer dispatched — the §5.7 limit. If it does not close at
  0R/0M, stop and escalate.**
  **M6 was FIXED, not overruled.** `.canvas-wrap` becomes a fixed 704x512 surface with
  `.canvas-region` scrolling, minimum scale 1.0, so no downscaled type — and the fix ships **the
  observer that was the actual finding**: new section `shell-canvas-text-legible` = **C10**,
  measuring the SVG's screen CTM scale and every label's rendered px over 4 states x 3 widths,
  with `SHELL_CANVAS_MIN_SCALE = 0.95` and `SHELL_CANVAS_MIN_TEXT_PX = 11.0`. **checks 9 -> 10.**
  The coder verified the reviewer's numbers before acting rather than accepting them: the fluid
  wrap did render at x0.5199 at 1024, putting a 14px title at 7.28px. M5 fixed by matching the
  unit generically and exempting by value; m4, m5, m6 all folded in.
  Deviation: the worktree ran detached and pushed a fast-forward to the branch, because
  `task/d-010-page-shell` is checked out in two stale agent worktrees. No new branch, no
  force-push — confirmed from git at the gate. All six cycle-1 findings verified fixed by the reviewer's own mutations, not by the
  coder's transcripts. **C3's <=768 deviation is SETTLED and accepted** — the reviewer did the
  arithmetic: 368 + 64 + 384 = 816 > 768, so no 768 row holds the palette at 328px+ with the
  canvas above its floor. C3 is met; do not reopen it.
  **M5** is R1's blind spot one layer down — C7's `length_re` still enumerates units in a fixed
  alternation, so `90dvh` / `12pt` / `2cm` / `0.25turn` report zero offenders. Match units
  generically, exempt by value.
  **M6 is a fix-induced regression and the clearest instance of §5.5 on this project yet:** the M2
  fix keeps the canvas on screen by scaling the SVG viewBox, which scales the text with it — 0.52
  at 1024, 0.497 at 768, so a 14px node title renders near 7px. Cycle 1's defect was traded for a
  new one **and no check observes it**, which is the actual finding. Overrulable in writing as
  belonging to the real Bench implementation; if fixed, it must add a check on rendered text size.
  m4 (the C9 docstring misrecords 2 registrations as pre-existing when AST shows this PR added
  them), m5 (the 768 gap is exactly 384.0px against a 0.5 tolerance — zero headroom, document it),
  m6 (the deviation note never addresses the reflow alternative) — all three folded into cycle 3
  and backlogged.
  Cycle 1 `2R / 4M / 3m`, `verdict=rework`, scope pass, PR #25 comment `5524842859`.
  **Both Requireds are instruments that cannot fail, and both were mutation-proven, not argued.**
  R1 `verify.py:6568-6580` — C7's literal sweep matches hex only, so `white`, `rebeccapurple`,
  `rgb()`, `hsl()` all pass, and `length_re`'s trailing `\b` after `%` can never match, so every
  percentage is invisible; `.palette { width: 42% }` leaves it at "zero offenders". Same class as
  D-002 cycle 3's M3, reintroduced in a new sweep. R2 `verify.py:6236-6263` — C1's 24 probes are
  derived from the canvas region's **own** rect, so they shrink with it: `max-width: 3px` still
  reports 24/24 PASS; and it only ever runs at 1440.
  M1 focus ring asserts presence not perceivability (the `verify.py:2405` pattern; real rings
  measure 6.20-6.69:1, so the page is fine and the check is not). **M2 is the only finding against
  the design itself:** the canvas surface is a fixed 704x512 in a region free to collapse — at
  1024 both exemplar nodes sit at x=733-866, outside a 336px region; at 768 the region is 80px and
  shows nothing. M3 13 new flake8 violations in a file flake8-clean on `main` (the F841 is a dead
  duplicate of the exemption list). **M4 is my defect:** C9's `grep -c 'all_results.append'` counts
  lines that merely *mention* the string, including the counting lines themselves — 86 reported
  against 78 real registrations by AST. The property holds (67 -> 78, nothing lost) but the floor
  is self-inflating. m1/m2/m3 backlogged.
- **History:** [`archive/design.md`](archive/design.md)

## Ready

_none._


## Blocked

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
- `verify.py` on `main` at `72d2950`: **71** registered sections.
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
