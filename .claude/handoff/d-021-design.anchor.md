# D-021 design anchor (50% mark)

Branch `task/d-021-canvas-frame-pan` in worktree `.claude/worktrees/agent-a3f0c5c43ddaa00dd`
(reset to origin/main 062103d). Venv `.venv-d021` (playwright). Not yet committed at write time.

## Root cause (confirmed by measurement, pre-fix)
One bug, three symptoms: the sheet was a fixed 1800x1200 SVG. At 1920x900 the viewport
measured `scrollWidth == clientWidth == 1920` -> zero horizontal pan range (user's defect 2);
at 50% zoom both axes had zero range and the area beyond the sheet was plain `--panel`
(defect 1); and a node past the window edge was unreachable rather than off-screen (PR #59 F1).

## Fix, as implemented
- `canvas-frame.html` script: `SHEET_MIN_W/H` + `SHEET_PAD=600`; `applyZoom()` now grows the
  sheet to `max(min, ceil(clientW/zoom) + 2*PAD)`, rewrites viewBox + width/height + the two
  backing rects; `resize` listener calls it. Grid stays in surface units (scales with zoom).
- `clearBand()` reads palette/mission-panel/zoom-controls/drawer rects; `fit()` targets that
  band and centres; `init()` ends with `fit()` so the page opens on the whole pipeline.
- Node layout recompacted to a 212-unit pitch, origin (700,500).
- `canvas-frame.css`: palette expanded 368 -> 256 (`--space-7 * 4`) to widen the clear band.

## Measured (post-fix)
1440 load: zoom 81%, all 5 nodes in band. 1024: 50%, all 5 in band. 768: 50%, n1+n5 partly
under panels but pannable. 1920: 126%. Diagonal drag moves both axes at 100% and 50%.
Dead end: a 5-node left-to-right chain cannot fit the band at 100% -- opening on Fit is the fix.

## Next steps (open)
1. Re-run measure.py with scroll set mid-range before each drag (200% starts at max edge, so
   dScrollLeft read 0 -- test artefact, range was 2400).
2. C8 pixel sampling (pip install pillow in .venv-d021) + screenshots at 1440/1024/768.
3. verify.py C10: drop `CANVAS_FRAME_DESIGN_WIDTHS` (use `SHELL_DESIGN_WIDTHS`; do NOT rename
   it -- that would edit other sections), read back palette/panel state and label from measured;
   add scroll-range probes (count must stay >= 27).
4. Update the recommendation prose (fixed-1800x1200 sentence; "Fit measured against viewport").
5. Red set on main vs branch, commit, `gh pr create`.
