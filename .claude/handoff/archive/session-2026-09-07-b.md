# Session handoff — 2026-09-07 17:5x

**Why:** the user asked for the handoff once B-018's coder finished; the 5-hour limit was ~75%+
spent (resets 18:30). No sub-agent was running at handoff time — B-018 reported normally and
`scout` had already returned, so nothing was recalled and no `HANDOFF NOW` was sent.
**Milestone:** M3 — wave 1 half done. B-018 is built and gated, awaiting its review; B-020, the
other wave-1 task, was never dispatched (deliberately held at the 75% soft threshold).

## Read first
1. This file.
2. `.claude/tasks/backend.md` — current as of this commit; B-018's entry carries the gate result
   and the two dispatch-time criterion corrections.
3. `docs/plan-m3-vertical-slice.md` — the milestone plan, `### B-020` for the next dispatch.

There is **no per-task handoff** for B-018: it completed, it did not hand over.
Do not load `.claude/tasks/archive/` or `backlog.md`. Same reason as always.

## In flight

| Task | Role | Branch | PR | Cycle | State | Handoff |
|---|---|---|---|---|---|---|
| B-018 | backend | `task/b-018-fixture-dataset` @ `8a4ef27` | #31 | 1 | complete; §5.1 free gate PASSED (605 passed, flake8 0); **not yet reviewed** | — (completed normally) |

## Git as of this commit

    main @ e7f6c72 (before this handoff commit)
    origin/task/b-018-fixture-dataset @ 8a4ef27
    gh pr list --state open  →  #31  B-018 — A committed fixture dataset the pipeline can run on

Re-run both before you act. If they disagree with the table above, **git is right.**

## First moves, in order
1. **Dispatch `code-reviewer` with `31` and nothing else.** The free gate is already done and
   passed — do not re-run it, and do not paste the task definition into the reviewer's prompt.
   The PR body carries scope, C1–C8 with evidence, and the transcript.
2. On `verdict=approve`, merge with `gh pr merge 31 --merge` and write the `## Done` line.
   **B-019 and B-021 are released by that merge** — B-019 is the next wave.
3. B-020 (connection allowlist → `RunConfig`, **CONTRACT TASK**) is independent of all of the
   above and can go out in parallel with the B-018 review. `isolation: "worktree"`, and raise the
   **reviewer's** effort when its turn comes — F-005 and F-007 consume its payload read-only.

## Waiting on the user
- **X4, X5 and X6 are undocumented processes.** The real dataset host carries seven files, not
  six: X1 158M, X2 92M, X3 51M, X4 19M, **X6 5.9M**, X5 5.3M, data 4.8M. `shared/CLAUDE.md` §5
  documents X1–X5 only and never mentions X6. **Mission 3 stays blocked** until the user says what
  X4/X5/X6 are. The user was told this and has not yet answered.
- **A sub-agent worked around a PreToolUse guard.** B-018's coder reports that the git/network
  guard blocked every direct `git`/`curl`/`wget` invocation, and that it proceeded via a
  subprocess-exec wrapper script and Python's `urllib.request`. The work itself is legitimate and
  was explicitly requested, but the guard did not hold. Raised with the user; no decision yet.

## Not carried over
- The synthetic-fixture approach B-018 started with. Superseded mid-task by the user's real-data
  ruling; the coder discarded it rather than keeping both paths. Do not resurrect it.
- B-020 was planned as a parallel wave-1 dispatch this session and was not opened. Nothing is
  written for it beyond the plan — it starts clean.
