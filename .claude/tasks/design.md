# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

### D-008 — CVD-safe node palette, and the checker claim that certifies it
- **Scope:** `docs/design-explorations/tokens.css` (the eight `--node-*` fills),
  `docs/design-explorations/verify.py` (`check_beamline_pairwise_luminance` and its
  docstring), `docs/design-explorations/beamline.css` (the `.palette__add::before` swatch
  only). Nothing else, anywhere.
- **Why it exists.** D-004 cycle 3 re-lit the palette onto a luminance ladder and met the
  criterion I set — 1.195:1 worst pairwise, 4.79:1 worst white-on-fill, hue drift ≤ 0.7°.
  **The criterion was the wrong one.** A normal-vision luminance floor is not a proxy for CVD
  safety, because protan/deutan L-cone loss shifts the luminous efficiency function away from
  WCAG's fixed 0.2126 red weight. Confirmed independently by both the cycle-3 reviewer and me,
  Machado 2009 severity 1.0 applied in **linear** RGB: 3 of 28 pairs below 1.15:1 under
  protanopia (worst 1.084:1), 2 under deuteranopia (worst 1.089:1), and worst white-on-fill
  drops to **4.48:1 — below AA**. The same re-lighting also pushed four fills below L=0.06, so
  three of them read as one black chip at the 9×9 px picker swatch.
- **Accept:**
  1. All 28 unordered `--node-*` pairs clear a stated floor **measured on Machado-simulated
     fills under protanopia, deuteranopia and tritanopia**, not on normal-vision luminance —
     with the simulation applied in linear RGB, and the floor justified by arithmetic showing
     it is reachable for eight colours before it is imposed.
  2. White-on-fill ≥ 4.5:1 for all eight under all three simulations, not only normal vision.
  3. The three named picker swatches are mutually distinguishable at 9×9 px — design manual
     §2 rule 1 requires the kind hue to read *in the picker*, which is where a student chooses.
  4. `check_beamline_pairwise_luminance` measures what its docstring claims. The current
     "survives every CVD type by construction" is false and must go; read
     `--node-label-on-fill` rather than hard-coding `(255,255,255)`.
  5. Every claim in the docstring is checked by the code beneath it. **This is the fourth
     false absolute claim this project has shipped in a self-describing comment** (D-001 ×2,
     D-003 ×1, now D-004) — the pattern is absolute phrasing outrunning the check, so state
     what is measured and nothing more.
- **Depends on:** D-004 (**done**, merged `bac2f62`).
- **Must run BEFORE D-005 and D-006** — both consume `tokens.css` read-only, and the cost of
  changing the palette triples once they exist. This is the sequencing constraint that made
  the finding worth a task rather than a backlog entry.
- **Lesson to carry into the dispatch, and it is mine:** I set a proxy metric and asserted in
  writing that it held "by construction". The coder wrote my assertion into the docstring, and
  it took the reviewer's independent simulation to catch it. **Do not hand a coder a proxy
  metric and a guarantee about it in the same breath** — give the metric, and let the check
  establish whether the guarantee holds.
- **Branch / PR:** `task/d-008-cvd-palette` — not yet opened
- **Status:** in progress (dispatched 2026-08-19, cycle 1)


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

### D-004 — Node-graph style A: Beamline, plus the shared node palette and checker
- **Scope:** `docs/design-explorations/` — create `beamline.html`, `beamline.css`,
  `beamline.js`; extend `tokens.css` (node-type hues, lock state) and `verify.py` (a
  `--beamline` section). Nothing else, anywhere.
- **Accept:**
  1. Persistence model inspectable in the DOM: Beamline persists an **ordered edge list
     only**, no coordinates — provable by reading a single serialised attribute.
  2. Connection interaction: click-to-connect **accepted**, drag-to-connect **refused**,
     both driven by real Playwright gestures, each assertion mutation-tested.
  3. All **64** ordered node-kind pairs attempted between two distinct node instances:
     **13 accepted, 51 refused**, with the accepted set named in the output.
  4. Every domain-inventory item present via `data-wf`, reported as *n* of *n* with the
     denominator printed; plus one locked node kind present-but-inert.
  5. Computed-style sweep at 1440/1024/768 with denominators, including the contrast of
     every node label on its own fill.
