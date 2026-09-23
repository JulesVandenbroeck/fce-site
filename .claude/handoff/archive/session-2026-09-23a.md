# Session handoff — 2026-09-23 (F-016 cycle 1 interrupted)

**Why:** 5-hour usage limit reached 87% and climbing, past §10's 75% soft stop. 0 sub-agents running
— F-016's coder had already handed itself off at its own trigger before I stopped dispatching.
**Milestone:** post-M4, the user's canvas re-architecture. D-021, F-014 and F-015 merged this session;
F-016 blocked; D-022 is the next dispatch and its ordering was corrected.

## Read first
1. This file.
2. `.claude/handoff/f-016-frontend-1.md` — the only in-flight task, and it carries a real dead end.
3. `.claude/tasks/{frontend,design}.md` — current as of this commit.

Do not load `.claude/tasks/archive/` or `backlog.md`. Same reason as always.

## The user's standing instruction
**"Continue with all tasks in series without requesting input from user."** Given 2026-09-23 and still
in force. Do not stop at checkpoints to ask; dispatch, gate, review, merge, repeat. The §7 hard stops
(3-cycle limit, a new third-party dependency, a physics or student-facing-number change) still apply.
The canvas design itself is settled — the user ruled "everything works as intended" on 2026-09-22;
that ruling is written up as `design.md` `## Decisions in force` §8-9 and is not to be re-opened.

## In flight

| Task | Role | Branch | PR | Cycle | State | Handoff |
|---|---|---|---|---|---|---|
| F-016 | frontend | `task/f-016-canvas-pan-zoom` @ `87582e8` | **none, deliberately** | 1 | C3/C6/C8 pass; C1/C2 blocked; C5 suspect; C4/C7/C9 not run | `handoff/f-016-frontend-1.md` |

**The missing PR is correct, not an omission.** The coder declined to open one for code failing its
own acceptance criteria. Do not treat that as an incomplete handoff.

## Git as of this commit

    origin/task/f-016-canvas-pan-zoom  87582e8 (pushed)
      src/fce_web/static/js/graph.js, src/fce_web/templates/shell.html, tests/e2e/test_graph.py
    gh pr list --state open   ->  (none)
    main: F-014 #61 06e4108, F-015 #62 dc2337f, D-021 #60 b3f8ef2 all merged

Re-run before you act. If it disagrees with the table above, **git is right.**

## First moves, in order

1. **Dispatch D-022 (design) — NOT F-016.** The frontend-then-design ordering was my error for this
   pair. `canvas.css`/`shell.css` are stale (last touched at D-019, before F-015's restructure) and
   still force `.canvas-svg { width: 100% }` plus a fixed `.canvas-wrap` width, so the canvas has no
   horizontal scroll range. Entry and scope are in `design.md` `## Ready`.
2. **Then resume F-016** from its handoff, using the §3 resume block. Its worktree is
   `.claude/worktrees/agent-a70512847d39d2c49`, still on the branch — **omit `isolation`**, this is a
   re-dispatch. Tell it to check `scrollWidth > clientWidth` on `#canvas-wrap` **before** touching
   `wirePan` again: if D-022 fixed the overflow, the bug is likely gone, and if it is not, that one
   measurement still splits the search space in half.
3. **Re-audit F-016's C5 once C1/C2 pass.** It currently passes and may be trivially true, because the
   drag it depends on silently no-ops. A criterion that cannot fail is §2's blind instrument.
4. **Suite floor is 726 but is NOT a stable green** — backlog N24, `test_observable_mode_is_config_not_identity`
   is flaky ~1 in 10 on `main` itself. Do not let a task "fix" it by weakening the assertion, and do
   not attribute it to a branch without reproducing it on `main`.

## Gate procedure — read §5.1, it changed this session
Run the free gate with the PR head checked out **detached in the primary checkout**, never from a
scratch worktree: `__editable__.fce_web-0.1.0.pth` pins `fce_web` to the primary checkout's `src/`,
so a worktree run serves `main`'s app while collecting the branch's tests. Confirm with
`.venv/bin/python -c "import fce_web; print(fce_web.__file__)"`. This falsified F-014's gate and cost
a round trip. Backlog **N19**. Note `.claude/` is the *branch's* copy while detached — return to
`main` before writing bookkeeping.

## Waiting on the user
- Nothing blocking. The canvas ruling is made; D-020's checkpoint is closed.
- **N15 is closed** (F-014). **N12/N14 closed** (F-015). **N13 is F-016, in flight.**

## Not carried over
- Nothing. N16-N18 closed by D-021; N19-N24 are filed in the backlog with full diagnoses.
