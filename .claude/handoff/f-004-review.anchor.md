# F-004 review anchor (PR #32, cycle 1)
- Worktree ~/fce-gate-f004 @ 407de7a, .venv built. PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright.
- Scope from PR body: templates/, static/js/shell.js, tests/e2e/test_shell.py. gh pr diff --name-only = those 4 (index.html is inside templates/) -> scope pass so far.
- Branch is behind main (main has B-018 fixtures); diff vs main shows deletions - not a scope issue, merge-base diff is clean.
- Next: pytest tests/ -q, flake8, run 7 criteria, mutation-test test_shell.py keyboard/inline-script checks.
- Open: all C1-C7 unverified at time of writing.