- **Depends on:** D-003 — cleared 2026-08-17, merged as `99ec8f3`.
- **Branch / PR:** `task/d-004-node-graphs` — **#6**. (The branch pre-existed at `c86981c`
  with no commits from the stopped first attempt; reused rather than re-cut.)
- **Status:** **done** (3 cycles) — merged as `bac2f62`. Verified on `main` after merging:
  `verify.py --all` → all 26 sections PASS. **Merged with 2 suggested-major open**, on the
  user's decision at the §5 loop limit, 2026-08-18: PR #6 met its own five criteria with 0
  required for two cycles running, and both open majors are palette problems traceable to my
  criterion rather than to Beamline. They are now **D-008**, which must run before D-005 and
  D-006. Cycle 1: 2 required, 5
  suggested-major, 5 suggested-minor. Cycle 2 fixed all of them, overruling none. Cycle-2
  review: 0 required, 2 suggested-major, 3 suggested-minor. Cycle 3 fixed both majors,
  overruling neither. **This is the last cycle before the §5 loop limit — if the cycle-3
  review is not clean, the task goes to the user as underspecified, not to a cycle 4.**
- **Bookkeeping loss, recorded honestly:** cycle 2's three suggested-minors were written down
  as "two folded into cycle 3, one backlogged". The backlogged one is named in `backlog.md`;
  **the two folded ones were never named anywhere and are lost.** Minors never block, so
  cycle 3 proceeded on the two majors alone. Name every finding individually in future, even
  the minors that are being handled immediately.

- **Cycle 3 delivered 2026-08-18. Verified independently by the orchestrator, and the
  verification found something the coder did not report:**
  - *Suggested-major 2 (worktree resolution) fixed.* `_primary_checkout_root()` resolves the
    reference via `git rev-parse --path-format=absolute --git-common-dir`. The coder ran it
    from inside its own worktree — the actual failing workflow, not a proxy — and
    `beamline-pairs` reports the allowlist executed from the real
    `fce-project/fce/ui/graph.py`, deriving 13 legal pairs. Verified before the fix that the
    incantation returns the primary checkout's `.git` from here.
  - *Suggested-major 1 (isoluminant palette) fixed, and fixed well on the axis I asked for.*
    All eight fills re-lit onto a luminance ladder. **Recomputed independently from the pushed
    tokens; every number reproduces:** worst pairwise contrast among the 28 pairs is
    **1.195:1** (was 1.011:1) against the 1.15 floor I set, and the five worst pairs sit at
    1.195–1.208, so the ladder is near-optimally even rather than merely clearing the bar.
    Worst white-on-fill is **4.79:1**, all eight still above 4.5 — so the focus ring, which
    rings in the same white, still clears SC 2.4.11's 3:1 floor everywhere.
    **The part worth recording: hue drift is at most 0.7°.** I asked for lightness to be
    *added* as a second channel rather than substituted for hue, which was the criterion I
    was least confident would survive contact with the palette. It did, exactly.
  - **A regression the coder did not report and my brief did not anticipate — protanopia.**
    Re-simulating all three CVD types (Machado 2009, severity 1.0) over the 28 pairs:

    | | worst pair before | worst pair after |
    |---|---|---|
    | deuteranopia | obs-global vs obs-custom **7.8** | obs-vecsum vs obs-custom **19.3** |
    | protanopia | data vs multiplicity **20.8** | data vs multiplicity **9.3** |
    | tritanopia | data vs obs-custom **18.7** | selection vs obs-global **19.4** |

    The headline deuteranopia collision that started this is genuinely resolved, 2.5× better.
    Tritanopia is unchanged. **But protanopia regressed from 20.8 to 9.3**, so the palette's
    worst case across all three types moved only 7.8 → 9.3. Better, but not the fix the
    numbers in the PR body imply.
    *The cause is a hole in the proxy I prescribed, so this one is mine, not the coder's.*
    `--node-data` `#775315` and `--node-multiplicity` `#465315` differ almost only in the red
    channel. Standard relative luminance weights red at 0.2126, so the ladder counts them as
    separated (1.208:1) — but a protanope has strongly reduced red sensitivity, so to them
    those two fills are close to isoluminant *and* on the lost red-green hue axis at once.
    **A luminance ladder computed with the standard coefficients is not a CVD-safe proxy for
    pairs separated mainly in red.** That is the general lesson; it will apply again to D-002.
    Not raised with the coder directly — it goes to the cycle-3 reviewer to find or not find
    on its own (§4 rule 3), and it is not `Required` for the same reason the original was not:
    every node also carries a text label, so nothing is unreadable.
