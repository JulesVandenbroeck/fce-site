# Orchestrator anchor — 2026-09-02

**Budget:** 5h usage at 76% (soft). Window resets 18:50. No new work opened past this point.

## Decisions made this session, and why
- D-002's work was rescued: the only copy was one unpushed local commit on
  `task/d-002-tokens-work`. Pushed first thing. The dispatched branch `task/d-002-tokens` is
  empty and stays that way — do not try to move commits onto it.
- **Ruling on `check_git_diff`** (`verify.py:1885-1950`): narrowed from "ships nothing under
  src/tests/content" to a two-entry allowlist (`tokens.css`, `static/fonts/`). Any future task
  shipping into those trees trips it and needs a fresh ruling. Intended, not a defect.
- **M2 ratified**: `verify.py:6324`'s `main()` edit is behaviour-preserving and my own `Check:`
  commands forced it. Declared, not charged.
- Backend trio released by the user but **strictly serial** — B-013 (#17), B-008 (#19),
  B-014 (#18), in that order, one at a time. This overrides the old parallel pattern.

## Dead ends — do not repeat
- `git pull --ff-only` on `main` fails whenever bookkeeping is unpushed and a PR merged
  remotely. Correct move is `git merge origin/main` then push. Never rebase.
- `verify.py --all` takes >2 minutes; a 120s Bash timeout kills it. Use `timeout 540`.
- `git worktree add` fails on a registered-but-missing path — `git worktree prune` first.

## In flight
- **D-002 cycle 2** (PR #24, head `93c4b14`), design-coder, own worktree. C8/C9 close M1's two
  halves. checks 7 -> 9. Contract task: do not merge with an open finding against the tokens.

## Next step, exactly
Collect the D-002 cycle-2 report, run the §5.1 gate in `~/fce-gate-d002`, dispatch the reviewer.
Then D-010 (ready, input 328.0 x 300.0px opened / 80.5px collapsed) or B-013 — serial, one only.
