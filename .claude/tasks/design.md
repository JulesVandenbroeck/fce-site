# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

### D-006 — Node-graph style C: Board
- **Scope:** `docs/design-explorations/` — create `board.{html,css,js}`; append a `--board`
  section to `verify.py`. `tokens.css` read-only.
- **Accept:** Board persists `{column, slotIndex}` in typed columns and accepts **both**
  gestures plus keyboard connection. Same 64/13/51 enumeration and sweeps. The plot lives
  *inside* the graph as the terminal node, so it must budget for D-003's fixed intrinsic
  **650×460** figure and be shown doing so at 768.
- **Depends on:** ~~D-004~~ (merged `bac2f62`), ~~D-008~~ (merged `2d0de23`) and ~~D-005~~
  (merged `4720179`). Same note as D-005: the fills are final, and `--node-data` is `#966746`.
- **Branch / PR:** `task/d-006-board` — local only at `4720179`, no commits yet. **Cycle 1
  RESUMED 2026-09-01** in the pre-existing worktree `~/fce-worktrees/d-006-board`, which still
  holds the interrupted work uncommitted (`board.html`, `board.css` staged; `verify.py` +1330).
  The coder was told to build on it, not restart, and to merge `main` in (bookkeeping only,
  never rebase). **checks=9**, and this dispatch is the first to carry `Check:`/`Expect:` pairs
  for all nine — the original had none recorded anywhere, which is why they were rewritten
  rather than cited.
**Run D-005 then D-006, serially — never in parallel.** Both append a new section to
`verify.py`; two coders in flight would collide on it, and the worktree rule protects the
branch, not the merge.


## Ready

_none — D-007 is blocked on D-006._

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

- **D-005** — Bench node graph, free canvas, drag-to-connect — #16, `4720179`, 3 cycles,
  `0R / 0M / 4m`, `verdict=approve`. The second design task to close on a clean gate.
  **Merged before its cycle-3 review ran** — see the process note below. 4 minors: m4 and m9
  carried into D-006 as C8/C9; **m7 open** (the "chips render identically" body claim, three
  cycles uncorrected); m9's own generalisation now C9.
- **D-008** — CVD-safe node palette + the checker claim — #7, `2d0de23`, 3 cycles + 1 re-spec,
  **first design task to close on a clean gate**. `verify.py` at 31 sections / 48 assertions.
- **D-004** — Beamline node graph, shared palette and checker — #6, `bac2f62`, 3 cycles,
  §5.7 limit; 2 open → **D-008**.
- **D-003** — interactive plot component at reference parity — #5, `99ec8f3`, 4 cycles, merged on
  the user's explicit override.
- **D-001** — wireframes: mission screen and recipe builder — #2, `b580729`, 4 cycles, 1 open;
  superseded by the 2026-08-16 node-graph pivot.

## Floors in force

### Enumerated for D-006 by `scout` at `b054481` — facts, not inherited claims
- **Enumerated by `scout` at `b054481`, not inherited:** `run_section` at `verify.py:4861`
  wraps **only** the bench block (`:4941-5014`); the beamline block (`:4920-4932`) does not use
  it — that is C9's target. D-008's six floors are asserted inside **three** registered
  sections (`:4959`, `:4967`, `:4974`), not six. `MISSION_SCREEN_DOMAIN_INVENTORY` at `:192`,
  22 items. `derive_reference_legal_pairs()` at `:2222`, `BEAMLINE_ADDABLE_KINDS` at `:168`
  (8 kinds). `check_bench_unflagged_file_url` at `:4777`. `grep -c 'all_results.append'` = 46.
  `verify.py` is 5029 lines. **A bare `python` there has no `playwright`** — the worktree venv
  and `PLAYWRIGHT_BROWSERS_PATH` are both required.
- **Cycle 1 reviewed: `1R / 1M / 2m`, `verdict=rework`, scope=fail.** Review posted verbatim:
  PR #20 comment `5495447592`. **R1 was mine, not the coder's** — `.claude/settings.json` showed
  in the diff because three bookkeeping commits (`b054481`, `08d93af`, `80bf19d`) were never
  pushed, so GitHub attributed my hook config to the PR. Pushed; merge-base moved to `b054481`;
  diff is now the three intended files. Branch never changed, so it cost no cycle. **The
  reviewer's diagnosis corrected my own gate reasoning**, which had diffed against *local* main
  and so saw nothing. M1: the fixed 650×460 plot left `.board-wrap` ~half empty at 1440/1024 and
  put the plot off-screen at 768 behind ~1100px of reserved column — it matters because Board is
  judged beside Beamline and Bench at D-007. m1 (no `Check:`/`Expect:` on C3/C5/C6/C7 — my
  omission) and m2 (one section printing three headers) folded into cycle 2.