- **Scope verified by the orchestrator:** `git diff --name-only main...origin/task/d-004-node-graphs`
  is exactly the five scoped files; the diff against `src/`, `tests/`, `content/` and
  `.claude/` is empty — the contamination from the incident below has not recurred.
- **PR body re-checked before dispatching the cycle-3 review** (§4 rule 3): carries the
  cycle-3 changes, the new criteria marked with evidence, a real `--all` transcript, the
  mutation test of the new check shown failing and restored, and the worktree-run proof.
  Stands alone.

- **Review, cycle 3 — 0 required, 2 suggested-major, 3 suggested-minor. §5 LOOP LIMIT
  REACHED; escalated to the user rather than dispatching a cycle 4.**
  The reviewer ran `verify.py --all` from its **own detached worktree** — exercising the
  worktree fix rather than reading it — and got 26/26 PASS; confirmed
  `_primary_checkout_root()` resolves to the primary checkout and the reference allowlist to
  the real `fce-project/fce/ui/graph.py`. It recomputed all 28 pairwise and 8 white-on-fill
  ratios in its own script and matched the PR body to three decimals. It mutation-tested the
  new check **twice, by monkeypatching `parse_root_tokens` rather than editing repo files** —
  collapsing a pair, and lightening a fill to `#cccccc` — proving both the pairwise branch and
  the AA branch are sensitive. Scope clean; 0 console errors at three widths; 0 `style=`,
  0 `!important`, 0 remote URLs, 0 hex literals outside `tokens.css`.
  - *Suggested-major 1* — `verify.py:2571`. **The new check's docstring claims luminance
    separation survives every CVD type "by construction". It does not, and the palette it
    certifies does not.** Applying Machado 2009 in **linear** RGB (the space the matrices are
    defined in — my own earlier pass applied them in sRGB, which is why I saw the direction
    but understated the size):

    | | pairs below the 1.15 floor | worst pair | worst white-on-fill |
    |---|---|---|---|
    | normal vision | 0 of 28 | 1.195:1 | 4.79:1 |
    | **protanopia** | **3 of 28** | obs-vecsum/obs-custom **1.084:1** | **4.48:1** |
    | **deuteranopia** | **2 of 28** | data/obs-global **1.089:1** | 5.04:1 |
    | tritanopia | 0 of 28 | 1.158:1 | 4.82:1 |

    **Every number independently reproduced by the orchestrator.** The cause: protan/deutan
    L-cone loss shifts the luminous efficiency function, so red-dominant fills darken relative
    to WCAG's fixed 0.2126 red coefficient. The white-on-fill headroom I called "deliberate"
    is spent under protanopia (4.48:1, below AA).
    **This is my decomposition error, twice over, and it is why the loop hit its limit.** I
    prescribed a normal-vision luminance floor as a proxy for CVD safety and told the coder in
    writing that it survives every CVD type "by construction" — the coder wrote my claim into
    the docstring. The criterion as written is met; the criterion was wrong.
  - *Suggested-major 2* — `tokens.css:179-186` + `beamline.css:322-336`. The re-lighting put
    four fills below L=0.06. At node scale all eight stay distinct (screenshot-checked), but at
    the **9×9 px `.palette__add::before` swatch**, `obs-object`, `obs-vecsum` and `histogram`
    read as the same black chip on cream — small-area colour discrimination is much weaker.
    Design manual §2 rule 1 requires the kind hue to read "on the node, **in the picker**, in
    the legend", and the picker is where a student chooses. Also downstream of my ladder brief.
  - *Suggested-minor ×3* — (a) `verify.py:2617` hard-codes `white = (255,255,255)` while the
    docstring says `--node-label-on-fill` is "asserted rather than assumed"; the token is never
    read. (b) PR body criterion 4 claims hue held "to one decimal"; the real drift is up to
    0.7°, so the substance holds but the precision claim does not. (c) The PR body's
    verification block is reformatted rather than verbatim (says 25 sections, lists 26) — every
    number reproduces, but a hand-edited verification block is the one thing it must not be.
  - **Neither suggested-major is `Required`, and the reviewer said why:** every node carries a
    text label and every swatch sits beside its name, so kind identity is never actually lost —
    only the at-a-glance reading the design manual asks for. It also named the legitimate
    counter-argument itself: Machado is a model, not ground truth.
