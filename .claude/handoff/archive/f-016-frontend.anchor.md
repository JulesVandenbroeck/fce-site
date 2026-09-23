# F-016 anchor — frontend, canvas pan/zoom (cycle 1, resumed)

Worktree: .claude/worktrees/agent-a70512847d39d2c49, branch
task/f-016-canvas-pan-zoom, merged origin/main (D-022 #63) in cleanly.

## Resolved this session
- The handoff's "scrollLeft no-ops in pointermove" mystery: TWO separate
  causes, both now understood.
  1. D-022 (merged) gave `#canvas-wrap` real overflow/scroll range in
     production shell.css. That part of the mystery is gone.
  2. The WIP C1 test dragged down-right from the origin (scrollLeft/Top
     start at 0, drag requested negative, browser clamps to 0 -- looked
     like "no-op" but was correct clamping). Confirmed via a scrollLeft
     setter probe: `SET scrollLeft -16 at graph.js:255 onMove`. Fixed the
     test to drag up-left instead -- confirmed panning now works at 100%
     zoom (scrollLeft/Top go 0,0 -> 80,60).
- graph.js's wirePan/applyZoom/setZoom/fit logic itself is NOT the problem.
  Did not touch graph.js.

## Real remaining blocker (CSS, out of scope)
`#zoom-controls` (and its buttons) has ZERO CSS in production shell.css/
canvas.css -- grep confirms no `.zoom-controls` rule anywhere shipped.
Unstyled, it flows at `#canvas-region`'s top-left (0,0), full width, so
`#zoom-out`/`#zoom-in`/`#zoom-fit` sit directly under the expanded
`.palette` overlay (z-index 2) at every viewport width. Confirmed via
`getBoundingClientRect`: zoom-out at x:0-26, palette spans x:0-256.
Collapsing the palette doesn't help either (collapsed width 64px still
covers zoom-out's 0-26 span). This blocks every test that must click a
zoom button: C1's 50%-zoom half, C4, C5, C6.
canvas-frame.css (the approved reference) already has the fix:
`.zoom-controls { position: absolute; top: var(--space-3); left: 50%;
transform: translateX(-50%); ...}` (lines ~145-184) -- never ported into
shell.css by D-022, which only covered `.frame`/`.canvas-region`/
`.canvas-wrap`. This needs a small design-owned CSS change; not something
frontend can fix within its file scope (shell.css/canvas.css are read-only
here, and no inline `style=`/JS-set styling is allowed either).

## Next step
Report this to orchestrator as a blocker needing a short design task
(port `.zoom-controls`/`.zoom-controls__btn`/`.zoom-controls__readout`
from canvas-frame.css into shell.css). Do NOT open the PR per the
dispatch's own instruction ("if C1/C2 still cannot be made to pass, do
not open the PR"). C1 (full, both zoom levels), C4, C5, C6 cannot pass
until that CSS lands. Work here (direction fix, CSS-injection removal
from tests) is committed on the branch so the next cycle can resume
directly once the CSS gap is closed.
