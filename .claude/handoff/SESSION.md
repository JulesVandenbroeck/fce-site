# Session handoff — 2026-09-08

**Why:** 5-hour usage limit reached 90% (resets 17:00). One sub-agent handed off; none is running.
**Milestone:** M3 — waves 1-2 merged. **Wave 3 running in series on the user's instruction**, not
parallel. B-021 is mid-cycle-2 and RED. F-005, F-006, D-015 unstarted.

## Read first
1. This file.
2. `.claude/handoff/b-021-backend-2.md` — **it is on `task/b-021-run-api`, not on `main`.**
   `git show origin/task/b-021-run-api:.claude/handoff/b-021-backend-2.md`
3. `.claude/tasks/{backend,frontend,design}.md` — current as of this commit.
4. PR #35's body (the criteria, verbatim) and its cycle-1 review comment
   `https://github.com/JulesVandenbroeck/fce-site/pull/35#issuecomment-5584607751`.

Do not load `.claude/tasks/archive/` or `backlog.md`. Same reason as always.

## In flight

| Task | Role | Branch | PR | Cycle | State | Handoff |
|---|---|---|---|---|---|---|
| B-021 | backend | `task/b-021-run-api` | #35 | 2 | **RED — `jobs.py` does not import** | `b-021-backend-2.md` (on the branch) |

Cycle 1 closed `findings=11, verdict=rework`. Cycle 2 stopped at 90% with F6 committed, F10
partial, `_retag_payload` (F2) written but unwired, and F9 half-applied — the
`_dataset_dir`/`_discover_active_samples` imports are gone while `_mc_samples()` still calls them.
F1/F7/F8/F3/F5/F4 are planned in the handoff and unwritten. **No suite or flake8 run since
`9b5527b`.** Cycle 2 is not finished; resuming it is not a third cycle.

## Git as of this commit

    main                      7cafdbc  (+ this commit)
    task/b-021-run-api        73dc1de  pushed, red
    gh pr list --state open   #35  B-021 — Job registry, POST /api/run, GET /api/run/{id}/result

Re-run both before you act. If they disagree with the table above, **git is right.**

## First moves, in order
1. **Re-dispatch B-021 cycle 2 to `backend-coder`** with the resume block (§3), pointing at
   `b-021-backend-2.md` on the branch. Its step 1 is finishing F9 so `jobs.py` imports again.
   **Give it `isolation: "worktree"`** — see "Against me" in the B-021 entry.
2. Then F-005 (Bench canvas), F-006, D-015 — still in series, still one at a time.
3. Wave 4 (B-022, SSE) consumes the `Job.events` queue this PR defines. Do not merge #35 with F1
   open: F1 is a permanent hang in exactly that contract.

## Waiting on the user
- Nothing blocking. The X4/X5 hold and the `git`-hook permission both stand as decided 2026-09-08.

## Not carried over
- Nothing dropped. B-020's F7 stays backlogged, unchanged.
- `~/fce-bookkeeping` is a `main` worktree created this session for orchestrator bookkeeping while
  a coder holds the primary checkout. Keep it or `git worktree remove` it; it holds no work.