- **Review, cycle 2 — both required findings confirmed genuinely fixed.** The reviewer
  re-derived every criterion against something it ran rather than against the PR body: its own
  Playwright script at three widths plus reduced-motion, its own 17-stop tab walk (8 ports
  ringed white at 5.05–10.92:1, 9 chrome stops at 6.20:1, locked tile unreachable), its own
  contrast sweep over **103 text-bearing elements after instantiating all 8 node kinds** (0
  below AA), its own click/drag/illegal-pair drive, and its own execution of the reference
  allowlist confirming 13 legal pairs. It also audited scope **per commit**, confirming the two
  `design:` commits touch only the five scoped files and the `orchestrator:` commits are
  net-zero against the merge base — which independently closes the contamination incident
  recorded below.
  - *Suggested-major 1* — `tokens.css:162-169`. The 8 node hues are **near-isoluminant**, so
    kind identity rests on hue alone and collides under colour-vision deficiency.
    **Orchestrator re-simulated this independently (Machado 2009 matrices) and confirms it:**
    seven of the eight span relative luminance **0.111–0.158**, and under deuteranopia
    `--node-obs-global` `#1f7a72` and `--node-obs-custom` `#9c3f78` land at RGB (102,106,115)
    and (98,103,118) — **distance 5.8**, the same colour. Under protanopia `data`/`multiplicity`
    are 21.7 apart and `obs-object`/`obs-vecsum` 24.9. (The reviewer reported 5.4 / 18.9 / 21.6;
    different simulation matrices, identical conclusion and identical pairs.) Not `Required`
    because every node also carries a text label, so nothing is unreadable — but design manual
    §2 makes node hue *the* thing that makes the graph readable at a glance, and it does not do
    that for ~8% of male students. **The cost triples after this merge**, because D-005 and
    D-006 consume this token set read-only.
    **One thing the review did not say, and it points at the fix:** cycle 2's histogram
    recolour to `#4a2f6e` (luminance 0.046) is the *only* hue that broke the isoluminance, and
    it is now the most separable of the eight. Spreading lightness across the set is the same
    move, applied to the other seven.
  - *Suggested-major 2* — `verify.py:98`. The reference fallback
    `REPO_ROOT.parent / "fce-project"` resolves against whatever checkout the file sits in, so
    it **does not resolve from a git worktree** — the exact workflow shared §6 tells reviewers
    and previewers to use. The reviewer reproduced it live from its own worktree: criterion 3
    cannot be checked at all without hand-symlinking. Cycle-1's suggested-major 4 added the
    pip-install branch and left this half open.
    `git rev-parse --path-format=absolute --git-common-dir` returns the primary checkout's
    `.git` even from a worktree, which is the clean resolution.
  - *Suggested-minor ×3* — two folded into cycle 3, one backlogged.
- **Cycle 2 delivered 2026-08-18. Verified independently by the orchestrator, not taken from
  the coder's report:**
  - *Required 1 fixed at the right layer.* `.port:focus-visible` now rings with
    `--node-label-on-fill` (white) instead of `--graphite-blue`. Recomputed against all eight
    fills: **5.05:1 worst case** (selection), 10.92:1 best — every one clears SC 2.4.11's 3:1
    floor, and in fact clears the 4.5:1 text floor too. Was 1.06–1.45:1. The `border-radius`
    override that made a focused port morph from circle to square is gone.
  - *Suggested-major 1 fixed.* `.node:nth-child(1..5)` now carry **only** `animation-delay`;
    hue comes from `.node--<kind>` alone. Confirmed by reading the committed file.
  - *Suggested-major 2 fixed.* `--node-histogram` `#38566b` → `#4a2f6e`. Separation from
    `--graphite-blue` goes 1.06:1 → **1.50:1**, and white-on-histogram is now 10.92:1.
    **Note for the reviewer's judgement, not settled by me:** 1.50:1 is still a low *contrast*
    number, but contrast is the wrong metric for "are these two hues distinguishable" — two
    very different hues can share a luminance. The coder's stated basis is a 62° hue-angle
    separation (purple against slate-blue), which is the right axis for the finding as raised.
  - *Required 2, and the three remaining majors* — reported fixed by the coder
    (focus check now composites and asserts >= 3:1, with a mutation transcript;
    `check_beamline_contrast` clicks the three undemonstrated kinds into existence before
    measuring; `box-shadow` literals moved to a new `--node-shadow` token and the paint sweep
    extended to see `box-shadow`; `REFERENCE_GRAPH_PY` resolved via the installed `fce`
    package with the sibling checkout as fallback, prerequisite documented for D-005/D-006).
    **Not independently re-verified by me — that is the review's job.**
  - *Coder reports* `verify.py --all` → 25/25 PASS with D-003's numbers unchanged (peak fill
    0.926), flake8 clean.
