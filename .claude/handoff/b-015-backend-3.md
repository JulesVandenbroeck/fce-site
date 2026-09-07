# Handoff: B-015 — Bound the expression reaching analytical_loop.py:290 (cycle 3)

- **Role:** backend-coder
- **Written:** 2026-09-04, at ~90% of the 5-hour limit (orchestrator sent HANDOFF NOW)
- **Cycle:** 3
- **Continues:** nothing — first handoff on this task; this cycle got no working time

## The task as I was given it
Resolve R2 and m3 from the PR #26 review
(https://github.com/JulesVandenbroeck/fce-site/pull/26#issuecomment-5540111544), cycle 3
(the §5.7 limit — if it does not converge here, escalate to the user rather than dispatching
a fourth cycle).

**R2 (closes as C10):** `_compiled_sel_exprs_reference_sites` in
`tests/test_analytical_loop_expr_bound.py:55-72` only matches `ast.Name` / `ast.Subscript`
with a constant slice, so a reintroduced *read* via `cfg.get("compiled_sel_exprs", [])` is
invisible (reviewer's mutation 6 passes when it should fail). Must widen the checker to catch
every shape the string key can come back as — including `.get`/`.pop`/`.setdefault` calls
with a string-constant key argument — while still not false-positiving on a comment.
Check (C10): four plugin mutations via `-p`/PYTHONPATH-injected `inspect.getsource` patch,
no tracked file edited: (a) comment naming the key → PASS expected; (b)
`branch_cfg["compiled_sel_exprs"] = []`, (c) `cfg.get("compiled_sel_exprs", [])`, (d)
`cfg.pop("compiled_sel_exprs", None)` → each must FAIL naming the reference. Paste all four
runs plus the unmutated control.

**m3 (closes as C11):** C8's `-k bound` selects all 8 tests because the filename contains
"bound", not just the two cap tests. Replace with exact nodeids for the two cap tests,
`pytest "tests/test_analytical_loop_expr_bound.py::<max_expr_length_nodeid>"
"tests/test_analytical_loop_expr_bound.py::<max_ast_nodes_nodeid>" -q` → expect `2 passed`,
and put that exact command with real nodeids into the PR body's C8 entry.

### File scope
Given to me as, verbatim:
- `src/fce_web/engine/analytical_loop.py`
- `tests/test_analytical_loop_expr_bound.py`
- `tests/test_run_context.py`

Read ONLY, plus what they import:
- `src/fce_web/safe_eval.py`
- `src/fce_web/engine/path_filter.py`

Do not modify any other file.

### Do not read
- `.claude/tasks/archive/**` and `.claude/tasks/backlog.md`
- the other roles' manuals under `.claude/`
- `.claude/worktrees/**`
- `docs/design-explorations/**`

### Acceptance criteria (verbatim, new ones only — C1-C9 are in PR #26's body)
Total checks: 11.

- [ ] C10 (closes R2) — see Check/Expect above, verbatim.
- [ ] C11 (closes m3) — see Check/Expect above, verbatim.

C1–C9 all still hold per cycle-2 review (0 suggested-major); do not re-litigate them, just
keep them green.

### Verification (required before reporting done)
```
PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright .venv/bin/pytest tests/ -q && \
  .venv/bin/flake8 src/ tests/ scripts/
```
Expected: `>= 588 passed` after `git merge origin/main --no-edit` (main floor is 582, this
branch's own floor is 588 and must not fall), 0 failed, 0 errors; flake8 silent.

## State of the branch
- Branch: `task/b-015-bound-loop-expr` — **could not access it from this worktree.**
- HEAD known from git log (read-only, via `git branch -a`/`git worktree list`):
  `02a542b` — the cycle-2 commit already reviewed (R1/M1 fixed, 588 passed, 0
  suggested-major, R2 the only open item). No new commits made this cycle.
- Working tree: this worktree (`agent-a491a3be8752ce225`) was on an unrelated local
  branch `worktree-agent-a491a3be8752ce225` at `c858ce8` (= current `main`), clean,
  **untouched** — no edits were made anywhere this cycle.
- `git merge origin/main --no-edit` on the task branch: **NOT attempted** — never reached
  the branch.
- venv: **not built** this cycle.
- PR: #26, still open, unchanged since cycle-2's `02a542b`.

## Acceptance criteria — where each one stands
- [ ] C10 — not met, not started.
- [ ] C11 — not met, not started.
- [?] C1–C9 — presumed still met (cycle-2 review confirmed 588 passed, flake8 clean, exact
  scope) but **not re-verified this cycle** — no test run was executed.

## Done
- Nothing. Read `.claude/shared/CLAUDE.md`, `.claude/backend/CLAUDE.md`, and
  `superpowers:receiving-code-review` skill only. Zero file edits.

## Not done, in the order I would do it
1. From a **fresh worktree/session**, resolve the branch-access problem below first (do not
   repeat my attempts — see Dead ends).
2. `git fetch origin && git merge origin/main --no-edit` on `task/b-015-bound-loop-expr`.
3. Build venv: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`.
4. Read `tests/test_analytical_loop_expr_bound.py:1-120` (the reference-sites checker and
   the two cap tests) and `src/fce_web/engine/analytical_loop.py` around line 290 to refresh
   context — this was never re-read this cycle either.
5. TDD: widen `_compiled_sel_exprs_reference_sites` to also match `ast.Call` nodes where
   `func` is an `Attribute` named `get`/`pop`/`setdefault` and at least one arg is
   `ast.Constant` with value `"compiled_sel_exprs"` (comment-safe, since `ast` walks parsed
   syntax, not comments — this is why the substring check was replaced with an AST walk in
   cycle 2, per the review that produced `02a542b`). Write the four mutation-plugin tests
   for C10 before touching the checker; watch (b)/(c)/(d) fail-to-fail against the *old*
   narrow checker first (red), then widen it (green), confirming (a) still passes.
6. Find the two cap tests' real nodeids (`pytest tests/test_analytical_loop_expr_bound.py
   --collect-only -q`), replace C8's `-k bound` command with the explicit two-nodeid form,
   run it, confirm `2 passed`.
7. Full suite + flake8, confirm `>= 588 passed`.
8. Update PR #26 body: append C10 and C11 with Check/Expect, update total to 11, replace
   C8's Check line with the explicit-nodeid command with real nodeids substituted in.
9. Push to `task/b-015-bound-loop-expr` (same branch, no new PR).

## Dead ends — do not repeat these
- **Cannot reach the task branch from this worktree.** `git checkout
  task/b-015-bound-loop-expr` in `agent-a491a3be8752ce225` fails: "already used by worktree
  at `.claude/worktrees/agent-a69a9a8164287b840`". That other worktree is checked out on
  exactly this branch at `02a542b` (the commit I need), but the harness's sandbox refuses
  any git command that targets it (`cd` there, or `git -C <path>`) — "a worktree-isolated
  agent's git operations must target its own worktree." `git worktree remove
  .../agent-a69a9a8164287b840` (run from my own worktree, no cd/-C) also fails: it is
  **locked**, "claude agent agent-a69a9a8164287b840 (pid 51589 ...)" — i.e. another live (or
  orphaned — I could not check, `ps` on that pid was denied by the permission classifier)
  agent process holds it. I did **not** force-remove it (`-f -f`) since that risks destroying
  another session's in-flight work; this needs the orchestrator to check whether that other
  agent/worktree is genuinely still active and, if not, clean it up (or re-dispatch this task
  into a worktree that actually has the branch, or into that existing worktree directly)
  before a cycle-4/re-cycle-3 attempt can even start.
- Do not try `git worktree add` for a *new* worktree on this branch either — same
  "already used by worktree" conflict, since the branch (not just the directory) is the
  thing git refuses to have checked out twice.

## Open questions for the orchestrator
- The branch `task/b-015-bound-loop-expr` is checked out in a **different, locked**
  worktree (`agent-a69a9a8164287b840`, pid 51589) than the one I was dispatched into
  (`agent-a491a3be8752ce225`). I could not reach the branch at all this cycle. Please
  either: (a) confirm that other worktree/process is stale and clean it up, then
  re-dispatch into a worktree that has the branch; or (b) dispatch the next attempt
  directly using that existing worktree if the harness allows it; or (c) if that agent is
  genuinely still running B-015 concurrently, two agents may be racing on the same branch —
  worth checking before more work lands on it.

## Environment notes
- No venv built, no server running, no temp files created by me. This worktree
  (`agent-a491a3be8752ce225`) was left exactly as found: on `worktree-agent-a491a3be8752ce225`
  @ `c858ce8`, clean.
