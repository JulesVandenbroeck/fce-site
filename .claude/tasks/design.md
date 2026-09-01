# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

### D-007 — Comparison index and the recommendation
- **Scope:** `docs/design-explorations/index.html`, `index.css` (**added to scope 2026-09-01 on the
  user's ruling** — no legal place for CSS otherwise; the D-001 precedent gave its index one too),
  `docs/design-explorations/README.md`, plus a two-line superseded note at the top of
  `docs/wireframes/README.md`. No page files, no `tokens.css`, no `verify.py`.
- **Accept:** C1 the index links exactly the three style pages, offline-standalone, no `<script>`;
  C2 each `<section id>` states what that style's graph persists; C3 the gesture named per style
  matches that page's own style tag; C4 the README carries `## Recommendation` with exactly one
  `**Recommended:**` line, the persisted shape it commits, and `### ` per style under
  `## What each option gives up`; C5 the wireframes note is ≤3 insertions / 0 deletions and the
  diff is exactly the four scoped files; C6 `verify.py` grep counts and red-set identical to
  `main`. C2 and C3 are mutation-gated. **checks=6.**
- **Depends on:** ~~D-004~~ (`bac2f62`), ~~D-005~~ (`4720179`), ~~D-006~~ (`0aee604`) — all merged.
- **Branch / PR:** `task/d-007-index` — **#21**, `71c6022`. `design-coder`, worktree, effort high.
- **Status:** **re-specification in flight (NOT cycle 2).** Cycle 1 = PR #21 `71c6022`, gate
  reproduced all 6 (verify.py exit 1, 265 assertions, only `board-lane-fill` red). Reviewed
  `0R / 1M / 3m`, scope pass. **M1 is my defect:** C4's second half — "names `docs/api.md` /
  `POST /api/run` as what the shape commits" — shipped with *"quote the lines in the PR body"*
  instead of a `Check:`, and that unfalsifiable half is the one that failed. §5.4 clause 2 →
  re-specification, does not count against §5.7. The README argued Board's `{column, slotIndex}`
  "is what `POST /api/run` actually carries"; `docs/api.md` marks `/api/run` **to be defined in
  M3** with no request body. Re-dispatched with **C7**: any `docs/api.md` claim in
  `## Recommendation` must also state the endpoint is unspecified, mutation-gated by restoring
  the false sentence. **checks=6 → 7.** The coder may change the recommendation if the honest
  argument no longer supports Board.
- **Review:** m1/m2/m3 all **backlogged and named individually** (index.css top-rule tokens on the
  wrong axis; the C2/C3 gate living only in the PR body; the unnamed `<section>` landmark).
  Backlog 76 → 79.
- **Gate defect found and fixed 2026-09-01:** C5's `git diff main --name-only` (two-dot) returned
  **seven** files at the re-spec gate, because I had committed bookkeeping to `main` twice while
  the task was in flight. Three-dot `git diff origin/main...HEAD` returns the correct four. The
  coder's work was never out of scope; my command was. Lesson written into
  [`orchestrator/CLAUDE.md`](../orchestrator/CLAUDE.md) §2.
- **Re-spec gate reproduced at `19bc819`:** scope exactly 4 files (three-dot), C1 hrefs exact,
  C4 `1/1/3/1` (**Recommended: Board**, unchanged), C7 exit 0 with hedges `to be defined` /
  `undefined` / `M3` present and no present-tense carry-claim, C6 greps 69/233. `verify.py` and
  `tokens.css` **byte-identical to `main` by blob SHA**, and the only file changed since the
  reviewed head is `README.md`, which `verify.py` never opens — so C6 holds by identity.
- **Re-spec reviewed at `19bc819`: `0R / 1M / 0m`, scope pass. M1 fixed and mutation-verified.
  M2 is NEW and is M1's defect one citation over** — the rewritten lede claimed
  `docs/design-brief.md` §4 "poses a question" about the run payload's `ui` object that §4 does
  not pose; `design-brief.md:51-54` in fact names **"slot indices"** as layout state *the engine
  ignores*, which leans against Board's differentiator rather than for it. §5.4 clause 3: C7 was
  met and **no criterion ever gated design-brief citations**, so this is the coder's ordinary-craft
  miss, not my brief. **CYCLE 2** (the re-spec did not consume one). Review posted:
  PR #21 comment `5498754050`.
- **Cycle 2 dispatched with C8:** every claim the README attributes to another document must be
  supported by it — quoted spans verbatim (ellipsis-aware), cited `§n` sections must exist —
  mutation-gated by altering one word inside a quotation. **checks=7 → 8.** C8's stated limit is
  written into the dispatch: it checks *quotations*, and cannot catch a *paraphrase* that
  misrepresents a source, which is precisely what M2 was; the coder must therefore table every
  characterising sentence with its supporting `file:line` for the reviewer to check by hand.
- **At cycle 2 of 3.** If cycle 3 does not close `0R/0M`, escalate to the user — no cycle 4.
- **CYCLE 2 DELIVERED `1e9b369`, GATE FULLY REPRODUCED 2026-09-01 — NOT YET REVIEWED.**
  Scope (three-dot) exactly the 4 files; only `README.md` changed since `19bc819` (27+/20-).
  C1 hrefs exact, no script/http. C4 `1/1/3/1`, **Recommended: Board** unchanged. C5 wireframes
  `2 0`. C6 greps 69/233 and `verify.py` blob-identical to `main` (`d3fc619b`). Sections carry
  `id="beamline|bench|board"` (plus `class="cmp-card"`). **C8 re-verified independently: all four
  document quotations are verbatim once whitespace is normalised** across README line-wraps —
  `"Any layout state … lives in a separate \`ui\` object the engine ignores."` and
  `"It still reads as a pipeline."` in `design-brief.md`, `"_To be defined in M3._"` in `api.md`.
  `README:58`'s `"these two belong together"` is the README's own prose, not a citation.
- **M2's substance held but the REVIEWER'S LINE NUMBERS WERE WRONG.** It cited
  `design-brief.md:43-44` and `:51-54`; those are unrelated text. The true lines, verified at the
  gate, are **`:168`** ("3. **It still reads as a pipeline.**") and **`:176-179`** (the
  `ui`-object / "slot indices" passage). The coder used the correct ones. Do not propagate the
  reviewer's figures.
- **The cycle-2 fix concedes the point rather than dodging it:** the lede now states outright that
  §4 does *not* pose this as a question and *does* classify `column`/`slotIndex` as ui state the
  engine ignores, then re-grounds Board on the requirement §4 states outright. Recommendation
  unchanged.
- **NEXT MOVE: dispatch `code-reviewer` on PR #21, effort medium, PR number + prior review URL
  only.** The §5.1 gate is already done and passed — do not re-run it. Prior review:
  PR #21 comment `5498754050`. Ask for `M2 fixed` / `M2 still open`, all 8 criteria re-run,
  incremental diff since `19bc819` (one file), and an independent check that the design-brief
  citations resolve — that is the class of defect this task has produced twice.
- **This is the M1 checkpoint** — the user picks Beamline / Bench / Board from it, and that choice
  unblocks D-002. Preview worktree: `~/d007-preview` (detached, under `$HOME`, never `/tmp`).
- **Enumerated 2026-09-01, not inherited:** `verify.py` registers **65** sections, **64** pass,
  `board-lane-fill` is the only red, `--all` exits 1. `grep -c 'all_results.append'` = **69** (4 are
  comment mentions), `grep -c 'results.append\|line('` = **233**. It hard-codes its four page
  paths (`verify.py:83,89,92,95`) and globs nothing, so a new `index.html` in that directory is
  invisible to it. **`SESSION.md`'s "63 sections" was stale; 65 is right.**

## Ready

_none._

## Blocked

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

#### Constraints the node-graph tasks established

The one axis CSS cannot swap is **what the graph persists**, and it is what later lands in
`POST /api/run`: **A · Beamline** ordered edge list only; **B · Bench** `{x, y}`;
**C · Board** `{column, slotIndex}` — the only one where the plot lives inside the graph as the
terminal node. What D-003 hands all of them: the figure is a **fixed intrinsic 650×460** CSS px
and does not reflow; harvest the **cycle-4** `--tab10-x2`/`--tab10-x3` values; `--ink-45` is
2.60:1 and not text-safe. Fuller case for each style: [`archive/design.md`](archive/design.md).

## Done

One line per task. Full entries in [`archive/design.md`](archive/design.md).

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