- **Scope re-checked after the git incident below:** `git diff --name-only main...HEAD` is now
  exactly the five scoped files; `git diff --stat main...HEAD -- src/ tests/ content/` empty.

#### Orchestrator git error, 2026-08-18 — bookkeeping commits landed on a task branch
**This is the §3 shared-`HEAD` failure the manual documents, and I walked into it.** The
cycle-1 coder checked `task/d-004-node-graphs` out **in the main working directory** rather
than in a worktree. I then ran three bookkeeping commits without checking `HEAD`, so
`fbf9c7c`-equivalents landed on the **task branch** instead of `main`. `git push origin main`
pushed an unchanged ref and reported success, so nothing surfaced it.

Two rules were broken at once: §4's carve-out says bookkeeping goes **straight to `main` and
never appears on a task branch**, and the contaminated branch put
`.claude/tasks/design.md` — which carries my written record of the cycle-1 review and my
framing of the whole task — **inside the PR diff the reviewer reads**. That is §4 rule 3:
the cycle-2 reviewer would have read my summary of cycle 1 instead of forming its own view.

Recovery, using no forbidden operation: the three commits were **cherry-picked** onto `main`
(`fbf9c7c`, `6a3f10f`, `2e8dfd0`) — the same remedy D-001 used for its contaminated branch —
and `main` was then merged **into** the branch, which is the manual's own prescribed fix for a
stale branch. The merge advanced the merge-base, so the two `.claude/tasks/*.md` files drop
out of `main...HEAD`. Verified: no file under `docs/` changed in that merge, and the task
files on the branch are byte-identical to `main`'s.

The merge was performed by the orchestrator rather than the coder only because the cycle-2
agent could no longer be resumed. It changed no file content and touched nothing under
`docs/`, `src/`, `tests/` or `content/`.

