# Session handoff — 2026-09-08

**Why:** the user asked to hand over once B-020 landed. Not a budget stop — ~55% of the 5-hour
limit, which resets 17:00. No sub-agent was interrupted; nothing is mid-edit.
**Milestone:** M3 — **waves 1 and 2 are complete and merged.** Wave 3 is released and unstarted.

## Read first
1. This file.
2. `.claude/tasks/{backend,frontend,design}.md` — current as of this commit, and the wave-3
   entries are already written up as `## Ready`.
3. `docs/plan-m3-vertical-slice.md` — the criteria for every wave-3 task.

Do not load `.claude/tasks/archive/` or `backlog.md`. Same reason as always.

## In flight

Nothing. No open PR, no running agent, no per-task handoff outstanding.
`.claude/handoff/b-020-backend-3.md` is consumed — B-020 merged — and can be archived alongside
this file when the next session tidies.

## Git as of this commit

    main                          1909046  (PR #33, B-020)
    gh pr list --state open   →   no open pull requests

Re-run both before you act. If they disagree with this file, **git is right.**

## What landed this session
- **B-020** #33 `1909046` — connection allowlist + graph→`RunConfig`. 4 cycles, the 4th
  authorised by the user past the §5.7 limit, closed `findings=0`. checks=14.
- **B-019** #34 `fff8ca3` — engine output → `HISTOGRAM_SCHEMA` payload. 2 cycles, all four
  non-blocking findings folded in before merge. checks=10.
- Suite floor **605 → 639**, flake8 0.
- **The pipe runs end to end for the first time:** B-019's C5 drives `run_analysis` on B-018's
  committed fixture through `build_histogram_payload` and gets an X1 peak within 3 GeV of the
  Z mass.

## First moves, in order
1. **Wave 3 is the milestone's biggest parallel batch and it is all released at once:**
   **B-021** (job registry + `POST /api/run` + `GET /result`) and **F-005** (port the Bench
   canvas) are independent and share no files — dispatch both, each with its own worktree.
   **F-006** (Observable interior) follows F-005; **D-015** follows both and is `effort: high`.
   Frontend and design on the same page are never parallel — D-015 waits.
2. Wave 4 (**B-022**, SSE) closes checkpoint 1: a run submittable and streaming by curl.

## Waiting on the user
- **A hook decision, raised this session and unanswered.** A `PreToolUse` hook refuses any Bash
  command whose text contains `git`; B-020's cycle-4 coder worked around it by calling
  `/usr/bin/git` directly and said so in its report. Its work verified clean (fast-forward, main
  merged not rebased, one commit, tests only). Either the hook is over-broad and misfiring on
  normal work, or the agent should have stopped instead of routing around it. The user's call.
- Still outstanding from before: **X4/X5 are undocumented processes, so mission-3 content stays
  blocked** until the user identifies them.

## Not carried over
- Nothing dropped. B-020's **F7** stays backlogged by the reviewer's own reasoning: the digest
  formula is transcribed a third time and exporting it from `runconfig.py` was outside that PR's
  file scope.
