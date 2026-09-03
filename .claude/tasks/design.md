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
- **Status:** **HANDED OFF (cycle 1) — agent killed mid-task 2026-09-02.** See
  [`handoff/SESSION.md`](../handoff/SESSION.md).
  **The work is NOT lost and NOT on the dispatched branch.** Reconciled against git: one commit
  `edf82c9` sits on **`task/d-002-tokens-work`**, local only, never pushed, no PR. The dispatched
  branch `task/d-002-tokens` is still at `9495696` with zero commits. Diff against `main` is
  8 files, all in scope: `src/fce_web/static/css/tokens.css`, four `.woff2` (EB Garamond roman +
  italic variable, Fira Mono 400 + 500), two OFL licence files, and `docs/design-explorations/
  verify.py`. Completeness unverified — no gate was run, no PR body exists.
  **PUSHED to origin 2026-09-02 — `task/d-002-tokens-work` at `841a044`** (`edf82c9` plus a
  merge of `main`); the work is no longer local-only. Still no PR and no gate run. Next move:
  open the PR from that branch, then run the §5.1 gate. Do not re-dispatch from scratch.
  **Coder dispatched 2026-09-02 (own worktree, Opus) to verify the existing commit against
  C1-C6 and open the PR from `task/d-002-tokens-work`** — not to redo the work. The dispatch
  carries the six criteria with `Check:`/`Expect:` pairs (they had none before), the enumerated
  facts, D-008's six floors with harvest-don't-search, and the `board-lane-fill` warning.
  **Delivered `6a874fd`, PR #24 opened. §5.1 gate reproduced 2026-09-02 in `~/fce-gate-d002`
  with the primary `.venv`:** the four token sections PASS / exit 0, counts **71** / **260**
  (floors 69 / 233), both greps exit 1, flake8 exit 0, `git diff main...HEAD --name-only` = the
  8 scoped files. Six floors clean and above D-008's harvested values: 6.116 / 20.246 / 13.442 /
  5.476:1 / 37.31 deg / +0.0000 — no palette search was run. `--ink-45` 2.596:1, present and
  labelled NON-TEXT-SAFE, asserted below AA rather than fixed.
  **C6 NOT MET, and it was unsatisfiable inside the file scope I gave — my defect, §2 question 3,
  the B-005 shape.** `--all` exits 1 with **three** reds, not one: `board-lane-fill` (intended)
  plus `git-diff-clean` and `bench-git-diff-clean`. `check_git_diff` (`verify.py:1885-1908`,
  registered twice) asserts `git diff --stat main...HEAD -- src/ tests/ content/` is empty, and
  D-002 is the first task that legitimately ships into `src/`. **Ruling 2026-09-02: narrow the
  guard to exempt exactly `src/fce_web/static/css/tokens.css` and `src/fce_web/static/fonts/**`;
  everything else under `src/`, `tests/` and `content/` stays guarded.** Re-spec'd and
  re-dispatched: scope widened to permit editing that one section, C6 re-worded, and **C7 added
  — the narrowed guard must still go red on a probe file under `src/fce_web/routes/` and under
  `tests/`**, four transcripts. **checks 6 -> 7. Still cycle 1** (a re-specification, not a
  cycle). Two declared deviations accepted: edits inside sections *this branch itself* added
  (strictly additive, both counts rose), and one `tokens.css` rounding fix 4.63 -> 4.62:1 found
  by the new check, no colour changed.
  **Open for later:** nothing on this branch renders the shipped `tokens.css` — `base.html`
  links no stylesheet (that is F-002) and the exploration pages read
  `docs/design-explorations/tokens.css`. So there are no screenshots of the real file by
  construction, and F-002 is what first exercises it.
  **C6 re-spec delivered `93c4b14`; §5.1 gate reproduced 2026-09-02 in `~/fce-gate-d002`:**
  `verify.py --all` exits 1 with `FAILED sections: ['board-lane-fill']` — the intended red and
  the ONLY one; counts **71 / 262**; flake8 exit 0; `git diff main...HEAD --name-only` = the
  8 scoped files. C7's four probe transcripts are commit-based (the guard diffs commit to
  commit, so a working-tree probe is invisible to it) and net out of the branch diff.
  `check_git_diff` is now `--name-only` against a two-entry allowlist —
  `SHIPPED_DELIVERABLE_FILE` / `SHIPPED_DELIVERABLE_DIR` at `verify.py:1885-1900`. **Any future
  task shipping under `src/`, `tests/` or `content/` will trip it and needs an orchestrator
  ruling to widen it — that is intended, not a defect.** Declared deviation accepted:
  `git-diff-clean` was added to `TOKENS_SECTIONS` so C7's `--section` command resolves; that
  dict is this branch's own addition, not a pre-existing section. **Cycle 1 reviewer dispatched**
  with the effort raised, as a contract task. **checks=7.**
  **Cycle 1 reviewed 2026-09-02: `0R / 2M / 3m`, scope pass, `verdict=rework`** — posted to
  PR #24 (`issuecomment-5510102458`). Everything claimed reproduced, and the reviewer re-derived
  all 23 WCAG ratios and three of the four CVD floors independently, decoded the four woff2 with
  `fontTools` (EB Garamond carries an `fvar wght 400-800` axis; all four cmaps hold the physics
  glyph set; 233,224 bytes total), and ran 18 mutations of which every one bit — including
  `--section no-such-section`, which fails rather than silently passing.
  **M1, and it is why this is a real cycle (§5.4 clause 3 — no criterion of mine ever gated it):
  no NON-TEXT contrast is computed anywhere, and `APP_TEXT_PAIRS` has no completeness
  assertion.** Measured by the reviewer: `--chrome-border` on `--chrome-bg` **1.30:1**,
  `--locked-border` on `--locked-fill` **1.39:1**, `--frozen-x3` on paper **2.73:1**,
  `--tab10-x3` on paper **1.92:1**, against WCAG 2.2 SC 1.4.11's 3:1. `--chrome-border` is what
  D-010 and F-002 will reach for as a control boundary. **A contract task does not merge with an
  open finding against the token set — D-004 did and it cost D-008.**
  **Cycle 2 dispatched 2026-09-02** with C8 (every non-text pair computed against 3:1, or on a
  named exemption list stating why it is not a UI boundary; mutation-gated) and C9 (every
  declared colour token appears in some computed pair or exemption list, so a later token cannot
  be silently uncovered; mutation-gated by adding an uncovered probe token). **checks 7 -> 9.**
  The dispatch states the feasibility per pair: the two border tokens can be darkened freely
  because neither is a node hue and neither enters D-008's six floors; the series colours are
  legitimately exemptible if the use is stated. **If a fix would move a node hue, stop — do not
  trade one floor for another.**
  **M2 RATIFIED BY ME, not a defect:** `verify.py:6324`'s `main()` condition gained
  `and not args.section`, outside the append-only scope, but it is behaviour-preserving and my
  own `Check:` commands forced it. The coder adds it to Deviations; no code change.
  m1 (`--timing` / `--duration-base` alias pair undocumented) and m2 (`verify.py:1948` prints
  `[PASS]` while asserting nothing) folded into cycle 2; m3 is a stale `260` in the PR body next
  to the correct `262`.
  **Cycle 2 delivered `d869d7e`; §5.1 gate reproduced 2026-09-03 in `~/fce-gate-d002` with the
  primary `.venv`:** `--section tokens-nontext` all PASS / exit 0 (44 non-text pairs computed
  above 3:1, 12 exemptions each naming both tokens and a reason, 34 of 34 declared colour tokens
  covered); counts **71 / 267** (floors 71 / 262); flake8 exit 0; `--all` exits 1 with
  `FAILED sections: ['board-lane-fill']` — the intended red and the only one; `git diff
  main...HEAD --name-only` = the 8 scoped files. Three colour values moved to clear SC 1.4.11 —
  `--chrome-border` `#d8cba8`->`#847c66`, `--locked-border` `#b3a98c`->`#726c59`, `--frozen-x3`
  `#b5883a`->`#a67d36` — **no node hue and neither reserved colour moved, so D-008's six floors
  are byte-identical to cycle 1's.** m1/m2 fixed, m3 noted (the live count is 267).
  **Cycle 2 reviewer dispatched 2026-09-03**, effort raised, contract task. **checks=9.**
  **Cycle 2 reviewed 2026-09-03: `0R / 1M / 2m`, scope pass, `verdict=rework`** — posted to
  PR #24 (`issuecomment-5522877398`). M1, M2, m1, m2, m3 all closed and verified: the reviewer
  re-derived all nine new non-text ratios independently to 3 dp, and ran mutations against C1,
  C2, C5, C7 and C8 (all monkeypatched, no repo file edited) — every one bit. `--all` 70 PASS /
  1 FAIL, section count 70 -> 71, `pytest tests/ -q` 413 passed.
  **M3, and it is a real cycle (§5.4 clause 3 — C9 shipped with a command; the command is
  blind):** `verify.py:7418-7424`'s C9 denominator counts a custom property as a *colour* only
  if its value parses as hex or `rgb()/rgba()`. The reviewer probed it: `#123456` and
  `rgb(18, 52, 86)` both FAIL and name the offender, but `hsl(...)`, `teal`, `oklch(...)` and
  `color-mix(...)` all **PASS silently** at "34 declared, 34 covered". Nothing shipped is
  mismeasured — C9's stated property simply does not hold in a contract file that later tasks
  extend. **Cycle 3 dispatched 2026-09-03** with C10: the recogniser must accept every CSS
  colour syntax, gated one probe per syntax (six transcripts), plus the negative that a
  probe-free run still exits 0 at 34/34 so widening cannot misclassify a length or a font stack.
  **checks 9 -> 10. This is the §5.7 limit — if it does not close at 0R/0M, escalate rather
  than dispatch a fourth.** m4 (`tokens.css:163-164`'s uncomputed "stays above 19 delta-E",
  true at 19.212) folded into cycle 3; m5 (the exploration `docs/design-explorations/tokens.css`
  still holds the three pre-fix values, divergence unrecorded) **backlogged** — that file is
  outside D-002's scope.
  **Cycle 3 delivered `8b16126`; §5.1 gate reproduced 2026-09-03 in `~/fce-gate-d002`:**
  `--section tokens-nontext` exit 0 (34 declared / 34 covered, 44 pairs PASS, 12 EXEMPT, the
  three frozen-sample separations 42.501 / 26.063 / 19.210 dE above a 19.0 floor); counts
  **71 / 269**; flake8 exit 0; `--all` exit 1 with `FAILED sections: ['board-lane-fill']` and
  nothing else; `git diff main...HEAD --name-only` = the 8 scoped files. M3 fixed at
  `verify.py:7420-7525` (`_looks_like_colour`: hex 3/4/6/8, eleven functional notations, the
  CSS named-colour set plus `transparent`/`currentcolor`, whole-value matches) — six per-syntax
  probes each exit 1 naming their own token, six non-colour probes each exit 0 at 34. m4 fixed:
  the "19 delta-E" claim is now recomputed inside a registered assertion, `tokens.css:159-168`
  comment only, no declaration value changed. **The PR body hit GitHub's 65,536-character
  limit** — C1-C10 and the check count are in the body, the cycle-3 transcripts in a linked
  comment (`issuecomment-5523071669`). Both are on the PR, so §4 rule 3 holds; a future task on
  this PR must append to the comment, not the body. Declared deviation accepted: two pair-loop
  guards inside this branch's own cycle-2 section were widened from absent-token to
  absent-or-unmeasurable, so a covered unmeasurable colour is named rather than raising a
  `ValueError` out of `_composited`. **Cycle 3 reviewer dispatched 2026-09-03**, effort raised.
  **checks=10. This is the §5.7 limit.**
  **Stale ref warning from the coder:** local `task/d-002-tokens-work` in worktree
  `agent-a93cc19d487486041` sits at `841a044`, which is **not** an ancestor of the PR head and
  would revert cycle 2 and 3. Nothing may be committed from that worktree. The remote branch is
  authoritative.
  **Uncollected:** the coder's 50%% anchor is untracked inside its worktree at
  `.claude/worktrees/agent-aa484a2374583ffaa/.claude/handoff/d-002-design.anchor.md` — committing
  it would have failed C6's own diff check. Collect it only if a handoff is needed.
- **Was:** cycle 1, re-dispatched 2026-09-02, own worktree, Opus. The 2026-09-01 dispatch
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
  ~~D-013~~ **merged 2026-09-02 (#23, `309c409`). D-010 is now READY** — its input is settled:
  opened node **328.0 x 300.0px**, collapsed **80.5px**, inline grow.
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
