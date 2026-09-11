# Handoff: D-015 review, PR #39, re-review after re-spec (cycle 2), head 9e8fbf1

## Task as given
Re-review PR #39 at 9e8fbf1. Read only the diff since 636562b. Re-run every criterion. Report prior findings F5 (remainder), F6, F7, F8 as fixed / still open. Judge C12 against its restated text (horizontal only; vertical half moved to F-009).
Previous review: https://github.com/JulesVandenbroeck/fce-site/pull/39#issuecomment-5632419260
Environment: primary checkout detached at 9e8fbf1, read-only. Export PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright and use .venv/bin/python.

## Stopped because
The orchestrator sent HANDOFF NOW. The `pytest tests/ -q` run was killed before it finished (exit 144, no result).

## Not done, in order
1. `.venv/bin/python -m pytest tests/ -q`: PR body claims 677 passed. This is the only unrun part (of C9).
2. `.venv/bin/python -m flake8 src/ tests/ scripts/`: never ran, because it was chained after pytest.
3. If both are green, the verdict is likely approve with no new findings. Nothing new was found in the 2-file incremental diff (canvas.css +1/-1, observable.css +1/-13).

## Criteria run, with real output
Driver: /tmp/claude-1002/-home-julvdnbr-Documents-Phd-teaching-fce-site/be9a184f-97e4-4a60-8707-dd220d00bb65/scratchpad/drive.py, run from the checkout as `.venv/bin/python <drive.py> <scratchpad> [mut]`.
- **Scope, C7 and C8.** `git diff --name-only main...HEAD` lists shell/canvas/observable.css, base.html and shell.html. The template hunks are 3 `<link>` lines and one `<span class="mission-panel__code">` wrapper. `tokens.css` and `docs/design-explorations` are untouched. scope=pass.
- **C1.** 16 distinct computed colours were found. Every one maps to a token except `rgb(0,0,0)` on HTML/HEAD/META/TITLE, which is non-rendering and already noted in the PR.
- **C2.** 12.75, 13.76, 5.18, 5.38 and 8.9, then 5.48, 8.79, 6.2 and 7.79. All match the PR body.
- **C3 and C4.** A grep for vermillion, frozen-x1, ink-45, hex, !important and outline:none in the 3 files returns 0 hits.
- **C5.** With reduced motion: node animation `none`, opacity 1. Palette and panel transition-duration both 0s.
- **C6.** All 12 layouts (1440/1024/768 × palette × panel): scrollWidth equals clientWidth, all OK.
- **C9.** The Playwright pass (all 4 kinds, open, 4 modes, edge n2 to n3, toggles) gave errors `[]`. The pytest and flake8 part is NOT run.
- **C10.** Collapsed 159.5×103.7. Opened 159.5×232.3 in all four modes.
- **C11.** The families on screen are EB Garamond and Fira Mono. `.mission-panel__code` is Fira Mono, and `fonts.check` returns true for both.
- **C12 (restated), MET.** Node at y≈350. RIGHT edge: node x 935.4 + 159.5 ≤ svg 393 + 702. All 4 pills are inside and `elementFromPoint` hits them, and the out port is inside. LEFT edge: node x 393.0 ≥ 393, and the pills and port are inside with hits.
- **C12 mutation.** I injected `.node__interior{width:300px}` with `add_style_tag`, not a repo edit. At the right edge, pills 3 and 4 are outside (pill 4 also fails the hit test). At the left edge, pills 1 to 3 are outside and the out port is outside. Restored run: everything inside again. The check can go red.
- **C13.** Collapsed scrollHeight/clientHeight is 104/104 for n2 to n4, and the opened n1 is 233/233. The remaining literal lengths are only the sr-only 1px/-1px, the breakpoints, and a comment. The keyframe computes `matrix(1,0,0,1,0,6)` at its start, so the calc resolves to 6px as before.

## Prior findings
- F5 remainder / F8: fixed. The header at observable.css:1 is now one line with no review ID.
- F6: fixed by re-spec. C12 is restated as horizontal only, the original is kept struck through, and the F-009 backlog note is in the PR body. The horizontal half verifies and mutates red.
- F7: fixed. canvas.css:125 is now `calc(var(--space-1) + var(--border-heavy))` and resolves to 6px.

## New findings so far
- none

## Dead ends
- Do not `pkill -f 'pytest ...'` from a Bash call: the pattern matches that call's own shell and kills it.

VERDICT: pr=39 cycle=2 verdict=incomplete-handoff
