# D-016 handoff — design, cycle 1 (HANDOFF NOW, no work committed)

NOTE: worktree isolation refused writes to the primary checkout's .claude/handoff/, so this
file lives in the WORKTREE instead, at:
.claude/worktrees/agent-a1a7be38838a932a5/.claude/handoff/d-016-design-1.md
The orchestrator/next session must copy or read it from there — it is not in the primary
checkout's `.claude/handoff/`.

## Status
No branch created yet (`task/d-016-results-chart-styling` does not exist locally or on
origin — never pushed). No files written. Nothing to commit. Worktree is clean, still on
`worktree-agent-a1a7be38838a932a5`.

## Worktree
`/home/julvdnbr/Documents/Phd/teaching/fce-site/.claude/worktrees/agent-a1a7be38838a932a5`
No venv set up yet in it. Next session must create one (check pyproject.toml extras) before
running tests/Playwright. `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright` is the shared
browser cache — reuse it, do not reinstall.

## Reading done — do not re-read, grep/cite instead
Fully read and internalised: `.claude/shared/CLAUDE.md`, `.claude/design/CLAUDE.md`,
`docs/design-brief.md` (§2, §4, §5, §7 esp.), `tokens.css` (all of it — colour tokens
already exist: `--frozen-x1/x2/x3`, `--vermillion`, `--graphite-blue`, focus tokens, motion
tokens), `shell.css` (all 326 lines), `base.html`, `shell.html`, `chart.js` (all 503 lines),
`run.js` (all 209 lines).

## What's established about C1 (the canvas-displacement bug) — dead ends and open question
- `shell.html`: `.canvas-region` contains three flex-item siblings in document order:
  `.canvas-wrap` (the node graph, fixed 704x512), `.run-control` (the Run button),
  `.results` section (status/progress/note/chart).
- `shell.css:183-191` — `.canvas-region { flex: 1 1 0; display: flex; ... }` has **no
  `flex-direction` set**, so it defaults to **row**. `.canvas-wrap` (`shell.css:198-205`)
  has `margin: auto`, which is what centres it — auto margins absorb free space on
  *both* axes in flexbox, which is why this one rule centred the canvas both ways before
  the chart existed.
