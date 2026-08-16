# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

_none_

## Ready

_none_

## Blocked

### D-002 — Design token foundation
- **Scope:** `src/fce_web/static/css/tokens.css`, `src/fce_web/static/fonts/`
- **Accept:** every colour, spacing, type-scale, radius, and timing value defined as a
  custom property; the lab-notebook palette committed with measured AA contrast ratios
  documented in the file; self-hosted woff2 fonts, no CDN; a chosen serif and mono that
  are explicitly not Inter/Roboto/system-ui/Space Grotesk
- **Depends on:** D-001 **and the user's layout decision** — the M1 checkpoint
- **Owed from D-001:** the wireframe contrast ratios were measured against wireframe white,
  because no paper colour exists yet. AA must be re-measured against the real paper token.
- **Branch / PR:** not yet opened

## Done

### D-001 — Wireframe exploration: mission screen and recipe builder
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

