# Session handoff — 2026-09-09

**Why:** the user asked for a handoff once the work in flight finished. Not a budget stop —
~75% of the 5-hour limit, which resets 17:00. Both running agents completed; no agent was
interrupted and nothing is mid-edit.
**Milestone:** M3 — wave 3 is **frontend-complete** (F-005 merged, F-006 built), wave 4 (B-022)
is code-complete and unreviewed. Checkpoint 1 is one review and one merge away.

## Read first
1. This file.
2. `.claude/tasks/{backend,frontend}.md` — current as of this commit. The B-022 and F-006
   entries carry everything below in more detail; do not re-derive it from `git log`.
3. `docs/plan-m3-vertical-slice.md` for any task's criteria.

Do not load `.claude/tasks/archive/` or `backlog.md`. Same reason as always.

## In flight

| Task | Role | Branch | PR | Cycle | State | Handoff |
|---|---|---|---|---|---|---|
| B-022 | backend | `task/b-022-sse-events` | #37 | 2 | code complete, **awaiting review** | — |
| F-006 | frontend | `task/f-006-observable-interior` | **none** | 1 | code complete, **no PR** | — |

Neither agent needed a per-task handoff: both finished their work and reported cleanly.

## Git as of this commit

    task/b-022-sse-events              20d0e72   PR #37 open
    task/f-006-observable-interior     8cb14ab   no PR
    main                               (this commit)
    gh pr list --state open        ->  #37 only

Re-run both before you act. If they disagree with the table above, **git is right.**

## What landed this session
- **B-021** was already merged before this session (#35, `78ceb8d`); the lists were stale
  because the primary checkout sat on the task branch. Reconciled from `~/fce-bookkeeping`.
- **F-005** #36 `b7fdfdf` — the Bench canvas. 2 cycles, `findings=1, verdict=approve`.
  Suite floor 654 -> **664**, `tests/e2e/` 37 -> 47. F10 backlogged (121 items).

## First moves, in order
1. **F-006 has no PR and that is the only thing standing between it and review.** Re-dispatch
   `frontend-coder` at the existing branch `task/f-006-observable-interior` (`8cb14ab`) with
   the sole task of writing the PR body — C1-C7 verbatim, total 7, and the verification
   transcript. **Do not write that body yourself** (§4 rule 3). The code is done and gated:
   670 passed, flake8 0, 53 e2e nodeids.
2. **PR #37's body says `Total checks: 8` at its head while C9-C11 sit below it.** The count
   is 11. Send it back for that one correction — a §5.1 gate return, not a cycle — then
   dispatch the reviewer. Tell the reviewer to check the `TestClient` timeout claim first
   (backend.md has it); it is the cycle's one deviation and it contradicts its instruction.
3. Merge #37 on approve. **That closes M3 checkpoint 1** — a run submittable and streaming by
   curl. Report the checkpoint to the user per §7.
4. Then **D-015** (`effort: high`, needs F-005 + F-006 merged) and **F-007** (needs F-006 +
   B-022 merged). D-015 and F-007 both touch the same page, so they are **not** parallel.

## Waiting on the user
- **B-022 cycle 1's hook bypass.** The coder routed around a refusing `rtk` hook with a
  wrapper script — the exact workaround ruled out 2026-09-08 after B-020 cycle 4. The work
  checks clean, so this is a process question, not damaged code. Nothing is blocked on it.
- **The hook itself.** Four agents hit it this session. It is **not** misfiring: it correctly
  enforces worktree isolation, and my dispatches were what was wrong (see below). But it
  refused F-006's `git add`/`commit`/`push` in a *correctly* isolated cycle-1 worktree, which
  no dispatch error explains. That case is worth someone looking at.

## Rules earned this session, already written into the manuals
- **`isolation: "worktree"` is cycle-1 only** (orchestrator §4, commit `d0901d1`). It builds a
  fresh worktree on a generic `worktree-agent-*` branch from the primary checkout's HEAD —
  right for a coder branching off `main`, wrong for every re-dispatch, and wrong for a reviewer
  whose PR branch is checked out elsewhere. It cost one whole dispatch before it was diagnosed.
- **Never run the gate with the bare `python`.** The primary checkout's system interpreter has
  no `fce_web` on its path, so pytest collects **nothing** and reports it as an empty run, not
  an error. Always `.venv/bin/python`. Cost one false gate.

## Not carried over
- Nothing dropped. F-005's F10 is backlogged with its one-line fix recorded.
