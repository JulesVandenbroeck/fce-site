# D-002 design anchor — cycle 1, C6 re-spec

## Where the work is
- Branch `task/d-002-tokens-work`, PR **#24**. origin head `6a874fd`.
- The branch is checked out in worktree `agent-a93cc19d487486041`, so this agent works
  **detached at 6a874fd** and publishes with `git push origin HEAD:task/d-002-tokens-work`
  (fast-forward, no force). Do not `git checkout` the branch here — it is claimed.

## Decisions
- Deliverables already on the branch and already inside scope: `tokens.css`,
  4 woff2 + 2 OFL files, and 4 new `verify.py` sections. `git diff main...HEAD --name-only`
  at 6a874fd lists nothing outside scope, so C6's diff half is already satisfied.
- Only remaining edit: narrow `check_git_diff` (verify.py:1885-1908) to exempt exactly
  `src/fce_web/static/css/tokens.css` and `src/fce_web/static/fonts/**`.
  Implementation: keep the `git diff main...HEAD -- src/ tests/ content/` invocation,
  switch `--stat` to `--name-only`, filter returned paths against an allowlist.
  Do NOT drop `src/` from the pathspec — C7 requires an out-of-scope `src/` probe to fail.

## Dead ends ruled out
- Narrowing the pathspec itself (e.g. to `src/fce_web/routes/`) — disables the guard for
  directories that do not exist yet.
- Deleting/skipping/relabelling the section — explicitly a Required finding.

## Next step
1. Narrow `check_git_diff`; flake8 clean (max-line-length 120).
2. Run all 7 criterion checks incl. C2/C5 mutation pairs and C7's four transcripts.
   `export PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright` first.
   Expect exit 1 with `board-lane-fill` the ONLY failing section (red on main by design).
3. Counts must not fall: `grep -c 'all_results.append'` >= 71, `grep -c 'results.append|line('` >= 260.
4. Commit, push, append C6 (re-spec) + C7 to PR #24 body; never rewrite C1-C5.

## Criteria still open
C6 (re-spec), C7. C1-C5 hold but must be re-run and re-pasted.
