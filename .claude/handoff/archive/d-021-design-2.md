# D-021 design — handoff, cycle 2 @ 90%

The watchdog fired at 90% on this cycle's **first tool call** (`~/.claude/fce-usage.json`:
`five_hour_pct: 90`, resets 1790109600 = 22:40). Almost nothing of cycle 2 was affordable.
No verification was run this cycle and **no green claim is made below.**

- Branch: `task/d-021-canvas-frame-pan` @ `7b1c210`, PR #60 (not updated; body still cycle 1's)
- Criteria: C1–C12, 12 total — C1–C10 met at cycle 1 and unre-measured since the F2 edit;
  **C11 and C12 open**.
- Findings: **F3 fixed** (`01b140c`), **F2 code fixed but unverified and unprobed** (`7b1c210`),
  **F1 and F4 untouched**.

## What was done

1. **F3** — `git rm .claude/handoff/d-021-design.anchor.md` on the branch, commit `01b140c`.
   `git diff --stat main...HEAD` is now three files, all under `docs/design-explorations/`.
   The anchor's content is already in the primary checkout (orchestrator copied it); do not
   re-create it on the branch.
2. **F2** — `docs/design-explorations/canvas-frame.html:355-363`. `applyZoom` now takes a
   three-term `Math.max` per axis: `SHEET_MIN`, the viewport term, and
   `max(node.x) + NODE_W + SHEET_PAD` (resp. `.y`/`NODE_H`). The reviewer's suggested form,
   unimproved — it is the one expression that makes the sizing monotonic in the content the
   sheet holds, and no second code path was added.
   **Not run in a browser. Not probed. Treat as untested.**

## Open, in order

- **C11 / F2's probe.** New probe in `canvas-frame-no-h-scroll`: at 1920, drag `n5` toward the
  far edge at 50%, zoom to 200%, assert the node's surface extent is inside the scroll range.
  Must go red when the third `Math.max` term is removed. Report both transcripts.
- **C12 / F1.** Replace the `covers` element-rect comparison at `verify.py:9077-9078, 9095`
  with `document.elementsFromPoint(x, y)` containing `.canvas-grid`, at the four corners and
  centre of `#canvas-viewport`. Must go red under the reviewer's mutation (backing paper/grid
  rects painted over part of the sheet, SVG element size untouched). Report both transcripts.
- **F4.** `verify.py:8938-8952` — swap the single click + `wait_for_timeout(250)` for
  `page.wait_for_selector(f'{region}[data-state="{want}"]')`.
- **Re-measure C6/C8/C9** after the F2 edit: the sheet dimensions change at every zoom and
  C9's load zoom depends on them.
- **PR body:** append C11 and C12 with evidence; do not rewrite C1–C10.

## Dead end / trap to check first

`moveNode` (canvas-frame.html:439-440) clamps `n.x` to `sheet.w - NODE_W`, and `applyZoom`
now reads node extent to compute `sheet.w`. Confirm the two do not feed each other — if
`moveNode` ever calls `applyZoom`, the clamp and the sizing become mutually recursive. It did
not appear to on a read, but it was not exercised.

## Verification

None this cycle. Last known state is cycle 1's, at `85f4665`: `--canvas-frame` 54 probes PASS,
`--all` red set `{board-lane-fill}` = `main`'s, difference empty. The 54 floor still stands and
must be re-established, then grown by C11's probe.