- **Cycle 2 delivered `8fe9523`; §5.1 gate reproduced** in `~/fce-gate-d006`: `--all` exit 0,
  **278** assertion lines, **65** summary sections, **0 FAIL**. Floors rose again, measured by me
  at `b054481` and at HEAD: `all_results.append` 46 → **69**, assertion lines 177 → **233**.
  Scope clean at source. M1 fixed by stretching the lanes and adding an `aria-hidden`
  ruled-line filler (`board.css:186,251-266`); m1 and m2 fixed. **checks 9 → 11**, C10 lane-fill
  and C11 plot-reachable-at-768, both mutation-gated by the coder.
- **A defect in MY criterion, disclosed by the coder rather than banked — record it.** C10 as I
  wrote it was **trivially satisfiable**: under the pre-existing `align-items: flex-start` every
  lane's box already equalled its own content, so "unused vertical extent" was ~0 by construction
  and the check could not have failed while the panel was visibly half empty. That is §2's
  "instrument that structurally cannot observe the property it certifies", and it is mine. C10 is
  sensitive *now* only because the fix moved to `align-items: stretch` — **a future revert to
  `flex-start` turns C10 green again with the blank panel back.** Documented in the PR body; the
  cycle-2 reviewer rules on whether C10 needs strengthening. Do not let this close unexamined.
- **Cycle 2 reviewed: `1R / 0M / 0m`, `verdict=rework`, scope=PASS.** Review posted verbatim:
  PR #20 comment `5496706014`. R1, M1, m1, m2 all confirmed fixed and verified independently —
  M1 by screenshots at three widths plus a check that the filler carries no tab stop and is
  invisible to `persistUI`. Every claim in the body reproduced exactly.
- **The single Required is a stronger form of the C10 hole I had already recorded, and the
  reviewer found it by mutating what the PR body had not.** `check_board_lane_fill` takes
  `contentHeight` from the column's *direct children*, and `.board-column__fill` is a direct
  child with `flex: 1 1 auto`, so it always reaches the bottom and `unused` is ~1px whatever the
  lane holds. **Proof: deleting the Multiplicity node outright left a 632.5px lane holding only
  decorative ruling and the check reported `unused=1.0px (limit 158.1px)` `[PASS]` at all three
  widths.** It certifies the wallpaper is present, not that the space behind it is used.
  **Mine before the coder's:** C10 said "the height its own content actually occupies" and never
  defined *content*, and the filler added to satisfy M1 became the thing satisfying the
  measurement — circular by construction.
- **Cycle 3 dispatched — the §5.7 limit.** C10 **restated, not replaced**: same ID, same section
  name, same 25%/120px threshold; *content* now means user-addressable node cards only, with
  `aria-hidden`/decorative children excluded, and the mutation gate is now **node deletion**, not
  filler shrinking. The coder is told explicitly that C10 and M1 are now in tension, that a
  genuine `[FAIL]` is a page problem rather than a measurement problem, and that **reporting the
  threshold as unreachable is a legitimate outcome** — tuning the threshold or narrowing the
  measurement to force green is not. **If cycle 3 does not close `0R/0M`, escalate to the user;
  do not open a cycle 4.**
- **Do not re-derive:** `.board-wrap { overflow-x: hidden }` does *not* break C11 — `overflow:
  hidden` remains programmatically scrollable via `scrollLeft`. Established by the cycle-2
  reviewer.


## Ready

_none — D-007 is blocked on D-006._

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

- **D-005** — Bench node graph, free canvas, drag-to-connect — #16, `4720179`, 3 cycles,
  `0R / 0M / 4m`, `verdict=approve`. The second design task to close on a clean gate.
  **Merged before its cycle-3 review ran** — see the process note below. 4 minors: m4 and m9
  carried into D-006 as C8/C9; **m7 open** (the "chips render identically" body claim, three
  cycles uncorrected); m9's own generalisation now C9.
- **D-008** — CVD-safe node palette + the checker claim — #7, `2d0de23`, 3 cycles + 1 re-spec,
  **first design task to close on a clean gate**. `verify.py` at 31 sections / 48 assertions.
- **D-004** — Beamline node graph, shared palette and checker — #6, `bac2f62`, 3 cycles,
  §5.7 limit; 2 open → **D-008**.
- **D-003** — interactive plot component at reference parity — #5, `99ec8f3`, 4 cycles, merged on
  the user's explicit override.
- **D-001** — wireframes: mission screen and recipe builder — #2, `b580729`, 4 cycles, 1 open;
  superseded by the 2026-08-16 node-graph pivot.

## Floors in force

### Enumerated for D-006 by `scout` at `b054481` — facts, not inherited claims
- **Enumerated by `scout` at `b054481`, not inherited:** `run_section` at `verify.py:4861`
  wraps **only** the bench block (`:4941-5014`); the beamline block (`:4920-4932`) does not use
  it — that is C9's target. D-008's six floors are asserted inside **three** registered
  sections (`:4959`, `:4967`, `:4974`), not six. `MISSION_SCREEN_DOMAIN_INVENTORY` at `:192`,
  22 items. `derive_reference_legal_pairs()` at `:2222`, `BEAMLINE_ADDABLE_KINDS` at `:168`
  (8 kinds). `check_bench_unflagged_file_url` at `:4777`. `grep -c 'all_results.append'` = 46.
  `verify.py` is 5029 lines. **A bare `python` there has no `playwright`** — the worktree venv
  and `PLAYWRIGHT_BROWSERS_PATH` are both required.
