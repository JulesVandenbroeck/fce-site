# Handoff: F-016 — Pan and zoom on the canvas surface (cycle 1)

- **Role:** frontend-coder
- **Written:** 2026-09-23 ~19:30, at ~60% of the 5-hour limit (stopping on a
  confirmed blocker, not usage — see below)
- **Cycle:** 1
- **Continues:** `.claude/handoff/f-016-frontend-1.md` (the interrupted cycle 1)

## The task as I was given it

Goal: The canvas pans by left-drag and keyboard and zooms 50-200% with a
single Fit affordance, in the real app.

File scope — edit ONLY:
- src/fce_web/static/js/graph.js
- src/fce_web/templates/shell.html
- tests/e2e/test_graph.py
- tests/e2e/test_smoke.py

Read ONLY: docs/design-explorations/canvas-frame.{html,css}, shell.css,
canvas.css (read-only).

Acceptance criteria (verbatim, total checks: 10):
- [ ] C1 left-drag on empty canvas pans both axes (scrollLeft AND scrollTop
  change) at 100% and at 50% zoom.
- [ ] C2 a drag starting on a node moves the node and leaves
  scrollLeft/scrollTop byte-identical.
- [ ] C3 keyboard pan (focused #canvas-wrap, arrow keys) reaches both axes.
- [ ] C4 zoom clamps to 50-200%.
- [ ] C5 the sheet stays monotonic in node extent — zooming in never orphans
  a node placed at a lower zoom. The test must actually move a node (assert
  its position changed) and must go red under a mutation dropping the
  node-extent term from applyZoom; show that red run in the PR body.
- [ ] C6 Fit shows every node, and is the only such affordance (no separate
  reset-to-100% control).
- [ ] C7 F-015's no-horizontal-page-scroll probes in test_smoke.py still
  pass.
- [ ] C8 no nested region landmark: #results is not a second landmark
  inside #drawer.
- [ ] C9 full suite ≥ 729 passed + additions, flake8 0, no existing
  assertion weakened.
- [ ] C10 no test injects canvas-frame.css or overrides production CSS;
  every pan/zoom test runs on the real app stylesheets. Check:
  `grep -n "add_style_tag\|canvas-frame.css" tests/e2e/` → no matches.

## State of the branch

- Branch: `task/f-016-canvas-pan-zoom` — pushed: yes
- HEAD: `e706e7a` — merges origin/main (D-022 #63) in, fixes the C1 pan
  test's drag direction, removes the CSS-injection workaround from
  test_graph.py entirely (C10 now literally true — grep confirms no
  `add_style_tag`/`canvas-frame.css` anywhere in tests/e2e/).
- PR: not opened. Per the dispatch's own instruction — "If C1/C2 still
  cannot be made to pass, do not open the PR" — and C1 (the full test, both
  zoom levels) still cannot pass; see below.
- Working tree at handoff: clean (worktree
  `.claude/worktrees/agent-a70512847d39d2c49`, `.venv2/` untracked, not
  part of the diff).
- Tests at HEAD:
  `PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright pytest tests/e2e/test_graph.py -k "pan or zoom or Fit or fit" -q`
  → `4 failed, 2 passed, 20 deselected` (C2, C3 pass; C1, C4, C5, C6 fail,
  all four on the same root cause below).
  `flake8 src/ tests/ scripts/` → clean.
  Full suite not re-run this cycle (no point until the CSS blocker is
  closed — would just reproduce the same 4 failures plus whatever the
  baseline already had).

## Acceptance criteria — where each one stands

- [ ] C1 — not met, in one half. 100%-zoom sub-case now passes (confirmed
  via probe: drag up-left from origin moves scrollLeft/Top 0,0 → 80,60).
  50%-zoom sub-case still fails: it needs `#zoom-out.click()`, blocked —
  see Dead ends.
- [x] C2 — met. `pytest tests/e2e/test_graph.py -k test_drag_starting` →
  passed.
- [x] C3 — met. `pytest tests/e2e/test_graph.py -k test_keyboard_pans` →
  passed.
- [ ] C4 — not met. Needs `#zoom-in`/`#zoom-out` clicks, blocked, same
  cause.
- [ ] C5 — not met. Needs `#zoom-out` clicks to reach 50% before the drag,
  blocked, same cause.
- [ ] C6 — not met. Needs `#zoom-out` then `#zoom-fit` clicks, blocked,
  same cause.
- [?] C7 — not re-verified this cycle (unrelated to the blocker; carried
  over from cycle 1, no reason to expect it changed. Cycle 1's handoff
  didn't report it broken).
- [x] C8 — met. `grep -n 'id="results"' src/fce_web/templates/shell.html` →
  `<div class="results" id="results">`, a plain div, not nested inside
  `#drawer`'s own region.
- [ ] C9 — blocked on C1/C4/C5/C6.
- [x] C10 — met. `grep -n "add_style_tag\|canvas-frame.css" tests/e2e/` →
  no matches (both removed from test_graph.py this cycle).

## Done

- `tests/e2e/test_graph.py` — removed `_use_panzoom_css`/`CANVAS_FRAME_CSS`/
  the `Path` import entirely; every pan/zoom test now runs against
  production CSS only (C10). Fixed the C1 test's drag direction (see Dead
  ends — this was never an app bug). Trailing-newline flake8 fix.
- Merged `origin/main` (D-022, PR #63, commit a81aba0) into the branch —
  clean merge, no conflicts.

## Not done, in the order I would do it

1. **Close the CSS gap** (see Dead ends) — needs a design task, out of this
   task's file scope. Port `.zoom-controls`, `.zoom-controls__btn`,
   `.zoom-controls__btn--fit`, `.zoom-controls__readout` from
   `docs/design-explorations/canvas-frame.css` (lines ~145-184) into
   `src/fce_web/static/css/shell.css`, the same pattern D-022 already used
   for `.canvas-wrap`/`.frame`/`.canvas-region`.
2. Re-run `pytest tests/e2e/test_graph.py -k "pan or zoom or Fit or fit"`
   once that CSS lands — expect all 6 to pass with zero further JS/HTML/test
   changes; nothing else in this task's scope needs touching.
3. Re-verify C7 (`pytest tests/e2e/test_smoke.py` — grep for the
   no-horizontal-scroll test names first, cycle 1's handoff didn't name
   them).
4. Full suite + flake8, then open the PR.

## Dead ends — do not repeat these

- **The cycle-1 "scrollLeft is a no-op in pointermove" mystery had two
  separate causes, both now resolved — do not re-investigate wirePan's
  pointer handling, it is correct.**
  1. D-022 (merged since cycle 1) gave `#canvas-wrap` real
     `overflow: auto` + scroll range in production CSS. That part of the
     old mystery no longer applies.
  2. The other part was a **test bug**, not a JS bug: cycle 1's C1 test
     dragged **down-right** from the canvas's initial scroll position
     (0, 0). `scrollLeft`/`scrollTop` cannot go negative, so the browser
     silently clamps the write back to 0 — which looks exactly like "the
     assignment did nothing." Confirmed by patching
     `Object.defineProperty(Element.prototype, 'scrollLeft', ...)` with a
     logging setter and running the same drag: it logged
     `SET scrollLeft -16 at graph.js:255 onMove` on every step. Fixed by
     dragging up-left instead (`start[0] - 80, start[1] - 60`); confirmed
     working via a standalone probe (0,0 → 80,60). **graph.js was not
     touched and does not need to be.**
- **The real, current blocker: `#zoom-controls` has zero CSS in
  production.** `grep -ni zoom src/fce_web/static/css/*.css` matches only
  two code-comment lines, no rule. Unstyled, `#zoom-controls` (a static-flow
  sibling of `#canvas-wrap` inside `#canvas-region`, which is
  `position: absolute; inset: 0`) renders full-width at the very top of
  `#canvas-region` — `getBoundingClientRect()` confirmed `#zoom-out` at
  x:0-26, `#zoom-in` at x:67-93, `#zoom-fit` at x:96-130, all at the same
  y as `.palette`'s expanded rect (x:0-256, z-index 2). The palette (a
  z-index:2 overlay) sits on top of all three buttons, so
  `page.locator("#zoom-out").click()` times out with "subtree intercepts
  pointer events" — reproduced directly, this is not flaky, it is 100%
  reproducible at every width tried (1280 viewport).
  - **Tried and ruled out:** collapsing the palette first
    (`#palette-toggle`) does not help — collapsed width is
    `var(--space-7)` = 64px (confirmed in `tokens.css:318`), which still
    fully covers `#zoom-out`'s 0-26px span.
  - **Not tried, and not this task's to fix:** any CSS change. `shell.css`/
    `canvas.css` are explicitly read-only in this task's file scope; no
    inline `style=` or JS-set positioning either — that is a visual
    decision, which is design's, not frontend's, per
    `.claude/shared/CLAUDE.md` §4. `docs/design-explorations/canvas-frame.css`
    already has the correct rule (`.zoom-controls { position: absolute;
    top: var(--space-3); left: 50%; transform: translateX(-50%); ...}`,
    lines 145-158) — it was simply never ported into `shell.css` by D-022,
    which only covered `.frame`/`.canvas-region`/`.canvas-wrap`.

## Open questions for the orchestrator

- Please dispatch a short design task to port `.zoom-controls` and its
  three child selectors from `docs/design-explorations/canvas-frame.css`
  into `src/fce_web/static/css/shell.css`. It's a same-shape port to
  D-022's (bring an approved reference rule into production CSS), and it
  is the only thing standing between this branch and green on C1/C4/C5/C6.
  No JS or markup changes are expected to be needed after it lands.

## Environment notes

- Worktree: `.claude/worktrees/agent-a70512847d39d2c49`, has its own
  `.venv2/` (untracked, already set up — `python -c "import fce_web,
  pytest, playwright"` succeeds).
- `export PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright` before running
  Playwright tests.
- No server left running; nothing else stateful.
