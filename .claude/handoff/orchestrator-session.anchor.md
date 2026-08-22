# Orchestrator anchor — 2026-08-22 (session 2), 53% context

**Milestone:** M2, last task. B-012 is the checkpoint; everything else in M2 is merged.

## State
- B-012, PR **#15**, branch `task/b-012-parity-proof`, head **`57939b5`** (cycle 3).
- checks=**10** (C1-C10, all with Check:/Expect: now in PR #15's body — that closed R3).
- Cycle 1: 3R/2M/4m (comment 5381713608). Cycle 2: 1R/1M/1m (comment 5381993475).
  Cycle 3 dispatched and returned; §5.1 gate passed at `57939b5`: **413 passed, flake8 0**,
  `src/ content/ pyproject.toml` byte-identical to main. Re-review dispatched next.
- **Cycle 3 is the §5.7 limit.** If the re-review is not clean, STOP and escalate to the user.
- Suite floor 398 -> 406 -> 411 -> **413**.

## Decisions
- Interrupted cycle-2 work (177 uncommitted lines) recovered, not redone; patch saved at
  `.claude/handoff/b-012-cycle2-interrupted.patch`. Not counted as a cycle.
- M3 diagnosed a **cycle** under §5.4 clause 3 (fix-induced by M1's own fix, gated by no
  prior criterion). R3 was a dispatch defect and did not by itself make a re-specification.
- Gate runs in `~/fce-gate-b012` (detached worktree) with the PRIMARY venv — B-012 touches
  no `src/`.

## Dead ends / hazards
- `cd` into `.claude/worktrees/**` is denied by `.claude/settings.json`; use `git -C`.
  The cycle-3 coder ALSO could not Read there and worked around it with git plumbing —
  **relay to the user; that deny rule may be over-broad.**
- Uncommitted on `main`: the whole token-diet workflow rewrite (12 modified + 4 new files
  under `.claude/`, plus CLAUDE.md). User has not been asked whether to commit it. ASK.

## Next step
Collect the cycle-3 re-review -> post it verbatim to PR #15 -> if clean,
`gh pr merge 15 --merge`, write the `## Done` line + archive post-mortem, then **STOP and
report the M2 checkpoint to the user** (§7).
