# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

### D-004 — Three node-graph styles
- **Scope:** `docs/design-explorations/` — `index.html`, `{beamline,bench,board}.{html,css,js}`,
  `README.md`, extend `tokens.css` and `verify.py`; plus a two-line superseded note at the
  top of `docs/wireframes/README.md` and nothing else outside the new directory.
- **Accept:** (1) persistence model differs per page and is inspectable in the DOM;
  (2) connection interaction differs per page and is driven by real Playwright gestures —
  Beamline accepts click and rejects drag, Bench the reverse, Board both plus keyboard;
  (3) all 121 ordered node-type pairs attempted per page, 0 illegal accepted, 0 legal
  refused; (4) every domain-inventory item present per page via `data-wf`, 0 missing, plus a
  locked node type present-but-inert; (5) full sweep at three widths with denominators.
- **Depends on:** D-003 — **cleared 2026-08-17**, merged as `99ec8f3`.
- **Status:** **dispatched 2026-08-17, stopped by the user before any commit.** Branch
  `task/d-004-node-graphs` exists at `c86981c` (= `main`, no commits). No PR. Partial work
  survives **uncommitted** in the agent worktree
  `.claude/worktrees/agent-aabe0d4da7ede4df9` — a single 41-line addition to
  `docs/design-explorations/tokens.css`. That worktree has changes, so it will not be
  auto-cleaned; do not remove it without reading the diff first.
- **CRITERION 3 IS WRONG, AND THE ERROR IS THE ORCHESTRATOR'S.** It says "all **121** ordered
  node-type pairs attempted per page". 121 implies 11 node kinds. The reference has **8
  concrete kinds**, so the real figure is **64 ordered pairs**. The number was inherited from
  this entry's original wording and was never grounded in anything.
  **Verified against source by the orchestrator, not taken from the agent:**
  - `fce-project/fce/ui/graph.py:163` — `_VALID_CONNECTIONS` has **9** keys: `DataSource`,
    `Multiplicity`, `Selection`, `Observable`, `ObsGlobal`, `ObsObject`, `ObsVectorSum`,
    `ObsCustom`, `Histogram`.
  - `fce-project/fce/ui/state.py:35` — `NODE_LABELS`, the same 9.
  - `fce-project/fce/fce.py` — `create_node("...")` is called for exactly **8** of them.
    **Bare `"Observable"` is an allowlist key that is never instantiated**, so it is a
    grouping, not an addable node kind.
  So: 8 addable kinds → 64 ordered pairs; 9 keys including the abstract one → 81. Neither is
  121. **Fix the criterion before this is re-dispatched**, and state which of 64 or 81 is
  wanted rather than leaving the coder to choose.
- **The stopped agent found this by reading `ui/graph.py`** instead of trusting the dispatch,
  and encoded it in the tokens.css comment before it was stopped. That is the behaviour the
  four verification rules are meant to produce, and it worked on the first try here.
- **The other thing its partial work settles:** the node-type palette. 8 hues, each paired
  with white node-title text and claimed to composite at >= 4.5:1, plus a `--locked-fill`
  that is desaturated rather than merely lighter, with its label on full `--ink` because
  `--ink-70` over that fill measures 4.30:1 — below the 4.5:1 floor. **Those contrast numbers
  are the coder's own and have been verified by nobody**; `verify.py`'s D-004 contrast
  section, which was to have measured them, was never written.
- **Size risk, recorded before the next attempt:** this task is 12 files and three
  interactive prototypes, well past the orchestrator manual's own splitting test (§2, "more
  than about three files, suspect it is really two tasks"). D-003, a smaller task, took four
  cycles. If a re-dispatch thrashes, split it — one page per task, with `tokens.css` and
  `verify.py` extended by the first and only read by the others — rather than spending cycles.
- **The three, pushed apart on what the graph persists** — the one axis CSS cannot swap, and
  the thing that later lands in `POST /api/run`:
  - **A · Beamline** — auto-laid rail, persists an ordered edge list only, click-to-connect,
    colour on node chrome. Best 768 story; gives up all arrangement agency.
  - **B · Bench** — free canvas, persists `{x, y}`, drag-to-connect, colour on the wires.
    Its real cost is not the drag — the plot inspector always occludes the graph, so cut and
    consequence are never co-visible. Framed as the *sandbox-mode candidate*.
  - **C · Board** — typed columns with slots, persists `{column, slotIndex}`, both gestures
    plus keyboard, colour on the columns. **Recommended:** the only one where the shape of
    the page changes per mission (columns appear as missions unlock) and the only one where
    the plot lives *inside* the graph as the terminal node.
- **What D-003 hands it, and it is not just a file to import:**
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
- **Branch / PR:** not yet opened

## Ready

_none_

## Blocked

### D-002 — Design token foundation
- **Scope:** `src/fce_web/static/css/tokens.css`, `src/fce_web/static/fonts/`
- **Accept:** every colour, spacing, type-scale, radius, and timing value defined as a
  custom property; the palette committed with measured AA contrast ratios documented in the
  file; self-hosted woff2 fonts, no CDN; a chosen serif and mono that are explicitly not
  Inter/Roboto/system-ui/Space Grotesk
- **Depends on:** ~~D-001 and the user's D-001 layout decision~~ — **blocker changed
  2026-08-16.** Now blocked on the user's choice among Beamline / Bench / Board at the D-004
  checkpoint, with `docs/design-explorations/tokens.css` as its input rather than a blank
  page. Left pointing at the old blocker it would read as waiting on something extinct.
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

