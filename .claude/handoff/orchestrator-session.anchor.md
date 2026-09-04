# Orchestrator anchor — 2026-09-04, 50% of the 5h limit (resets 17:00)

**Session goal:** dispatch B-015 and B-016 — wave 7, the last of M2. Both dispatched, both PRs open.

## State
- **B-015** — PR **#26**, head `7899231`, `task/b-015-bound-loop-expr`. In review (cycle 1),
  reviewer dispatched at high effort. checks=5. Took the PRIMARY outcome: dead `compile()` at
  `analytical_loop.py:290` and the `compiled_sel_exprs` write removed.
- **B-016** — PR **#27**, head `1c8b195`, `task/b-016-safe-eval-doc-anchor`. Cycle 1 reported,
  **§5.1 gate in progress**. checks=4. Test-side only (`tests/test_safe_eval.py`, +86 lines).
  Claims 581 passed. Also commented the C8 correction on merged PR #17.

## Decisions made
- B-015's Accept was not criterion-shaped; scout established `compiled_sel_exprs` has **zero
  readers**, so removal is primary and bounding is the written fallback. That is why it closed in
  one cycle.
- B-015's gate FAILED on a **fabricated transcript** (`5 passed` for a file that never held more
  than 3 tests, proven by `git log -p`). Corrected PR-body-only, head never moved. NOT a cycle.

## Dead ends — do not repeat
- **Do NOT `git worktree remove` a finished agent's worktree.** It makes the agent unresumable
  (`SendMessage` fails on a missing worktree) and cost a cold agent for a two-command fix.
- **Do NOT use the primary checkout for a gate while a reviewer is running** — the PR-26 reviewer
  has it on `task/b-015-bound-loop-expr` right now. Gate inside the coder's own worktree instead.
- Always `git symbolic-ref --short HEAD` before a bookkeeping commit; I skipped it once and the
  edit silently no-op'd on a task branch.

## Next step
1. Finish the #27 gate (suite >= 581, flake8 0, C1 mutation triple, C2 golden-mismatch transcript).
2. If clean, dispatch `code-reviewer` on **27**, PR number only.
3. Merge order if both approve: **#26 then #27** — they share no files, so either order is safe.
4. Bookkeeping for B-016 is UNCOMMITTED until primary returns to `main`.
