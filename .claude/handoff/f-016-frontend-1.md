# F-016 handoff — frontend, canvas pan/zoom (cycle 1)

Branch pushed: `task/f-016-canvas-pan-zoom`, commit `87582e8`. No PR opened
yet (WIP: C1/C2 not passing — see below). Sandbox in this session refused
writes outside the worktree, so this handoff and the earlier anchor live at
`.claude/handoff/` inside the worktree, not the primary checkout as the
protocol asks — copy them over.

## What's done and works
- graph.js: sheet/zoom state, `applyZoom`/`setZoom`/`fit`/`wirePan`, ported
  from `docs/design-explorations/canvas-frame.html` almost verbatim.
  `clampToCanvas`/`nextSpawnPoint` now read the mutable `sheet.w/h` instead
  of the old fixed `CANVAS_W`/`CANVAS_H`.
- shell.html: `#canvas-wrap` gets `tabindex=0 role=group`, the extra
  `canvas-viewport` class, an updated aria-label; `#zoom-controls` markup
  added (zoom-out/zoom-in/fit + `#zoom-readout` output), copied verbatim
  from the reference. F3 carry-in done: `#results` is now a plain `<div>`,
  not a second landmark nested in `#drawer`'s own region.
- tests/e2e/test_graph.py: new tests for C1/C2/C3/C4/C5/C6, using
  `page.add_style_tag(path=canvas-frame.css)` + a small ID-selector override
  (`#canvas-wrap{width:auto}`, `#canvas-svg{width:auto;height:auto}`) plus a
  `resize` dispatch, because production `canvas.css`/`shell.css` predate
  D-022 (confirmed via `git log`: last touched at D-019, before F-015's
  markup restructure) and do not give `#canvas-wrap` real overflow/sizing —
  this is disclosed in the test module's own docstring, not hidden.
- **Verified passing individually** (`pytest tests/e2e/test_graph.py -k
  "pan or zoom or Fit or fit"`): `test_keyboard_pans_the_focused_canvas...`
  (C3), `test_node_extent_stays_inside_the_sheet_after_zooming_in` (C5,
  though see caveat below), `test_fit_shows_the_whole_graph...` (C6).

## The blocking dead end — read this before touching wirePan again
`test_drag_on_empty_canvas_pans_both_axes...` (C1) and
`test_drag_starting_on_a_node_moves_it_and_does_not_pan` (C2) both fail:
**`els.wrap.scrollLeft -= ...` assigned inside a `pointermove` handler on the
real, server-rendered `#canvas-wrap` has zero effect** — confirmed by
extensive isolation (all via ad-hoc `console.log`/`page.evaluate` probes,
since removed):
- Plain `page.evaluate("...scrollLeft = 33...")` on `#canvas-wrap`, OUTSIDE
  any event handler, DOES work (scrollLeft becomes 33).
- Native browser scrolling of the SAME element (arrow keys with it focused)
  DOES work — this is C3, and it passes.
- The exact same `scrollLeft -=` line, in a *freshly created* `<div>`
  (same CSS class `canvas-viewport`, same `tabindex=0`/`role=group`, same
  ancestor chain — appended as a child of the real `#canvas-region`, even
  with an SVG+rect inside identical to the real markup), scrolls correctly
  when dragged.
- Removing `setPointerCapture`, removing `preventDefault`, and disabling
  every production stylesheet were each tried and made no difference (the
  last one broke hit-testing entirely, so wasn't conclusive).
- So it is not CSS, not event-handler wiring, not pointer capture, not
  preventDefault — it is something specific to the pre-existing
  `#canvas-wrap` DOM node (server-rendered, present since F-004/F-015) that
  defeats a pointer-triggered scrollLeft write and *only* that combination
  (native scroll and out-of-handler JS writes both still work on it).
- **Not yet tried:** bisecting by removing shell.html elements one at a time
  from the real page (start with the `data-graph` attribute persistUI sets,
  then the existing pointerdown/pointerup listeners on ports and node
  handles elsewhere in graph.js, then the SVG's `foreignObject`/`<g>`
  children) to find what specifically differs from the ad-hoc div. Also
  worth trying: a completely vanilla Chromium page fetched via `curl`/saved
  HTML of the rendered DOM (to rule out a Playwright/CDP-specific quirk tied
  to this exact page's script-injected content), and checking the installed
  Chromium version's known bug tracker for "scrollLeft pointermove" issues.

## Next step for whoever picks this up
1. Solve the scrollLeft mystery above, or if it resists, consider routing
   pan through `element.scrollBy()` or `scrollTo()` instead of `+=`/`-=` on
   the properties directly (untested — may hit the same wall, since the
   evidence points at the write itself being dropped, not at the delta
   math).
2. Fix `_use_panzoom_css`'s test helper if the mechanism changes.
3. Re-run `pytest tests/e2e/test_graph.py -k "pan or zoom or Fit or fit"`,
   then the full suite (`pytest tests/ -q`, baseline 726 passed at `dc2337f`)
   and `flake8 src/ tests/ scripts/`.
4. C5's test passed in this state, but audit it once C2 is fixed — with the
   node-drag itself silently blocked by the same scrollLeft-adjacent issue
   (or, separately, by the palette overlay covering a node spawned at
   (16,16) when expanded — a second, distinct occlusion issue also worth
   checking against the `_inside`-style tests before trusting a "passing"
   drag-based assertion), it may have been passing for the wrong reason
   (node never actually moved, so trivially inside the sheet).
5. Only then open the PR — don't open one for code known not to satisfy its
   own acceptance criteria.

## Do not repeat these dead ends
- Not the CSS cascade (production `.canvas-svg{width:100%}` etc. — already
  worked around via the test's own style injection + resize dispatch).
- Not `setPointerCapture`, not `preventDefault`, not `stopPropagation`.
- Not `touch-action`/`contain`/`overscroll-behavior`/`will-change` on any
  ancestor — computed styles on `#frame`/`#canvas-region`/`#canvas-wrap` are
  unremarkable (dumped and compared, all `none`/`auto`).