- **Cycle 1 delivered `f871dc9` as PR #20** (2026-09-01). **§5.1 gate reproduced** in
  `~/fce-gate-d006` (detached worktree, primary checkout's venv, `PLAYWRIGHT_BROWSERS_PATH`
  exported): `--all` exit 0, **257** assertion lines, **0 FAIL**, "All sections passed";
  `--board` exit 0, **123** lines, 0 FAIL. Scope clean on the three-dot diff — `board.html`,
  `board.css`, `verify.py` only; the `.claude/settings.json` that `gh pr diff --name-only`
  shows is my own `b054481` bleeding through a two-dot diff, **not** a coder edit. **No
  `board.js`** — the module is inlined, so D-005's two wasted cycles were not repaid. Floors
  rose, measured by me at the base and at HEAD with the same command: `all_results.append`
  **46 → 67**, assertion lines **177 → 228**.
- **Sent back at the gate, body-only, NOT a cycle:** the body claims **21** board sections; the
  `--board` run prints **22** distinct section names (17 `board-*` + 4 `anatomy-*` +
  `payload-schema-sanity`). Every other number reproduced. Same shape as D-004 cycle 3's
  "25 sections / listed 26" — the count was decoration. Coder asked to fix the number, state
  the command that yields it, and leave HEAD at `f871dc9`.
- **Two questions left for the reviewer, deliberately not pre-judged by me:** (a) C2 — the coder
  reads D-005's "two supports" as drag-to-connect **and** click-to-connect, where Bench accepts
  the first and refuses the second; that is an interpretation of my wording, not a fact.
  (b) C9 — the coder reports every section already went through `run_section` before this task,
  which contradicts `scout`'s finding that the beamline block at `:4920` was unwrapped. If the
  coder is right, D-005's m9 was already closed and C9 adds the proof rather than the fix.
  **One of those two is wrong; the reviewer settles it against the base commit.**
- **Criteria:** C1 `{column, slotIndex}` shape, empty list refused; C2 both pointer gestures
  plus a keyboard-only path; C3 64/13/51 through the reference-executed allowlist, helpers
  reused not re-transcribed; C4 22-of-22 off the shared inventory; C5 the bench sweep's own
  three widths plus D-008's six floors, reusing the three check functions; C6 the terminal plot
  node budgeting D-003's fixed 650×460 at 768; C7 unflagged `file://`; **C8 closes D-005's m4**
  — launch-flag ban asserted by `ast` in the harness, a regex explicitly ruled insufficient;
  **C9 closes D-005's m9** — every `all_results.append` must come from `run_section`. Each is
  mutation-gated with a transcript pair. Told explicitly **not** to create `board.js`.
- **Floors handed to the coder as measurements, not quotes:** both `verify.py` counts are to be
  taken on the merge-base and on HEAD with the same command and both pasted. The recorded
  "46 sections / 149 assertion lines / 121 non-bench" figure has an unrecorded command behind
  the 149; `scout`'s `grep -c 'results.append\|line('` gives **177**. **Reconcile at review —
  do not treat 149 as authoritative until the command that produced it is known.**


- D-008's six simultaneous palette floors: min CVD ΔE **5.129** (≥4.0), normal-vision node-node
  **14.170** (≥14.0), node-vs-reserved **13.442** (≥4.0), white-on-fill **4.595:1** (≥4.5),
  fill-vs-reserved hue gap **14.1°** (≥12.0°), clamping excess **+0.0051** (≤0.01).
- `verify.py` on `main` as of `4720179`, measured by the reviewer at cycle 3: **46** registered
  sections / **149** assertion lines, of which **121** are non-bench. A fall in any is `Required`.
  The historical "31 / 48" figure is D-008's own claim and does **not** reproduce; reconciling it
  is backlogged. Exactly two assertion lines changed between cycles 2 and 3 — C9's strengthening
  and the intended `3 → 2` prose-lint denominator — machine-diffed by the reviewer, every other
  integer in the suite unchanged.

## Process note — D-005 was merged before its gate ran (RESOLVED)

`4720179` landed on `main` at **2026-09-01T08:23:27Z**, ~12 minutes before I dispatched the
cycle-3 reviewer. **The user merged it themselves, by hand, having judged cycle 3 finished** —
confirmed by them 2026-09-01. Legitimate, and not a rule-5 breach: rule 5 binds the agents, not
the person who owns the repo. Closed, no action. The gate ran afterwards and returned
`0R / 0M`, so what is on `main` is what a clean review would have approved anyway.