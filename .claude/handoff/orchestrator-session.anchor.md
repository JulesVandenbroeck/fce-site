# Orchestrator anchor — 2026-09-11, 75% of 5h (resets 17:00)

## In flight
- B-023 PR #43 — cycle 2 coder running in worktree agent-aeabe6cf7540d2d34 (thread env at analytical_loop.py:272; C6/C7 added, checks 7).
  Next: gate (suite ≥680 in worktree by absolute path), re-review with cycle-1 comment 5633850118 and F1-F3.
- D-017 PR #44 — reviewer running. Next: post review, merge on approve, Done line + archive.

## Merged this session
D-015 0eded93, F-010 57a42a5, F-003 1f9d344, F-009 ad36dd9.

## Decisions (user)
- rtk excludes git globally (~/.config/rtk/config.toml). settings.json manual-read denies removed.
- Wave 5 go-ahead. F-007 uses client mission-1 defaults (tests/test_api_run.py:24-38).

## Next, after the window resets
F-007 (needs B-023 + D-017 merged) → F-008 → D-016. B-024 (unit tests writing real ~/.fce) after B-023.

## Dead ends
- `cd .claude/worktrees/*` is denied — run gates with absolute paths (`$W/.venv/bin/python -m pytest $W/tests --rootdir=$W`).
- Local main diverges if bookkeeping is unpushed before `gh pr merge` — push first, then `git pull --ff-only`.
