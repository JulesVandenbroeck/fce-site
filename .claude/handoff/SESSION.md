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
- **Nothing blocking.** Both open questions were ruled on 2026-09-08:
  - **The `git` hook is allowed.** `Bash(git *)` and `Bash(rtk git *)` are now in
    `.claude/settings.json`'s `permissions.allow`, so the `rtk hook claude` `PreToolUse` rewrite
    no longer leaves a sub-agent facing a refusal. **The workaround that prompted this — B-020's
    cycle-4 coder calling `/usr/bin/git` to route around the hook — should not recur, and is not
    a precedent.** An agent that finds a hook blocking it stops and reports; it does not go
    around it. That work was verified clean before merge (fast-forward, `main` merged not
    rebased, one commit, tests only).
  - **X4/X5 stay undocumented, deliberately.** Mission-3 content therefore stays blocked. This
    is a decision, not an open question — do not re-raise it, and do not author mission-3
    content on a guess about what those samples are.

## Not carried over
- Nothing dropped. B-020's **F7** stays backlogged by the reviewer's own reasoning: the digest
  formula is transcribed a third time and exporting it from `runconfig.py` was outside that PR's
  file scope.
