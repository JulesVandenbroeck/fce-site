# Handoffs

Where work goes when a session runs out of context instead of where it stops.

At 90% context, any role stops mid-task, commits and pushes what it has, and writes a file
here that a cold successor can resume from. The orchestrator collects those and writes
`SESSION.md`, which the next `/orchestrate` reads first.

- `<task-id>-<role>-<cycle>.md` — one interrupted task. Written by the sub-agent, into the
  **primary checkout** (not a worktree, not a task branch — the orchestrator reads these from
  `main`). Format: `.claude/shared/context-failsafe.md` §8.4.
- `SESSION.md` — the orchestrator's index over the above, plus the first moves for the next
  session. Format and rules: `.claude/orchestrator/CLAUDE.md` §10. Deliberately under ~60
  lines; it points at state, it does not restate it.
- `archive/` — consumed handoffs. **Nothing here is ever deleted**, only moved, exactly as in
  `.claude/tasks/`.

A handoff is not a record that a task failed. It is a record that a task is resumable. The
failure mode this directory exists to prevent is the one that leaves no file at all.

Two things to know before trusting anything in here: these files were written by an agent
that was out of budget, and **git is the authority** — a handoff whose task is already merged
is stale. Reconcile first, as always.