**The standing fix:** a coder must never check a task branch out in the main working
directory — `git worktree add` or `isolation: "worktree"`, every time, even for a single
agent. §3 justifies this for *parallel* dispatch; this incident shows a **single** agent is
enough to cause it, because the orchestrator shares that working directory. Check
`git symbolic-ref --short HEAD` before every bookkeeping commit.
- **Review, cycle 1 — and it found a real accessibility defect the checker was built to
  miss.**
  - *Required 1* — `beamline.css:47-52`. The focus ring is `--focus-ring` (= `--graphite-blue`
    `#3c5a6e`) drawn with `outline-offset: 2px` on a 20 px port, so it lands **on top of the
    node's own saturated fill**. It fails WCAG 2.2 SC 2.4.11's 3:1 floor against **all eight**
    node hues. **Orchestrator recomputed all eight independently and they reproduce to the
    digit:** histogram 1.06, obs-object 1.12, obs-vecsum 1.16, obs-custom 1.18, multiplicity
    1.24, data 1.26, obs-global 1.42, selection 1.45. On `--node-histogram` the reviewer
    tabbed to it and screenshotted it: genuinely imperceptible, the only remaining cue being
    the port accidentally morphing from a circle to a rounded square. **8 of the 17 keyboard
    stops have no usable focus indicator.**
  - *Required 2* — `verify.py:2405-2410`. `check_beamline_focus_walk` defines "visible focus
    ring" as `matches(':focus-visible') && outlineStyle !== 'none' && outlineWidth > 0`.
    **Confirmed verbatim by the orchestrator.** That is a *presence* test, not a
    *perceivability* test — it returns PASS on a 1.06:1 ring. So the report line "17 carried a
    visible focus ring, 0 did not", and criterion 5's claim resting on it, are not supported
    by what the check measures. This is the D-003 cycle-1 failure class exactly: an assertion
    that cannot fail in the way that matters.
  - *Suggested-major ×5* — position-decides-hue (`.node:nth-child(1..5)` set `background`
    alongside `animation-delay`; **confirmed** — `(0,2,0)` beats `.node--<kind>`'s `(0,1,0)`,
    so for the first five rail slots the hue is decided by **position, not kind**, and it is
    invisible today only because the demo order happens to match); `--node-histogram` and
    `--graphite-blue` are 1.06:1 apart and read as one colour doing two unrelated jobs; the
    armed-port state swaps the fill to `--graphite-blue`, taking the most important feedback
    in the whole click-to-connect model from 4.29–6.59:1 down to 1.06–1.45:1 and carrying
    nothing in the accessibility tree; `verify.py:63` hard-codes a sibling `../fce-project`
    checkout, so the **shared** checker D-005/D-006 inherit is reproducible on one machine;
    and `box-shadow: 0 1px 0 rgba(0,0,0,0.15)` is a hard-coded colour outside `tokens.css`
    that `PAINT_PROPS` cannot catch and that falsifies `beamline.css:1-2`'s own header.
  - *Suggested-minor ×5* — two folded into cycle 2 (see below), three backlogged.
  - **What the review verified rather than assumed:** scope (5 files, `+1911/-13`, the 13
    deletions all in `verify.py`'s docstring and an args guard, no D-003 check body altered),
    flake8 clean, 49 pytest passes, `verify.py --all` 25/25 reproduced with D-003's numbers
    unchanged, **its own Playwright drive** at three widths, its own 216-element scan for
    coordinate-shaped attributes after four real add-node clicks, its own real
    `mouse.down/move/up` and keyboard connection attempts, and — the best of it — it
    **`exec`'d `_VALID_CONNECTIONS` out of the reference `ui/graph.py` and regex-extracted
    `create_node("…")` from `fce.py` itself**, then diffed the result against `beamline.js`'s
    table: symmetric difference empty. Criterion 3 is checked against the reference's running
    code, not against my dispatch.
- **Both of my flagged doubts resolved, and one of them against me.** (1) Criterion 5's
  "5 of 8 hues" deviation is **not** a defect: the reviewer recomputed all eight ratios from
  the raw tokens itself and every number reproduces, so the values are true regardless of how
  many nodes exist on a fresh load. What remains is that the *sweep* measures five of them
  while three are asserted — worth closing when the focus fix touches this code anyway.
  (2) The claim that the inherited comment was breaking D-003's token parser is **not
  confirmed**; the reviewer reports 25/25 with D-003's numbers unchanged, which shows the
  parser works now, not that it was broken before. Left unproven rather than recorded as fact.
- **Coder reports** (unverified by anyone else yet): `verify.py --all` → **25/25 sections
  PASS**, including every pre-existing D-003 section unchanged; `flake8` clean;
  `git diff --name-only main...HEAD` exactly the 5 scoped files; `git diff --stat
  main...HEAD -- src/ tests/ content/` empty. Five mutation tests driven (accept path,
  refuse path, coordinate assertion, inventory count, locked-tile keyboard reachability),
  each shown failing then restored. 22 domain-inventory items via `data-wf`; 17 tab stops
  all with a visible ring.
- **PR body checked before dispatching review** (orchestrator §4 rule 3): carries the task ID,
  goal, verbatim scope, all five criteria marked with evidence, a real verification
  transcript, a mutation-testing section, and declared deviations. Stands alone.
- **The inherited `tokens.css` comment did more damage than anyone knew.** It was dispatched
  as "one false sentence" — it claimed contrast ratios were measured by a `verify.py` section
  that had never been written. The coder reports it was **also syntactically breaking D-003's
  own token parser**, which nobody had noticed because nothing had re-run the parser since.
  **This needs independent confirmation from the review**, since it is a claim about the
  shared file D-002 harvests.
- **Declared deviations, cycle 1, for the reviewer to weigh:** (1) bare `--beamline` still
  triggers D-003's pre-existing unconditional anatomy block, because that block never checked
  any flag and changing it was out of scope; (2) a `check_beamline_focus_walk` was added
  beyond the five named criteria; (3) the node-fill contrast report shows **5 of 8** hues on a
  fresh load — the other three need an add-node click to exist — so 3 of the 8 label-on-fill
  ratios are asserted in a `tokens.css` comment rather than measured by the sweep. **Criterion
  5 says every node label against its own fill; on the coder's own account it measures five
  eighths of them.** Do not resolve this from the coder's report — it is exactly what the
  review is for.
- **New shared surface for D-005/D-006, from the coder's report:** `tokens.css` gains
  `--node-*`, `--locked-*` and a new `--on-graphite-blue`; `verify.py` exposes
  `parse_root_tokens`, `resolve_allowed_colors`, `contrast_ratio`, `composite_over` and
  `EXHAUSTIVE_CLAIM_PATTERNS` as read-only helpers, plus `BEAMLINE_DOMAIN_INVENTORY`, which
  is the **mission screen's** inventory rather than a Beamline-specific one — so D-005 and
  D-006 must satisfy the same 22 items. If that survives review, rename it in D-005 rather
  than let the name mislead.

#### The 64/13/51 ruling, and why the old criterion was wrong
The original criterion said "all **121** ordered node-type pairs". 121 implies 11 node
kinds. **The error was the orchestrator's** — the number was inherited from this entry's
first draft and was never grounded in anything. Verified against reference source, twice,
by the orchestrator rather than taken from an agent:

- `fce-project/fce/ui/graph.py:163` — `_VALID_CONNECTIONS`, **9** keys.
- `fce-project/fce/ui/state.py:35` — `NODE_LABELS`, the same 9.
- `fce-project/fce/fce.py:501-526,802-806` — `create_node("…")` is called for exactly
  **8** of them. **Bare `"Observable"` is never instantiated**: it is an allowlist
  grouping, not an addable node kind, so no node of that kind can exist on a canvas and no
  gesture can target it.

**Ruled: 8 addable kinds → 64 ordered pairs.** Not 81, and not 121. `Observable` stays out
of the enumeration *and* out of the palette, because enumerating it would test a state the
UI cannot reach.

The 13 legal pairs, derived from the allowlist with `Observable` removed:

| Source | Legal destinations | *n* |
|---|---|---|
| `DataSource` | `Multiplicity`, `Selection` | 2 |
| `Multiplicity` | `Multiplicity`, `Selection` | 2 |
| `Selection` | `Selection`, `ObsGlobal`, `ObsObject`, `ObsVectorSum`, `ObsCustom` | 5 |
| `ObsGlobal` / `ObsObject` / `ObsVectorSum` / `ObsCustom` | `Histogram` | 4 |
| `Histogram` | — | 0 |

`Multiplicity → Multiplicity` and `Selection → Selection` are legal **between two distinct
nodes of the same kind**; `link_callback` (`ui/graph.py:193-213`) validates on kind alone,
so self-loops are out of scope for this check.

#### What the stopped attempt left, and what to do with it
The first D-004 agent was stopped by the user before any commit. One **uncommitted** 41-line
addition to `docs/design-explorations/tokens.css` survives in the agent worktree
`.claude/worktrees/agent-aabe0d4da7ede4df9`. **Do not remove that worktree without reading
the diff.**

It found the 8-vs-11 discrepancy itself, by reading `ui/graph.py` rather than trusting the
dispatch — which is exactly the behaviour the four verification rules exist to produce.

Its palette: 8 hues, each with white node-title text, plus a `--locked-fill` that is
desaturated rather than merely lighter, its label on full `--ink` because `--ink-70` over
that fill measures 4.30:1, under the 4.5:1 floor. **The orchestrator recomputed all ten
ratios independently and every one reproduces exactly** — white on the 8 hues is
5.05–7.74:1, `--ink` on `--locked-fill` is 8.90:1, `--ink-70` is 4.30:1. The values are
sound and should be kept.

**One sentence in it is false and must be corrected, not inherited:** the comment says the
ratios are "measured by verify.py's D-004 contrast section", and that section was never
written. It is a claim about a check that does not exist — the D-003 failure class exactly.
Either write the section first or reword the comment.


### D-003 — Interactive plot component at reference parity
- **Branch / PR:** `task/d-003-plot-component` — #5, merged as `99ec8f3`. Branch kept at `4ed75d8`.
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

