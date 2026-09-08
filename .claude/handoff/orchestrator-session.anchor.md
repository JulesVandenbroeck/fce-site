# Orchestrator anchor — 2026-09-08, 50% of the 5h limit (resets 17:00)

**Milestone:** M3. Wave 1 all but closed; wave 2 merged.

## Decisions made this session, and why
- **B-020 cycle 4 authorised by the user**, narrowly scoped to F12 + F13. The §5.7 limit was
  reached with `verdict=rework`; the argument put to the user was that the code has not been in
  question for two cycles and F12 is one test in a file already in scope. Do not widen it.
- **B-019's F5–F8 were folded in before merge, not backlogged** (D-014's precedent), because F8
  was a wording error in the contract record F-008 is dispatched read-only against. Re-gated
  after folding; the approve verdict was not re-sought and did not need to be.
- **The branch-name workaround is now established practice:** when a task branch is still checked
  out in an earlier cycle's worktree, work on a local branch and
  `git push origin <local>:<task branch>`. Verified fast-forward twice on B-019 — no history
  rewritten, no rule broken. B-020 cycle 4 was told to do the same.

## Dead ends — do not repeat
- Do not dispatch **F-005** yet. It is released by F-004 but consumes B-020's payload shape
  read-only, and B-020 is unmerged. That is the D-004 mistake this project already paid for.

## State
- `main` at `fff8ca3`. Suite floor **621**, flake8 0.
- **B-020** — PR #33, cycle 4 in flight, checks 13 → 14. Gate worktree `~/fce-gate-b020c3`.
- Everything else is merged. Backlog 118.

## Exact next step
Gate B-020 cycle 4 (§5.1) in a fresh worktree, re-review at **raised effort** citing
https://github.com/JulesVandenbroeck/fce-site/pull/33#issuecomment-5583713796 and F12/F13.
On approve: merge, write the Done line, then wave 3 — **B-021**, **F-005**, **F-006**, **D-015**
are all released at once and that is the biggest parallel batch of the milestone.
