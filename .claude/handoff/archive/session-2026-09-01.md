# Session handoff — 2026-09-01 (orchestrator context 90%)

**Why:** orchestrator context reached 90%. **No sub-agents were running** — all reported and
were collected. Nothing was cut off.
**Milestone:** M1 — D-007 is at **cycle 2, delivered and gate-passed, awaiting its review.**
It is the checkpoint the user reads to choose Beamline / Bench / Board.

## Read first
1. This file.
2. `.claude/tasks/design.md` — D-007's entry in `## In progress` carries the full cycle record
   and the exact next move. It is current as of this commit.
3. `.claude/tasks/backend.md` — untouched this session. B-008 still cycle 2, #17/#18 still held.

Do not load `.claude/tasks/archive/` or `backlog.md`.

## The one thing that will confuse you if you do not read it here

**`verify.py --all` exits 1 on `main` and that is correct.** Exactly one of 65 sections is red:
`board-lane-fill` — D-006's C10, overruled on the user's ruling (PR #20 comment `5497106719`),
left registered and red on purpose. Not a regression. Must not be deleted, disabled, relabelled
or downgraded. Confirmed this session by a full run: exit 1, **265** passing assertion lines.
(A previous `SESSION.md` said "63 sections / 62 pass" — that was **wrong**. 65/64 is right.)

## In flight

| Task | Role | Branch | PR | Cycle | State | Handoff |
|---|---|---|---|---|---|---|
| D-007 | design | `task/d-007-index` | #21 | 2 | **Delivered `1e9b369`. §5.1 gate fully reproduced — do not re-run it. Awaiting cycle-2 review.** | — |
| B-008 | backend | `task/b-008-path-filter-safe-eval` | #19 | 2 | untouched this session; at the §5.7 limit | `b-008-cycle3-interrupted.patch` |
| B-013 | backend | `task/b-013-safe-eval-findings` | #17 | 1 | **HELD BY THE USER** | — |
| B-014 | backend | `task/b-014-api-contract-findings` | #18 | 1 | **HELD BY THE USER** | — |

## Git as of this commit

    origin/main = fe2b917 (+ this bookkeeping commit)
    open PRs: #21 D-007 (cycle 2, gate passed, unreviewed), #19 B-008, #18 B-014, #17 B-013
    PR #21 head = 1e9b369
    gate worktrees (detached, reusable, safe to remove): ~/fce-gate-d007, ~/fce-gate-d007b,
      ~/fce-gate-d007c, and ~/d007-preview (user-facing, at the STALE cycle-1 head 71c6022)

Re-run `git branch -a` and `gh pr list --state open` before you act. If they disagree, **git is right.**

## First moves, in order
1. **Dispatch `code-reviewer` on PR #21, effort medium, with the PR number and the prior review
   URL (`#issuecomment-5498754050`) and nothing else.** The §5.1 gate is done and passed —
   re-running it wastes a browser suite. Ask for `M2 fixed`/`M2 still open`, all **8** criteria
   re-run, incremental diff since `19bc819` (one file: `README.md`), and an **independent check
   that the `docs/design-brief.md` citations resolve** — this task has shipped a false citation
   twice, once to `api.md` (M1) and once to `design-brief.md` (M2).
2. **Warn that reviewer:** the previous review's own line numbers for M2 were wrong
   (`:43-44`/`:51-54`). The correct lines are **`design-brief.md:168`** and **`:176-179`**,
   verified at the gate. The coder used the correct ones.
3. At 0R/0M: merge `gh pr merge 21 --merge`, refresh the preview worktree to the merged head,
   and **STOP** — D-007 is the checkpoint.
4. **Cycle 3 is the last one.** If the review reopens M2 or finds a new major, fix it once; if
   that does not close it, escalate to the user. No cycle 4.

## Waiting on the user
- **The M1 style choice**, at D-007. Everything in design after it depends on it. The coder
  recommends **Board**; the user is free to overrule.
- Whether to unhold #17 and #18, and whether to resume B-008.

## Not carried over
- D-005's **m7** — still not chased, recorded in `design.md` `## Done`.
- D-007's m1/m2/m3 are **backlogged and named** (backlog 76 → 79). Do not fold them into D-007.
- The D-006 C10 argument is closed by the user's ruling. Do not reopen it.
