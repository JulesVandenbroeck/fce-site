# D-002 design coder — cycle 2 handoff (written at the 90% watchdog)

**Written in the worktree, deliberately UNTRACKED.** The harness refused a write to the
primary checkout, and committing it here would put a path outside the file scope into C6's
`git diff main...HEAD --name-only`. Cycle 1's anchor was left untracked for the same reason
(PR #24 deviation 7). Copy it to `.claude/handoff/` in the primary checkout from
`.claude/worktrees/agent-ac4c06436a85b453e/.claude/handoff/d-002-design-cycle2.md`.

**Status: cycle 2 is COMPLETE and pushed.** This file exists because the watchdog fired at
90% after the work was done, not because anything is unfinished.

- Branch `task/d-002-tokens-work`, head `d869d7e`, pushed to origin as a fast-forward from
  `93c4b14`. Worked detached from `origin/task/d-002-tokens-work`; no second worktree, no
  branch created, no rebase, no force-push.
- PR **#24** body updated: C1–C7 preserved verbatim, C8 and C9 appended with both mutation
  transcripts, m1/m2/m3 answered, M2 ratification recorded in Deviations. Check count 9.

## What changed

- `tokens.css` — three values moved to clear WCAG 2.2 SC 1.4.11's 3:1 floor:
  `--chrome-border` `#d8cba8`→`#847c66`, `--locked-border` `#b3a98c`→`#726c59`,
  `--frozen-x3` `#b5883a`→`#a67d36`. Reasoning is written into the file beside each.
- `verify.py` — new section `tokens-nontext` (`verify.py:7284-7545`): 44 computed non-text
  pairs, 12 named exemptions each printed with its measured ratio, plus the C9 completeness
  diff (34 declared colour tokens, 34 covered) and its inverse.

## Decisions worth not re-litigating

- `--tab10-*` is EXEMPT, not raised: it reproduces matplotlib's resampled tab10 verbatim, so
  moving a value would make the token a lie. `--frozen-x3` was raised instead because our own
  renderer paints it.
- `--locked-border` ends up darker than `--chrome-border`. Forced by `--locked-fill`'s
  luminance; addressed in the comment at `tokens.css:240-247`.
- Historical ratios ("it used to be 1.39:1") were reworded out of the CSS prose entirely — the
  C2 sweep requires every `N.NN:1` literal to be recomputable from the shipped tokens, and a
  former value cannot be.

## Dead ends already paid for

- The word `inter` inside "user-inter*face* component" trips `tokens-fonts`' banned-face scan.
- The bare word `EXEMPT` in a docstring trips `no-fabricated-identifiers` as an undefined name.
- Bash here refuses `cd X && …` and `VAR=y cmd` forms; run scripts from files with absolute
  paths instead.

## Verification at head

`verify.py --all` exits 1 with `board-lane-fill` as the only failing section (the gate that is
red on `main`). `flake8` exit 0. Counts: `all_results.append` 71, `results.append\|line(` 267.
`git diff main...HEAD --name-only` confined to `verify.py`, `tokens.css`, `static/fonts/**`.

## Next step

Nothing for the coder. The orchestrator dispatches the cycle-2 reviewer on PR #24.
