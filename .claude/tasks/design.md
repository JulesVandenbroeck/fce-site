# Design tasks

Owned by `design-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `D-nnn`, allocated in order and never reused.

---

## In progress

### D-001 — Wireframe exploration: mission screen and recipe builder
- **Scope:** `docs/wireframes/` (output only — no application files)
- **Accept:** `/wireframe` run for both the mission screen and the recipe-card builder;
  options explore genuinely different information architectures, not restyles of one
  layout; each is annotated with what it optimises for; a recommendation is stated with
  reasoning. **Output goes to the user for a decision — this is an M1 checkpoint.**
- **Depends on:** nothing
- **Branch / PR:** `task/d-001-wireframes-clean` — #2
- **Status:** in review (cycle 3) — **the cycle-2 rework is done and pushed**, though the
  list said otherwise until the next session checked git. Commit `6457911` addresses the
  suggested-major and two of the minors: `base.css` body drops the named
  `-apple-system/BlinkMacSystemFont/Segoe UI` stack for the generic `sans-serif` keyword,
  making the PR's stated "no type decision has been made" premise true; `.tab-btn` gains
  `font: inherit`, so every element on all three pages now computes to one of exactly two
  `font-family` values instead of falling back to the UA default; `README.md`'s palette is
  replaced with the exhaustive twelve-grey list plus the grep that proves it; and
  `brain/design-taste.md` is deleted rather than kept unused.
  **Cycle 3 is the loop limit** (orchestrator manual §5) — if this review does not converge,
  the orchestrator stops and hands the disagreement to the user rather than dispatching a
  fourth cycle.
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

_none_