### D-003 — Interactive plot component at reference parity
- **Scope:** `docs/design-explorations/` — `plot.html`, `plot.css`, `plot.js`, `frame.css`,
  `tokens.css`, `payload.json`, `verify.py`. Nothing under `src/`, `tests/` or `content/`.
- **Branch / PR:** `task/d-003-plot-component` — #5 (7 files, +3249)
- **Scope:** `docs/design-explorations/` — `plot.html`, `plot.css`, `plot.js`, `frame.css`,
  `tokens.css`, `payload.json`, `verify.py`. Nothing under `src/`, `tests/` or `content/`.
- **Accept:** (1) `verify.py --plot` prints each named anatomy feature present/absent from
  the DOM; (2) figure `getBoundingClientRect` reported as measured numbers at 1440/1024/768
  against a floor; (3) cutflow figure complete, efficiency-% count = stage count; (4) full
  computed-style sweep with denominators at all three widths, including `fill` and `stroke`;
  (5) `git diff --stat -- src/ tests/ content/` empty.
- **Depends on:** nothing. Dispatched alone — the figure's real minimum dimensions constrain
  where every D-004 style can put it, so guessing costs a cycle later.
- **Why it exists:** the user ruled for full parity with the reference python figure
  (`fce-project/fce/engine/plotter.py`), ratio panel included. That ruling was then narrowed
  twice by the user's own later rulings — see the deviation list below.
- **Status: done (4 cycles, 3 reviews) — merged as `99ec8f3`, on the user's explicit
  override, with the `Required` finding open.**
- **Resolution — the second deliberate exception to orchestrator §5, and it must not
  generalise.** The user was shown the finding, shown that the fix was a one-character change
  to a constant (`<= 8` → `<= 9`) that the reviewer had already proved lands on the
  reference's exact tick step, shown the alternative of un-ticking the criterion and ruling
  the tick step a deviation, and shown the orchestrator's written advice **against** merging
  as-is. They chose to merge anyway. Recorded here because the rule is otherwise absolute and
  a silent exception would corrode it.
  **What this leaves false, stated plainly:** PR #5's criterion 1 reads "main-panel y-limits
  **and major ticks** match the reference" and is ticked. The limits match to 0.05%; the
  ticks are step 2000 against the reference's 1000. The tick is wrong and stays wrong in the
  merged record.
  **Grounds, such as they are:** `docs/design-explorations/` ships nothing and no application
  file imports it; the defect is a coarser tick grid on an exploration figure, not a physics
  or accessibility error; and the finding is in `backlog.md` with its reproduction and its
  one-line fix. **This does not extend to `src/`, `tests/` or `content/`** — nor, note, to
  `tokens.css`'s *values*, which D-002 harvests and which were therefore fixed rather than
  merged wrong.
- **The cycle-4 review that produced this finding is recorded below.** Head at merge
  `4ed75d8`. Four coder passes, three reviews; already past §5's limit and running on the
  user's cycle-4 tie-break, so the orchestrator escalated rather than extending it.
- **Everything else in the review passed independent re-verification** — see below. The
  merged figure renders the Z peak at 92.6% of panel height (from ~40%), which is the change
  this task existed to make.
