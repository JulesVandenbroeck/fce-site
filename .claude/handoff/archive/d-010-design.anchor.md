# D-010 design anchor — cycle 3

Worktree: `.claude/worktrees/agent-a9eb21b29aea98409`, DETACHED at cfd2a1d (branch
`task/d-010-page-shell` is checked out in two other stale worktrees, so push with
`git push origin HEAD:task/d-010-page-shell`). PR #25.

Scope: shell.html / shell.css / verify.py only. Cycle 3 = §5.7 loop limit.

## To resolve
M5 (C7 length_re unit alternation), M6 (canvas text scaled illegible), m4, m5, m6.

## Decisions
- **M6 fixed, not overruled.** `.canvas-wrap` is now a FIXED 704x512 surface
  (`width: calc(var(--space-7)*11)`, `flex: 0 0 auto`, `margin: auto`); `.canvas-region`
  keeps `overflow:auto` and scrolls at 1024/768. Dropped the region's
  `justify-content/align-items: center` — centring makes an overflowing item unreachable;
  flexbox zeroes auto margins on negative free space, so `margin:auto` is the safe form.
  Measured: scale 0.9961 at all three widths, title 13.95px, body/toggle 11.95px,
  region scrollWidth 736 vs client 400 (1024) / 384 (768), page has no h-scroll.
  Rejected an intermediate min scale (0.82): neither 1024 nor 768 avoids scrolling anyway,
  so it would scroll *and* shrink the type.
- **New section `shell-canvas-text-legible` (C10)** — check count 9 -> 10. Constants
  `SHELL_CANVAS_MIN_SCALE = 0.95`, `SHELL_CANVAS_MIN_TEXT_PX = 11.0` at verify.py:6205.
- M5: replace the unit alternation with a generic `[a-zA-Z]+|%` unit, exempt by value.

## Next steps (in order)
1. Write `check_shell_canvas_text_legible`, register it in main()'s `args.all or args.shell`
   block (~verify.py:7500) and in `SHELL_SECTIONS` (~8570). Raise the AST floors.
2. M5 regex in `check_shell_shipped_tokens` (~verify.py:6690).
3. m4 (C9 docstring: the 2 extra registrations are NEW, from the --section rewrite),
   m5 (docstring: 384.0 at 768 is exactly the floor, intended), m6 (deviation note: why
   single-row was kept over a reflow).
4. `verify.py --all` (PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright), flake8, pytest 413,
   mutation transcripts for M5 and M6, screenshots at 1440/1024/768, append to PR #25 body.
