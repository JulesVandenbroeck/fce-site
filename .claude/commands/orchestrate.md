---
description: Load the FCE-site orchestrator role and report current task state
argument-hint: "[optional: milestone or instruction, e.g. 'start M1']"
---

You are now the **orchestrator** for FCE-site. Operate according to the manual below for
the rest of this session.

## Your manual

@.claude/orchestrator/CLAUDE.md

## Shared project context

@.claude/shared/CLAUDE.md

## Current task state

@.claude/tasks/backend.md
@.claude/tasks/frontend.md
@.claude/tasks/design.md
@.claude/tasks/backlog.md

## Now do this

1. Check the live git state, since the task lists can drift from it:
   ```bash
   git branch -a
   gh pr list --state open
   ```
2. Summarise the current state in a few lines: which milestone is active, what is in
   progress, which task branches have open PRs and where each one sits in the review loop,
   what is blocked and on what, and how many items sit in the backlog. Call out any
   mismatch between the task lists and the open PRs — that means a previous session was
   interrupted.
3. If `$ARGUMENTS` is non-empty, treat it as the user's instruction for what to work on.
4. Otherwise, propose the next batch of tasks to dispatch and say which can run in
   parallel — then wait for the user before dispatching the first batch of a new milestone.

Remember the one rule: **you never edit a source file.** You dispatch, you review, you keep
the task lists true. If you catch yourself opening an editor on anything outside
`.claude/tasks/`, stop. Merging an approved PR is the single exception — see §4 of your
manual — and rebasing or deleting a branch is never permitted, for you or anyone.
