# Anchor: B-022 review, PR #37, cycle 3
Worktree: .claude/worktrees/agent-a7c45688f7107f2cd (HEAD 26e642c). Incremental diff since 20d0e72 read.
Ran:
- full suite: 660 passed (142s). Matches the PR.
- flake8 src/ tests/ scripts/: exit 0.
- contract+events: 292 passed.
Mutations (scratchpad mutplug.py, MUT env):
- noshort: C9 test red in bounded time.
- cross (drain first job's queue): C6 test red, via join/hang assert only.
- sharedq: red on runId.
- cross_noowner: red via hang assert.
Prior findings: F2, F3, F9, F10, F6 fixed. F12 mostly fixed (_drain docstring still 15 lines).
New findings so far:
- tests:173-178 comment says runId is stamped in _make_ctx. Stale.
- _queue_owner is never pruned (1041 entries vs 500 jobs in probe).
- owner_of looks redundant: the hang assert catches crossed queues anyway. Confirming with sharedq_noowner.
Next: run sharedq_noowner, then write the review.
