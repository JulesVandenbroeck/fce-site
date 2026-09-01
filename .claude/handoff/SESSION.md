# Session handoff — 2026-09-01 (orchestrator context 90%)

**Why:** orchestrator context reached 90%. No sub-agents were running at handoff — all four
completed and reported. Nothing was cut off.
**Milestone:** M1 — **D-006 merged, so all three node-graph styles now exist. D-007 is unblocked
and is the next dispatch. It is the user's checkpoint.**

## Read first
1. This file.
2. `.claude/tasks/design.md` — rewritten clean this session; D-007 sits in `## Ready` with the
   one warning its dispatch must carry.
3. `.claude/tasks/backend.md` — unchanged this session. B-008 is the live one.

Do not load `.claude/tasks/archive/` or `backlog.md`.

## The one thing that will confuse you if you do not read it here

**`verify.py --all` exits 1 on `main` and that is correct.** Exactly one section is red:
`board-lane-fill`. It is D-006's C10, overruled in writing on the user's ruling (PR #20 comment
`5497106719`), and left registered and red deliberately so the constraint stays visible.
**It is not a regression, it is not yours, and it must not be deleted, disabled, relabelled or
downgraded to make the run green.** 62 of 63 sections pass, 265 assertions.

## In flight

| Task | Role | Branch | PR | Cycle | State | Handoff |
|---|---|---|---|---|---|---|
| B-008 | backend | `task/b-008-path-filter-safe-eval` | #19 | 3 | **stopped by the user last session, never resumed this one.** HEAD is cycle 2's `fba2ad6`; uncommitted +79 lines in `tests/test_path_filter_exprs.py` in `.claude/worktrees/agent-a209cb7cb16742776`. **At the §5.7 limit — if cycle 3 does not close `0R/0M`, escalate, do not open a cycle 4.** | `b-008-cycle3-interrupted.patch` |
| B-013 | backend | `task/b-013-safe-eval-findings` | #17 | 1 | **HELD BY THE USER.** Gate reproduced (`4d5f374`, 413 passed); review dispatched 2026-08-31, no verdict ever returned. Do not re-dispatch without the user. | — |
| B-014 | backend | `task/b-014-api-contract-findings` | #18 | 1 | **HELD BY THE USER**, same reason. Gate reproduced (`3e3550f`, 565 passed). | — |

## Git as of this commit

    origin/main = 0aee604 (Merge PR #20, D-006 Board)
    open PRs: #19 B-008 (cycle 2 reviewed, rework), #18 B-014 (held), #17 B-013 (held)
    gate worktree ~/fce-gate-d006 exists, detached — reusable, its venv is the primary checkout's

Re-run `git branch -a` and `gh pr list --state open` before you act. If they disagree with the
table above, **git is right.**

## First moves, in order
1. **Dispatch D-007.** Entry is in `.claude/tasks/design.md` `## Ready`, dependencies all merged.
   Its dispatch must tell the coder about the known-red `board-lane-fill` section, and that
   D-007 does not touch `verify.py` so it must not try to fix it.
2. **Then stop — D-007 is the checkpoint.** The user picks Beamline / Bench / Board, and that
   choice is what unblocks D-002.
3. B-008 cycle 3 only if the user wants it before the checkpoint; it is independent of M1.

## Waiting on the user
- **The M1 style choice**, at D-007. Everything in design after that depends on it.
- Whether to unhold #17 and #18.

## Not carried over
- D-005's **m7** (the "chips render identically" PR-body claim, three cycles uncorrected) is
  recorded in `design.md` `## Done` and is not being chased.
- The C10 argument is closed by the user's ruling. Do not reopen it without them.
