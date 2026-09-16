# Session handoff — 2026-09-16

**Why:** the user called the handoff. 1 sub-agent recalled (D-016, design) and handed off.
**Milestone:** M3 — **all coding work is merged.** Only D-016 (styling) stands between here and checkpoint 2.

## Read first
1. This file.
2. `.claude/handoff/d-016-design-1.md` — only if you are re-dispatching D-016. It carries the reading
   already done and one open question; the criteria live in `design.md`, not there.
3. `.claude/tasks/{backend,frontend,design}.md` — current as of this commit.

Do not load `.claude/tasks/archive/` or `backlog.md`. Same reason as always.

## In flight

| Task | Role | Branch | PR | Cycle | State | Handoff |
|---|---|---|---|---|---|---|
| D-016 | design | none — never created | — | 1 | not started: no branch, no commit, no CSS | `handoff/d-016-design-1.md` |

## Git as of this commit

    gh pr list --state open  ->  []
    main  a893d17 orchestrator: D-016 dispatched — last M3 task, checkpoint 2 follows
    no task/d-016-* branch exists on origin or locally
    working tree clean

Re-run both before you act. If they disagree with the table above, **git is right.**

## What this session merged

B-024 #45 `849f832` · F-007 #46 `1fdb8e6` · F-008 #47 `7472675`.
Suite floor **697 passed**, `tests/e2e/` **74** nodeids, flake8 0 — verified on `main` at `7472675`.

**M3's pipe is real end to end in a browser:** place four nodes, connect them, press Run, watch the phase
and percentage stream, and a Z peak draws at **90.6 GeV** from the fixture. Reproduced in three
independent worktrees.

## First moves, in order
1. **Re-dispatch D-016** (design, cycle 1 — it never started, so `isolation: "worktree"` is still correct,
   or reuse `.claude/worktrees/agent-a1a7be38838a932a5`). Criteria C1-C13 are in `design.md`'s entry.
   **Answer its open question first:** measure whether `.canvas-region`'s row layout can hold
   `#run-control` + `#results` beside a 704px canvas at 1440 at all (~48px left over). If it cannot, the
   dispatch's prescribed `overflow-x: auto` fix is wrong and the region must stack — C1's property is the
   `elementFromPoint` check, not the mechanism.
2. Then **M3 checkpoint 2**: report to the user what works, the exact command to try it, what was
   overruled or backlogged, and the fixture question below.

## Waiting on the user
- **The fixture normalisation decision, raised this session and unanswered.** B-018's fixture keeps a
  2000-event slice but its MC weights are full-sample production normalisations, so weighted MC is ~6
  events against ~712 raw pseudo-data. The physics is correct and the shapes agree (both peak in
  `90.0-91.2 GeV`), but `yMax = max(stack, data)` renders the MC stack as a ~1px sliver and pegs every
  populated ratio bin at the panel clip: **correct and unreadable**. Options are scaling the fixture
  weights, normalising at demo time, or accepting it as a fixture artefact real datasets will not have.
  It does not block D-016; it decides what the checkpoint demo shows. Backlogged, evidence in
  `backend.md` `## Contracts in force`.

## Not carried over
- Nothing dropped. Backlog 131 -> **134** this session (B-024 F4, F-007 F11, the fixture normalisation item).
- Gate worktrees `~/fce-gate-b024`, `~/fce-gate-f007`, `~/fce-gate-f008` are left in place, detached, each
  with a venv. Reuse or `git worktree remove` them; they are not branches.