- **Review, cycle 4 — and it corrected the previous review, which is the headline.**
  - *Required* — `plot.js:106`. Criterion 1 ("main-panel y-limits **and major ticks** match
    the reference") is ticked but only half met. Limits match to 0.05% (8630.71 vs 8635.47);
    the major ticks do not — reference **step 1000**, this SVG **step 2000**. The PR body and
    `verify.py:497-500` describe this as an irreducible approximation artefact. **It is not:
    it is the hard-coded cap in `if (max / step <= 8)`.**
  - **Orchestrator verified this directly rather than trusting either reviewer, because the
    two reviews disagreed.** Cycle 3 reported reference majors `[0, 2000 … 8000]`; cycle 4
    reported `[0, 1000 … 8000]`. Running matplotlib's own `AutoLocator`: for ylim `0..8635.47`
    **and** for `0..8391`, it returns **step 1000** in both cases. **Cycle 4 is right and
    cycle 3's sub-claim was wrong** — though cycle 3's headline (peak at ~40% of panel) was
    correct and is what mattered. Arithmetic on the live constant: `8630.71 / 1000 = 8.63`,
    rejected by `<= 8`, so it falls to step 2000; at `<= 9` it accepts 1000 and matches.
  - *Suggested-major* — `plot.js:87,103-108`: three of the five ladder rungs are unreachable,
    so the comment's "keeps the same five-multiplier ladder" describes code that does not
    exist. **Confirmed by the orchestrator:** `magnitude = 10^floor(log10(max))` forces
    `max / magnitude ∈ [1, 10)`, so `s = 1` returns whenever the ratio clears the cap and
    `s = 2` always returns otherwise (ratio/2 < 5); `2.5`, `5`, `10` and the fallback at
    line 108 are dead under either cap. This is *why* the axis can only ever land on 1× or 2×
    magnitude, so the next person to tune it will mis-diagnose it the same way.
  - *Suggested-minor ×4* → backlogged.
  - **What this review verified rather than assumed:** scope (7 files; cycle 4's diff exactly
    the 5 named), 89 PASS reproduced, flake8 clean, 26 pytest passes, **its own independent
    reference render** reproducing the PR body's numbers to the digit, its own DOM probe
    (`peakFrac 0.9259`), a fresh `resampled(3)` run matching `tokens.css`, both suggested-major
    fixes driven for real (reveal does not replay; Enter and Space on bin 5 both set the
    readout), the palette toggle proven CSS-only by byte-comparing `#hist-svg` outerHTML
    across the click, 146 text elements contrast-swept, and the new prose lint **run against
    the pre-fix commit** — 8 matches, exactly the 8 claimed.
  - **The instrument held this time.** Cycles 1 and 3 both found the checker defective; cycle
    4's checker was independently re-run and its new assertions confirmed non-vacuous.
- **Cycle 4 — both required findings answered within the ruling.** `verify.py --all` →
  **89 PASS, 0 FAIL**, exit 0; flake8 clean; `git diff --stat main...HEAD -- src/ tests/
  content/` empty. Scope held at exactly the 5 files named for this cycle (`git diff
  --name-only 4d4f4e4..4ed75d8`); `frame.css` and `payload.json` untouched as instructed.
  - *y-scale fixed at the root cause.* `plot.js:100-109` — `niceCeilingAndStep` headroom
    `1.35 → 1.08`, and it no longer rounds the axis top to a "nice" ceiling. **Peak fill goes
    ~40% → 92.6% of the main panel.** Checked the way the criteria demanded: the reference
    was rendered from this `payload.json` through `plotter.py` itself (via a faked-`uproot`
    adapter, matplotlib 3.11.0 / mplhep 1.3.1) giving peak fill **0.9254**, against the SVG's
    **0.9259** — within 0.1 point, two independently produced numbers rather than one.
  - *Mutation-tested.* Reverting to the pre-fix ladder makes both new assertions fail with
    `this SVG: 0.400` / `this SVG: 20000`; restored byte-identical, both pass.
  - *tab10 corrected.* `--tab10-x2`/`--tab10-x3` set from a fresh
    `colormaps["tab10"].resampled(3)` run, not copied from the dispatch — the fix and its
    verification do not share a hand. **D-002 must harvest these values, not cycle 3's.**
  - *Counted claims replaced by a lint.* `EXHAUSTIVE_CLAIM_PATTERNS` extended to catch
    counted-exception phrasing, shown catching the pre-fix wording (**8 matches → 0**). The
    rulings panel now lists all five deviations without counting them. This is the first time
    the D-001 failure class has been turned into a check rather than a promise.
  - *Both suggested-majors fixed, neither overruled.* The reveal now arms once per figure
    (`armReveal()`), so flipping between histogram and cutflow no longer costs ~1.6 s each
    way; the 40 bin hit-areas gained real `click`/Enter/Space activation matching the
    `role="button"` they already advertised.
- **Reported rather than left silent, per the dispatch:** the y-scale fix did **not** close
  the x-major-spacing deviation — `xMajor` is a separate hardcoded constant in `plot.js`,
  untouched by `niceCeilingAndStep`. So x spacing remains a ruled deviation.
- **Declared deviations, cycle 4.** (1) The coder could not check out
  `task/d-003-plot-component` in its worktree — the branch was held by a stale sibling
  worktree and `git worktree remove` was blocked by its sandbox — so it worked on a local
  branch tracking the same remote ref and pushed to `task/d-003-plot-component`. Same remote
  branch, same PR, no second PR. **The orchestrator has since removed that stale worktree and
  fast-forwarded the local ref to `4ed75d8`.** (2) PR title edited again, because the old one
  itself carried a count ("two ruled exceptions") that this cycle outgrew. (3) The reference
  render adapter `render_reference.py` is not committed — outside the five-file scope — and is
  reproduced in the PR body instead.
- **The user's tie-break, 2026-08-16: fix the y-scale and the colours only.**
  - *Fix:* the y-axis (a real visual defect — the Z peak renders at ~40% of panel height)
    and the tab10 X2/X3 values (a factual error that **D-002 would inherit**).
  - *Accept as further user-ruled deviations:* the ratio panel's missing `xerr` bin-width
    bars, the main panel's 31 bottom tick marks, and the x major spacing. These join legend
    placement and sample colour as things this figure knowingly does differently.
  - *Not chosen:* full parity repair, and dropping parity as the governing rule. Parity still
    governs the anatomy; the deviation list is now longer than the figure's own prose claimed.
  - **Coupling the dispatch names explicitly:** x major spacing and the y-scale come from the
    *same* tick-step algorithm (`plot.js:62-73`), so fixing y may correct x for free. The
    coder is told to report which, not to hold x wrong on purpose.
- **The instruction that matters most in cycle 4, and it is a D-001 lesson:** the figure's
  prose must **list** its deviations and never **count** them. "Two named exceptions" is what
  made Required 1 a finding rather than a footnote — the claim was falsifiable by arithmetic
  the moment a third was found. No counts, no "exhaustive", no "only". D-001 burned four
  cycles on exactly this shape.
- **Review, cycle 3 — the first review that checked parity against the reference itself.**
  Cycle 1's reviewer declared it *could not*, because the engine is not vendored here. This
  one found `fce-project/fce/engine/plotter.py` outside the repo, rendered it **from this
  exact `payload.json` through the reference's own code path**, and diffed against the SVG.
  So these are new findings on new ground, not the same finding recurring — the D-001
  failure mode is **not** what is happening here.
  - *Required 1* — the anatomy-at-parity claim, which explicitly names "ticks", is false in
    four further respects. **Independently confirmed by the orchestrator against
    `plotter.py` source, not taken on the reviewer's word:** `plotter.py:84` sets
    `tick_params(axis="x", bottom=False, labelbottom=False)` on the main panel while the SVG
    draws 31 bottom tick marks; `plotter.py:169` passes `xerr=widths / 2` while the SVG has
    0 horizontal ratio error bars. The reviewer additionally measured main-panel y-limits
    `(0, 8391)` with majors `[0, 2000, …, 8000]` against the SVG's `0–20000` / `0,10000,20000`,
    and x majors `0/50/100/150` against `0/25/…/150`.
    **The y-scale one is a real visual defect, not merely a false sentence:** the Z peak
    fills ~40% of the panel instead of ~95%. Root cause named at `plot.js:62-73` — the
    `steps` ladder starts at `1 * magnitude` and can never select the reference's 2000 step.
  - *Required 2* — `tokens.css:57-65`, `plot.html:93-102` claim the tab10 triples are
    "exactly what the reference assigns". **Confirmed false by the orchestrator running
    matplotlib directly:** `colormaps["tab10"].resampled(3)` → `#1f77b4, #8c564b, #17becf`;
    the file carries `#1f77b4, #ff7f0e, #2ca02c`, which is `tab10(0),(1),(2)` unresampled.
    X2 and X3 are wrong. **D-002 harvests this file**, so it would inherit the error.
  - *Suggested-major* — `plot.css:170-205`: the reveal animation re-fires on every tab
    re-show, because the switcher toggles `display`. Measured ~1.6 s before the figure
    settles, **each way**, for a student flipping between histogram and cutflow to compare.
    `verify.py` accommodates it with `wait_for_timeout(1700)` rather than flagging it.
  - *Suggested-major* — `plot.js:370-391`: the 40 bin hit-areas still carry `role="button"`
    with only hover/focus handlers, so a screen reader announces 40 buttons that do nothing
    on Enter. Raised as minor in cycle 1 and backlogged; it is now major because the readout
    is `aria-live` and the mismatch is load-bearing.
  - *Suggested-minor ×3* → backlogged.
  - **What the review verified rather than assumed:** scope (7 files, nothing under `src/`,
    `tests/`, `content/`), `87 PASS` reproduced exactly, 49 pytest passes, flake8 clean, its
    own Playwright legend measurement at three widths, **its own mutation of the legend
    assertion** (moved the legend inside → FAIL, as the coder claimed), and **its own
    mutation of the contrast probe** (widened the legend swatch so labels sit on the fills →
    `6 of 114 on solid fill, 4 below AA`, catching ink-on-vermillion at 2.76:1). The coder's
    two new checks are therefore confirmed non-vacuous by someone other than their author.
  - **Not treated as a finding:** the out-of-scope PR *title* edit — metadata, not a file,
    disclosed, and in the spirit of criterion 4. The orchestrator had already accepted it.
- **Cycle 3 was delivered and reviewed as follows.** The cycle-2
  *review was never dispatched* — the previous session recorded "back in review" and was
  interrupted before the reviewer ran, so cycle 2 was verified by its author and by nobody
  else. **This review therefore covers cycles 2 and 3 together**, and the PR body was
  rewritten to carry both cycles' evidence.
- **Cycle 3 — both rulings applied.** `verify.py --all` → **87 PASS, 0 FAIL**, exit 0
  (83 → 87: the new `legend-layout` section adds three widths plus a summary line);
  `flake8` clean; `git diff --stat main...HEAD -- src/ tests/ content/` empty. Scope held
  at exactly the 7 files (`gh pr diff 5 --name-only`).
  - *Legend outside the axes.* `FIG.w` 480 → 650; the legend is now a sibling of
    `.panel-main`/`.panel-ratio` drawn at `axesRight + legendGap`. Measured
    `rightOfAxes=True, noOverlap=True` at all three widths; figure 650×460 against a derived
    floor of 416×454; body horizontal overflow `False` at 768.
  - *The assertion was made falsifiable, and shown to be.* Two independent mutations —
    structural (legend back inside `.panel-main` → "legend not found") and geometric-only
    (kept as an `svg` child but at the old inside-axes coordinates → `rightOfAxes=False` at
    all three widths) — each failed, each reverted, then 87 PASS restored. This is the
    direct answer to the cycle-1 `Required` finding's *class*, not just its instance.
  - *Frozen palette is the default.* `<body data-palette="frozen">`, X1 on vermillion,
    tab10 still reachable through the toggle, repaint by CSS alone.
  - *Parity claims swept.* `grep -rn "parity"` over all 7 files, every hit read by hand;
    remaining instances scope the claim to anatomy or name the two exceptions.
- **Coder found and fixed a real pre-existing bug in its own checker, unprompted** — and
  this is the second cycle running in which the checker, not the page, was the defect.
  `check_contrast` measured SVG text through the inherited `color` property rather than the
  `fill` that actually paints it, and it swept only the visible tab, silently scoring the
  hidden one against a collapsed `(0,0,0,0)` rect. Post-fix: **114** text-bearing elements
  checked (up from 71), 0 on a saturated fill, 0 below AA.
- **Declared deviation, accepted by the orchestrator:** the coder also changed the PR
  **title** — `"…at reference parity"` → `"…(anatomy at parity; two ruled exceptions)"` —
  which was outside the stated scope of "the PR body". The argument is right: the title was
  the single most visible unqualified parity claim on the branch, and correcting every
  instance except the one at the top would have defeated the criterion. No file touched, and
  it was flagged in the PR's own deviations section rather than done quietly.
- **The user's two rulings, 2026-08-16 — both settled at the checkpoint.**
  1. *Legend placement:* **outside the axes.** Not the coder's recommendation, which was to
     keep parity and defer. The legend is to move to the right of the plot area so it never
     occludes the Z peak, at all three widths.
  2. *Sample colour mapping:* **frozen per-sample map, X1 pinned to vermillion** — the
     coder's recommendation, taken. Both schemes stay wired via `data-palette`; only the
     default flips.
- **These rulings narrow the D-001 pivot's "full plot parity" ruling, and that must not be
  lost.** Parity remains the rule for the figure's anatomy — panels, ratio, ticks, frame,
  stacking, band, header. It now carries **two named exceptions, both user-ruled**: legend
  position and sample colour assignment. Any later claim that this figure is "at parity with
  `engine/plotter.py`" is false unless it names both. **B-004 and D-004 read this entry** —
  neither should re-derive parity from the pivot text alone.
- **Cycle-2 numbers, for the record, unverified by review:** `verify.py --all` →
  **83 PASS, 0 FAIL**, exit 0; `flake8 docs/design-explorations/verify.py` → exit 0. The
  legend anatomy assertion among those 83 asserts *inside-axes* and is expected to be
  rewritten by cycle 3, not merely to keep passing.
- **PR body was stale when cycle 3 was dispatched** — it still carried the cycle-1
  verification block (`76 PASS`, and the line `ink-45 on paper: 12.75:1`, which is the exact
  falsehood cycle 1 raised as `Required`). Since the PR is the reviewer's only context
  (orchestrator §4 rule 3), dispatching a review against it would have handed the reviewer
  evidence contradicting the code and invited a re-report of a fixed defect. Refreshing it is
  part of cycle 3's scope. Caught by reading the PR body rather than the task list.
- **Cycle 2 resolution — every finding fixed, nothing overruled.**
  - *Required, fixed.* `parse_rgb` → `parse_rgba` (keeps alpha), plus `composite_over` to
    alpha-blend foreground over its real background before computing luminance. Verified two
    ways rather than one: the coder re-injected **the reviewer's own exact failing rule** on a
    scratch copy and watched it now fail at 1.84:1 where it had silently passed; and the real
    page's numbers now match the reviewer's independent hand-recomputation to the decimal —
    `--ink-70` 5.18:1, `--ink-45` 2.60:1. **New fact the fix surfaced:** `--ink-45` is used by
    **0 elements**, so the live verdict is unchanged, exactly as the review predicted.
  - *Suggested-major 1, settled from source — this is the one that mattered.* The coder read
    `engine/plotter.py:89-125` rather than reasoning about it: `frac2` is seeded with
    `LUMI_UNC**2` alone and never combines an MC-stat term, so **the reference itself omits
    it**. `weightsSquared` is therefore genuinely dead for this band in both implementations —
    not a parity gap — and it is kept only because it is pre-existing fixed contract, now with
    a structural length check. `totalRaw` and `thresholds` *were* dead, and were made
    load-bearing rather than dropped: `totalRaw` is cross-checked against `efficiencyPct`, and
    `thresholds` now drives the Z readout's evidence/discovery text and its vermillion
    styling. **This is the answer B-004 needs, and it is now evidenced against exact line
    numbers rather than asserted.**
  - *Suggested-major 2, fixed, counter-argument deliberately not invoked.* The coder could
    have overruled on the `.flake8`-exclude argument I left open to it, and chose not to:
    cheaper to fix than to spend a back-end task on a carve-out nobody has asked for. All 53
    violations fixed, type hints and docstrings on every function per shared §6.
  - *Suggested-minor ×2, fixed.* The figure floor is no longer copied from `plot.js`'s own
    `FIG` constants — it is derived independently from a live DOM bin count against the
    task's stated 9 px/56 px minimums, so it is falsifiable now and lands at 416×454 against
    a measured 480×460, two different numbers rather than one. `check_git_diff` now runs
    `main...HEAD`.
  - The denylist limitation of the exhaustive-claim lint is now stated in
    `check_no_exhaustive_prose`'s own docstring rather than left for a reader to discover.
- **Owed to D-002:** `--ink-45` composites to 2.60:1 against paper and fails AA if ever used
  for text. Currently unused. Do not inherit it into the real token file unstated.
- **Review, cycle 1.** The reviewer mutation-tested the checker rather than reading it, which
  is the only reason the required finding exists — every one of `verify.py`'s 76 assertions
  passes, and one of them cannot fail.
  - *Required* — `verify.py:767`, `parse_rgb` matches `rgba?\((\d+),\s*(\d+),\s*(\d+)` and
    **discards the alpha channel**, so every translucent text colour is measured as if
    opaque. That is exactly the token family this palette uses (`--ink-70`, `--ink-45`).
    Demonstrated, not inferred: on a copy with `.fit-readout { color: rgba(43,38,32,0.30) }`
    — truly ≈1.9:1 — `verify.py` reported it passing. The PR body prints
    `ink-45 on paper: 12.75:1`; composited it is **2.60:1**, below AA. Criterion 4's "0 below
    AA" therefore rests on a check that cannot see the most likely way this palette fails.
    **No live failure today** — recomposited, `--ink-70` is 5.18:1 and `--ink-45` is declared
    but unused — so this is a broken instrument, not a broken page.
  - *Suggested-major* — `plot.js:281-302`, `payload.json:137`: the band combines `lumiUnc`
    with `systUp` in quadrature and never reads `weightsSquared`, so either the reference
    omits the MC-stat term too (making `weightsSquared` a dead field that should not be
    proposed as contract) or the band is not at parity. `cutflow.totalRaw` and
    `fit.thresholds` are likewise declared and never consumed. This is the finding that
    matters most, because **B-004 is about to land these field names.**
  - *Suggested-major* — `verify.py`: 45 flake8 violations under the repo's own `.flake8`
    (`F401`, 42×`E501`, 2×`E741`, `E203`); no type hints or function docstrings on ~30
    functions, against shared §6. The reviewer named the legitimate counter-argument itself:
    if `docs/` is outside the lint gate, `.flake8`'s `exclude` should say so — and that file
    is back-end owned, so it needs raising, not assuming.
  - *Suggested-minor ×6* → backlog, except two the coder was asked to fix in this pass
    because they are about the honesty of the checker itself: `verify.py:649` hard-codes the
    floor to the figure's own fixed size so `meets_floor` cannot fail, and `verify.py:965`
    runs `git diff` with no revision, comparing worktree to index rather than the branch.
  - **What the review independently confirmed rather than took on trust:** scope compliance
    (`gh pr diff 5 --name-only` = exactly the 7 files), 49 pytest passes, its own Playwright
    audit at three widths with **alpha-composited** contrast over 76 + 52 elements finding 0
    below AA, screenshots examined for real, the palette toggle repainting via CSS alone
    (`.sample-x1` → `rgb(192,57,43)`), and a CDP accessibility tree showing all 40 bin nodes
    announcing with full labels. It also mutation-tested three of the checker's other sweeps
    and found them genuinely sound (paint 32 violations caught, focus 41 of 43 caught,
    reduced-motion 18 caught).
  - **One limit the reviewer declared:** it could not compare against `engine/plotter.py`,
    because the reference engine is not vendored into this repo yet. Anatomy is verified
    against the rendered DOM only. Worth knowing — parity to the *reference* is currently
    asserted by the coder and checked by nobody.
- **Coder reports:** `verify.py --all` → 76 PASS, 0 FAIL, exit 0. Anatomy read from the live
  DOM, 3/3 sections. Paint sweep 0 violations over 5158 property reads per width across 9
  properties including `fill`/`stroke`. 71 text elements contrast-checked, 0 below AA. Tab
  walk 43 stops, 43 with a visible ring. 18 reveal-animated elements, 0 still animating under
  reduced motion. 0 non-local requests, 0 console errors. `git diff --stat -- src/ tests/
  content/` empty.
- **PR body checked before dispatching review** (orchestrator §4 rule 3): carries the task ID,
  goal, verbatim scope, verbatim criteria each marked with evidence, and the real verify
  output. Stands alone.
- **Declared deviations, for the reviewer to weigh independently:** data marker `r=3` CSS px
  rather than a literal `markersize=4`; "black" furniture uses `--ink` not `#000`, per the
  token rule; the figure is a **fixed intrinsic 480×460** rather than responsive; `frame.css`
  is ~142 lines rather than ~120 after the token rewrite.
- **Two rulings owed to the user at the checkpoint, built but not decided** — both live in
  `plot.html`'s open-questions panel:
  1. *Legend placement.* Parity ships (framed, inside, upper-right) at all widths. Measured at
     1024: legend 152×85 against a 412 px plot area, 36.9% of axes width, over the Z peak.
     Coder's recommendation: keep parity as default, add an outside-axes position for narrow
     embeddings later.
  2. *Sample colour mapping.* Both wired for real via `data-palette` on `<body>`, CSS-only
     switch. Coder's recommendation: **frozen** per-sample map, X1 pinned to vermillion —
     X1 changing colour between missions is a teaching bug. Breaks parity with the reference.
- **Backlog candidates raised:** hover readout + legend sample-toggle (design-brief §5, not
  built); a sub-768 legend reflow; the reference's green "Discovered:" badge.

### D-001 — Wireframe exploration: mission screen and recipe builder
- **SUPERSEDED 2026-08-16 by the user's design pivot.** All ten options were drawn under
  constraints that no longer hold. `docs/wireframes/` is kept as the record of a decision
  that really was made; it is not current, and it will not be reopened — its one open
  `Required` finding is therefore permanently parked. The replacement work is D-003 + D-004
  in a fresh directory, `docs/design-explorations/`.
  **What changed, and the user's four rulings:**
  1. The site pivots to a **game-style interactive node graph** — nodes connected, added and
     removed. The graph **replaces the recipe-card stack entirely**; card types become node
     types. D-001's Card Stack recommendation is dead, as is Notebook Spread.
  2. **Ground stays light.** Warm paper survives. The one-rationed-vermillion-accent rule
     does not — saturated colour now encodes node type, sample identity and lock state.
     Vermillion alone stays held back.
  3. The three new wireframes **differ on connection interaction** — one click-to-connect,
     one drag-to-connect, one both.
  4. **Full plot parity with the reference python figure**, ratio panel included.
  `docs/design-brief.md` §4, §7, §8 and `.claude/design/CLAUDE.md` §2–3 were amended to
  match, each carrying a dated note, because the pivot reverses text those files stated as
  committed — `design-brief.md:150` said in terms that the node canvas was *not* a V1 goal.
  Two things from D-001 survive the pivot and should be carried into D-003/D-004: the
  domain inventory (every UI element the mission screen must hold), and the two
  verification rules extracted from its four failed cycles — see D-003's dispatch.
- **Scope:** `docs/wireframes/` (output only — no application files)
- **Accept:** `/wireframe` run for both the mission screen and the recipe-card builder;
  options explore genuinely different information architectures, not restyles of one
  layout; each is annotated with what it optimises for; a recommendation is stated with
  reasoning. **Output goes to the user for a decision — this is an M1 checkpoint.**
- **Depends on:** nothing
- **Branch / PR:** `task/d-001-wireframes-clean` — #2
- **Status:** **done** (4 cycles) — merged as `b580729`, on the user's override; the full
  resolution is at the end of this entry. What follows is the cycle-by-cycle record.
- **Cycle 2 rework** — done and pushed, though the list said otherwise until a later session
  checked git rather than trusting it. Commit `6457911` addresses the
  suggested-major and two of the minors: `base.css` body drops the named
  `-apple-system/BlinkMacSystemFont/Segoe UI` stack for the generic `sans-serif` keyword,
  making the PR's stated "no type decision has been made" premise true; `.tab-btn` gains
  `font: inherit`, so every element on all three pages now computes to one of exactly two
  `font-family` values instead of falling back to the UA default; `README.md`'s palette is
  replaced with the exhaustive twelve-grey list plus the grep that proves it; and
  `brain/design-taste.md` is deleted rather than kept unused.
  **Cycle 3 was the loop limit** (orchestrator manual §5). It did not converge, so the
  orchestrator stopped and handed it to the user rather than dispatching a fourth.
- **User's tie-break, 2026-08-16: one final scoped cycle.** Cycle 4 dispatched with the
  verification method named in the criteria — enumerate computed styles in a real browser
  over every page × option tab × width and report the count of elements inspected, because
  an assertion that inspects nothing passes trivially. **There is no cycle 5.** The coder
  was told the repeated failure is a verification-method problem caused by the
  orchestrator's criterion, not a competence problem, and asked to fix the *class* rather
  than the two named instances: a blanket link rule in `base.css` (the reviewer noted
  `index.html` passes only *incidentally*, via `index.css:32`), and a sweep of every claim
  in any wireframe file about colour, type or motion against what actually renders.
- **The user is reviewing the wireframes before choosing a layout direction**, so D-002 stays
  blocked on that decision regardless of how cycle 4 lands.
- **Cycle 4 delivered 2026-08-16 — in review.** Both findings fixed at the class level, and
  the new verification method did what the old one could not:
  - Finding 1 fixed as a blanket `a { color: #333 }` / `a:hover { color: #000 }` in
    `base.css`, not a per-selector patch, so no future unclassed link can reintroduce it.
    Author-origin rules beat UA `:link`/`:visited` regardless of specificity, so no
    `a:visited` rule was needed. The link stays underlined and keeps its focus ring.
  - Finding 2 fixed in `index.html`, `README.md` — **and `recipe-builder.css:4`, which the
    finding never named.** The coder swept the directory instead of fixing the two cited
    lines, which is the whole point of this cycle: the class, not the instances.
  - `aria-current="true"` added for real to the active option tab in both files, with the
    click handler moving it alongside the `active` class, correcting the cycle-2 record that
    described markup which did not exist.
  - **Verification, by the named method:** 39 page×width×tab combinations, **25,419 elements
    inspected via `getComputedStyle`**, 0 non-greyscale violations, 0 unparsed colour values —
    checking `color`, `background-color`, all four `border-*-color`, `outline-color`,
    `text-decoration-color` and `caret-color`. The element count is stated because an
    assertion that inspects nothing passes trivially. New link contrast 12.63:1 on white,
    11.59:1 on `#f5f5f5`. Regressions re-checked: 0 remote requests, 0 console errors, 0
    horizontal overflow, reduced motion still collapsing `.tab-btn` to `0s`.
- **Review, cycle 4:** 1 required, 0 suggested-major, 1 suggested-minor (the `.rb-matrix`
  scroll affordance, already backlogged, re-checked and confirmed harmless). Both cycle-3
  findings verified fixed: the `← index` link is the first tab stop at `rgb(51,51,51)`,
  underlined, with a visible ring; exactly one `.tab-btn` carries `aria-current="true"` at
  all times, driven through real `.click()`.
  - *Required* — `README.md:65-66` and `base.css:21-25` claim "**no third value exists
    anywhere in the directory**" / "two stacks across the whole directory". A computed
    `font-family` sweep returns **three**: `sans-serif` (8329 elements),
    `ui-monospace, "DejaVu Sans Mono", monospace` (156), and bare `monospace` (1) — on the
    `<code>sans-serif</code>` element at `index.html:80`, which no author rule covers.
  - **The finding was introduced by this cycle's own fix.** `git diff 6457911..HEAD` shows
    that `<code>` element being *added* while rewording the font claim, and the new
    verification enumerates paint properties only — never `font-family` — so the method that
    was supposed to close this class could not see it. The criterion itself is unharmed:
    `monospace` is a generic keyword, not a typeface, so "no chosen typeface" still holds.
    Only the sentence is false.
- **The structural problem, now visible across four cycles.** Each cycle the document makes
  an *exhaustive* claim about its own rendering ("no hue anywhere, in any file", "no third
  value exists anywhere in the directory"), and each fix introduces a new precision that is
  slightly wrong. The claims are hostages to fortune: a throwaway decision document does not
  need directory-wide exhaustiveness proofs, and every one of them is a defect waiting to be
  found. Making the next claim true is not the fix — **not making unfalsifiable-by-inspection
  claims is.** Escalated to the user 2026-08-16 rather than dispatching cycle 5 unilaterally,
  having already told both the user and the coder there would be none.
- **Resolution — merged on the user's explicit override, 2026-08-16, with the `Required`
  finding open.** This is a deliberate exception to orchestrator manual §5 ("Required — must
  be fixed. Not negotiable, not deferrable") and §4 rule 4, recorded here because the rule is
  otherwise absolute and a silent exception would corrode it. The user was shown that the
  option broke the approval gate and chose it anyway; the finding is in `backlog.md` with its
  reproduction and its fix.
  The grounds, for the record: `docs/wireframes/` is a throwaway decision document that
  ships nothing and that no application file imports, the acceptance criterion itself is
  unharmed, and the defect is one false sentence. Four cycles had produced four findings of
  the same shape, with no sign of the sequence terminating.
  **This override does not generalise.** It applies to a non-shipping document whose only
  consumer is the user. A `Required` finding on anything under `src/`, `tests/` or
  `content/` is not merge-able on the same reasoning.
- **Status:** **done** (4 cycles) — merged as `b580729`.
- **Review, cycle 3:** 1 required, 1 suggested-major, 2 suggested-minor. **Loop limit
  reached — escalated to the user 2026-08-16, no fourth cycle dispatched.**
  - *Required* — `mission-screen.html:16`, `recipe-builder.html:16`: the `← index` anchor is
    unstyled and renders `rgb(0, 0, 238)`, the UA default link blue. It sits in the page
    header and is the **first tab stop** on both main screens. Acceptance criterion 1
    ("black and white only — no colour") is therefore not met, and `README.md:62` ("No hue
    anywhere, in any file") is false as rendered. `index.html` escapes only incidentally,
    because `index.css:32` happens to set `.ix__card h2 a { color: #000 }`.
  - *Suggested-major* — `index.html:80` and `README.md:68` still claim prose falls to *the
    browser's default font*. Chromium's default is Times New Roman; these pages declare
    `font-family: sans-serif`, which resolves to the default **sans** (Arial here).
    Criterion 1 still holds — a generic keyword is not a typeface — but this is the *same*
    claim-versus-render mismatch cycle 2 was opened to fix, surviving in the one file the
    reader is told to open first.
- **Why it did not converge — the task was underspecified, and in a nameable way.** Both
  cycle-3 findings are one defect: **claims about the rendering, verified by grepping the
  source.** The coder's check was `grep -rhoiE '#[0-9a-f]{3,8}'` over the files, which
  structurally cannot see a UA default — no hex literal exists for the blue link or the
  Times fallback, so the grep was clean while the render was not. Cycle 2 fixed the one
  instance it was shown (`base.css`) rather than the class, so cycle 3 found the rest.
  "Black and white only" was never operationalised into a check, and that omission is the
  orchestrator's, not the coder's. Any future criterion of this shape must name the
  verification method: *enumerate computed styles in a browser*, never grep hex literals.
- **The reviewer measured rather than sampled**, which is why it caught what two passes
  missed: 891 text nodes resolved against their first opaque ancestor background for
  contrast (66 distinct combinations, 0 failures), `getComputedStyle` over every element on
  every option tab at every width rather than a grep, 37 screenshots, a real `Tab` walk
  (40 stops, 0 without a visible ring), horizontal-overflow probes in all 36
  page×tab×width combinations, and reduced-motion verified by re-rendering under
  `prefers-reduced-motion: reduce`.
- **One backlog entry is wrong and must be corrected when this resumes:** the cycle-2 record
  says `aria-current="true"` on the active option tab was "left in place and backlogged",
  but `grep -rn 'aria-current' docs/wireframes/` returns nothing — the entry describes markup
  that does not exist.
- **Review, cycle 2 (the first review that completed):** 0 required, 1 suggested-major,
  4 suggested-minor.
  - *Suggested-major* — `base.css:17` declares
    `font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`, a named
    system-UI stack, while the PR body and `README.md:62` both state that the browser
    default sans is used and that the only `font-family` declarations are a mono stack on
    numerics. Confirmed live: `getComputedStyle(document.body).fontFamily` returns that
    stack and every heading inherits it. No visual consequence on Linux, but a documentary
    one — a checkpoint document whose stated premise is "no type decision has been made"
    contains one, and design manual §2 names system-UI stacks among the fonts not to use.
  - *Suggested-minor* → backlogged, except the `README.md:60` palette omission, which sits
    in the same "ground rules" block as the font claim and is being fixed in the same pass.
  - **The reviewer re-ran the whole verification block and reproduced it to the decimal** —
    contrast worst case 4.95:1, 39 screenshots, zero remote requests, reduced-motion
    behaviour, and the git-recovery account. It also confirmed the three defects the coder
    said it found and fixed are absent from the current render.
- **Cycle 1 aborted** (2026-08-16): the first reviewer hit the account session limit and
  terminated before producing any findings. Its partial output was not forwarded to the
  replacement, which started clean from the PR alone (orchestrator manual §4 rule 3). Both
  orphaned agent worktrees were removed; every branch kept. The first reviewer
  hit the account session limit and terminated before producing any findings; its partial
  output is not a review and is deliberately not being forwarded to the replacement, which
  starts clean from the PR alone (orchestrator manual §4 rule 3). The orphaned agent
  worktree was removed; its branch, like every branch, was kept.
- **Branch note:** the planned branch `task/d-001-wireframes` was contaminated by F-001's
  commit `9f45703` during the shared-worktree collision (see the orchestrator manual §3).
  Design cherry-picked its own commit onto a fresh branch from `origin/main` rather than
  rebase, force-push or delete — the correct call. `task/d-001-wireframes` still exists at
  `4ce6561`, local only, never pushed. It is not deleted and not reused.
- **Coder's recommendation, for the checkpoint:**
  - *Mission screen* — **Option 2, Notebook Spread.** Method on the left, a run log on the
    right that grows downward instead of overwriting. The only option where a new run does
    not destroy the previous one, so "change one thing and compare" is carried by the
    layout rather than by a 15-year-old's memory; also the only one where missing the
    objective structurally reads as ordinary work rather than an error state. Costs the
    most to build and collapses into Option 5 at 768 px, so choosing it means building
    both. Cheaper fallback: Option 5. Avoid Option 1 despite its familiarity.
  - *Recipe builder* — **Option 1, Card Stack**, with one borrowing from Option 2: a
    collapsed card renders as a clause of a sentence ("Take data at 91 GeV from the IDEA
    detector.") rather than a settings summary. Free to do, and it is the difference
    between a stack that reads as a sentence — which the brief requires — and one that
    lists what you picked. Option 4, Guided Slots, is the fallback if playtesting shows
    students floundering in mission 1; the underlying config is identical, so switching
    later is front-end work, not a rebuild.

