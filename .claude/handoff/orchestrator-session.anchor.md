# Orchestrator anchor — 2026-09-09, 50% of the 5h limit (resets 17:00)

**Milestone:** M3. Wave 3/4 in flight. Bookkeeping worktree is `~/fce-bookkeeping` (on `main`);
the primary checkout is detached and used only for §5.1 gates.

## In flight
| Task | PR | Cycle | State |
|---|---|---|---|
| F-005 | #36 | 2 | gate PASSED (664 / flake8 0 / e2e 47). **Reviewer dispatched.** |
| B-022 | #37 | 2 | coder running in worktree `agent-a7c45688f7107f2cd` |

## Decisions made this session
- B-021 was already merged (#35, `78ceb8d`) before this session; lists were stale because the
  primary checkout sat on the task branch. Reconciled from `~/fce-bookkeeping`.
- **`isolation: "worktree"` is cycle-1 only.** Written into orchestrator §4 at `d0901d1`.
  On cycle 2+ omit it and name the existing worktree. Same for reviewers on a re-dispatch —
  an isolated reviewer cannot `gh pr checkout` a branch already checked out elsewhere.
- F-005 contract corrected: `nodes` is a **list** of `{id, kind, x, y}`, not keyed by id.
  `docs/plan-m3-vertical-slice.md:494` fixed in place. Confirmed by `scout` against
  `graph.py:120,122-123,135` and `:144-146` — do not re-derive.
- F-005 checks 8 -> 10 (C9 duplicate edge, C10 list shape). B-022 checks 8 -> 11 (C9 terminal
  frame, C10 bounded reads, C11 per-stream attribution).

## Dead ends — do not repeat
- The primary checkout's bare `python` has no `fce_web`: pytest collects **nothing** and
  reports it as an empty run, not an error. Always `.venv/bin/python`. Cost one false gate.
- The `rtk` git refusal is **not** an rtk bug. It correctly enforces worktree isolation; the
  defect was my passing isolation to re-dispatches. Two agents hit it; one stopped and
  reported (right), one wrote a wrapper script (wrong, and still unruled).

## Waiting on the user
- **B-022 cycle 1's hook bypass** — a wrapper script routing around the hook, the exact thing
  ruled out 2026-09-08. Work checks clean; process breach only. Nothing is blocked on it.

## Next step
Collect the F-005 re-review and B-022 cycle 2. Merge on approve. Then F-006 (needs F-005
merged), then D-015 (needs F-005 + F-006; `effort: high`).