- Task text (D-016 dispatch) asserts the fix is to **constrain `.chart-figure`** (the div
  chart.js wraps its svg in — `chart.js:239-241`) with something like `overflow-x: auto` and
  a max-width, *without* changing `.canvas-region`'s flex-direction. I was suspicious of
  this: at 1440px, `.canvas-region`'s available width is roughly 1440 − 368 (palette
  expanded) − 320 (mission-panel expanded) ≈ 752px, and `.canvas-wrap` alone is 704px fixed
  — leaving only ~48px of row space for `.run-control` + `.results` if they really do sit
  **beside** the canvas in a row. That seemed implausible for a "results region below the
  canvas" reading of the brief, and I had not yet confirmed which is true empirically
  (`document.elementFromPoint` per the task's own C1 check) before the handoff fired — **I
  had not yet started the dev server or taken a screenshot.** This is the first thing to
  resolve next: load the app, inspect actual computed `flex-direction` and children layout
  at 1280×720 in devtools/Playwright, *then* decide whether the fix is (a) constrain
  `.chart-figure` only as the task suggests, or (b) also give `.canvas-region` a
  `flex-direction: column` (which is a shell.css change, in scope for D-016) if row layout
  turns out to be structurally untenable. Do not assume either — check first.

## Other facts already extracted from chart.js/run.js (save yourself the re-read)
- `.chart-figure` div wraps `svg#hist-svg`, fixed `viewBox="0 0 650 460"` intrinsic size
  (`FIG.w`/`FIG.h` in chart.js, `FIG.h = 460`, computed `FIG.w` from constants — comes to
  650). This must never reflow (C3).
- Reveal classes: `.reveal-frame` (on `.plot-frame` rects), `.reveal-band` (on `.hist-band`
  sample paths and `.syst-band`, staggered `s0`–`s3`), `.reveal-data` (on `.data-points`
  group and `.panel-ratio` group). **`.reveal-armed` is added exactly once, to the
  `.chart-figure` wrapper div, by `armReveal()` (`chart.js:204-211`), and is never removed**
  — CSS must key off `.chart-figure.reveal-armed .reveal-frame` etc. and use
  `animation-fill-mode: forwards`, not rely on class removal. `armReveal` already skips
  adding the class entirely under `prefers-reduced-motion: reduce`, so the reduced-motion
  path just needs the *unarmed* (no `.reveal-armed` ancestor) state to already equal the
  settled end state — no separate media query needed in chart.css for that part, just make
  sure the base (non-`.reveal-armed`) rules for `.reveal-frame`/`.reveal-band`/`.reveal-data`
  already paint the final look with no animation.
- `.legend-frame` is a `<rect>` painted before its own swatches/labels
  (`chart.js:178`, first child of the `<g class="legend legend-framed">`), currently has no
  `fill` set anywhere → renders as solid black (SVG default fill) covering the legend text.
  Needs a `fill` (almost certainly `var(--panel)` or `var(--paper)` to match the notebook
  ground) plus probably a `stroke` for definition, in `chart.css`.
- `.hist-band` (`chart.js:328`, class `sample-${name.toLowerCase()} hist-band reveal-band
  sN`) needs `fill-opacity: 0.8` (task says F-008 removed it from the JS deliberately,
  D-016's job to restore in CSS) and its fill colour keyed by `sample-x1/x2/x3` classes to
  `var(--frozen-x1/x2/x3)` (tokens.css:169-171) — same colours must drive `.legend-swatch`
  fills for the matching `${item.cls} legend-swatch` classes (`chart.js:182`,
  `cls: sample-${s.name.toLowerCase()}`), so one rule set covers both graph and legend
  automatically if selectors are `.sample-x1 { fill: var(--frozen-x1); }` etc. applied to
  both `.hist-band` and `.legend-swatch` via a shared class match.
- `#run-button` uses `aria-disabled="true"/"false"` (`run.js:87`, `shell.js` sets it), never
  the `disabled` attribute (deliberately, per run.js's own comment — dropping it loses
  keyboard focus mid-run). CSS must style `[aria-disabled="true"]` for the busy/disabled
  look; `:disabled` pseudo-class will never match and must not be used.
- `.bin-hit` (`chart.js:364`, 50 `role="button" tabindex="0"` rects, `fill: none` inline)
  needs a visible `:focus-visible` ring meeting AA non-text contrast (3:1) — plain
  `outline: var(--focus-ring-width) solid var(--focus-ring)` per the existing shell.css
  convention (`shell.css:40-44`) should suffice but must be checked against paper AND
  against the coloured hist-band fills it may sit over.
- `.results__note` (`shell.html:76`, `run.js` `setNote()`) has **no `role="alert"`** already
  — confirmed by reading both files — so C7 is mostly "don't add one, style it as a quiet
  margin note (handwritten-feel per brief §7, lighter ink, maybe italic/rotated slightly per
  design manual's marginalia device, `.claude/design/CLAUDE.md` §3)", not a fix to markup.

## File scope (unchanged from dispatch, verbatim)
Edit only: `src/fce_web/static/css/chart.css` (new), `src/fce_web/static/css/shell.css`,
`src/fce_web/templates/base.html` (one `<link>` line only), `src/fce_web/templates/shell.html`
(class attributes / presentational wrappers only).

## Next step for whoever picks this up
1. `cd` into the worktree above (already exists, reuse it — do not `git worktree add`
   again), set up a venv, install the project, confirm Playwright browsers are usable.
2. Run the dev server, screenshot/inspect `.canvas-region` at 1280×720 and 1440/1024/768 to
   settle the C1 row-vs-column question empirically before writing any CSS.
3. Write `chart.css` fresh (does not exist yet) covering all the classes chart.js emits
   (full enumerated list is in the D-016 task dispatch text — re-read that, not this file,
   for the exact list, it's verbatim there).
4. Branch `task/d-016-results-chart-styling` from `main` **before** committing anything —
   has not been created yet.
5. Standalone Playwright verification script per the task's "Verification" section (not
   added to the repo) — none written yet.

No tests run, no lint run, no screenshots taken this cycle — session ended before any
implementation or verification work began.
