# F-016 anchor — frontend, canvas pan/zoom

Worktree: .claude/worktrees/agent-a70512847d39d2c49, branch not yet created
(still on worktree-agent-a70512847d39d2c49 — MUST `git checkout -b
task/f-016-canvas-pan-zoom` before committing). Sandbox refuses writes
outside this worktree — this anchor could not be placed in the primary
checkout as instructed; note that in the handoff/report if reached.

## Decisions
- Port canvas-frame.html's applyZoom/setZoom/fit/wirePan almost verbatim into
  graph.js. Keep existing ids (#canvas-wrap, #canvas-svg, #nodes-layer,
  #edges-layer, #canvas-status) — do NOT rename to canvas-viewport/node-card.
  Add class `canvas-viewport` onto #canvas-wrap as a styling hook (D-022).
- Replace fixed CANVAS_W/CANVAS_H with mutable `sheet` object grown by
  applyZoom (monotonic — max of viewport-derived, SHEET_MIN, node-extent
  terms). clampToCanvas/nextSpawnPoint now read sheet.w/sheet.h.
- Add #zoom-controls markup (zoom-out/zoom-in/zoom-fit buttons + output
  readout) inside #canvas-region, copied from canvas-frame.html verbatim.
- Pan: pointerdown on #canvas-wrap, skip if `ev.target.closest(".node")`
  (existing node class, NOT `.node-card`). Wheel = zoom (passive:false).
- Keyboard pan: native — tabindex=0 + role=group on #canvas-wrap, no JS,
  browser scrolls the focused scrollable element on arrow keys.

## Dead end / real blocker found
canvas.css/shell.css are STALE (last touched D-019, before F-015's markup
restructure) — `.canvas-wrap` is CSS-fixed-width, `.canvas-svg{width:100%}`,
no `overflow:auto` anywhere useful. Confirmed empirically: scrollLeft is a
no-op without `overflow != visible`. Production page CANNOT visually pan/zoom
until D-022 ships equivalent of canvas-frame.css. I CANNOT touch CSS (scope).
**Resolution:** e2e tests inject docs/design-explorations/canvas-frame.css
via `page.add_style_tag(path=...)` to exercise the real JS/DOM mechanism
under the CSS contract D-022 will supply — disclosed plainly in PR body, not
hidden. test_smoke.py's existing C7 h-scroll test is NOT touched by this
(tests real prod page, unaffected).

## Next step
shell.html structural comment done. Still need: canvas-wrap tabindex/role/
aria-label + canvas-viewport class, zoom-controls markup, graph.js changes
(constants, applyZoom/setZoom/fit/wirePan, init() wiring, clampToCanvas),
then test_graph.py new tests (C1-C6), confirm test_smoke.py C7
untouched/passing, F3 aria-label fix (shell.html #results nested landmark →
drop label or change to div), full suite + flake8, PR.
