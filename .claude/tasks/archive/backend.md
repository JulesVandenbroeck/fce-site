# Back end — completed task archive

Full entries for every merged back end task, moved out of `.claude/tasks/backend.md` so that
`/orchestrate` no longer loads the whole project history on every session start.
Nothing here was deleted or edited — these are the entries verbatim.

**Read this file on demand only.** When a task's history is actually in question, open
it. Never at startup.

**Some tasks appear more than once, deliberately.** A task that was written up at merge and again
at a later reconciliation has both write-ups here, and they are *not* copies — each carries
material the other does not. Checked 2026-08-22: the shorter entries hold 44-135 lines of unique
text apiece. Read the one whose heading matches the vintage you want, or read both. Nothing here
is ever deleted or edited.

---

## Done — most recent first


### B-011 — The headless driver
- **Scope:** `src/fce_web/engine/driver.py`, `src/fce_web/runs.py`, `tests/test_driver.py`
- **Branch / PR:** `task/b-011-headless-driver` — #14, merged `82ef336`
- **Result:** 2 cycles, **clean gate — 0 required, 0 suggested-major**; 4 suggested-minor
  backlogged. Suite 386 -> 401 -> **398** (see the authorised removal below).

#### What it ships
`run_analysis(config: RunConfig, ctx: RunContext, env=None) -> RunResult`, replacing the
reference's `run_engine.execute_analysis` (`run_engine.py:18`), whose only real defect was that it
returned `None` and put its answers in globals through `safe_set_state` at 21 lines. Per the user's
vendor-scope ruling the driver **stops once the histogram ROOT files are written** — the
reference's `render_plots` call at `run_engine.py:55` is not ported, and criterion 5 greps
`driver.py` for `render_plots|plotter|fitter|pyhf|matplotlib|mplhep` to keep it that way.
`RunResult` gained `cancelled` and `reason`, both defaulted so B-009's call sites were untouched.
The engine's own 0..1 is scaled through one named constant `_ENGINE_PROGRESS_SHARE = 0.9`.

**The reviewer ran it end to end against the real 91 GeV datasets on both cycles** — cold, 33.3s,
genuinely reading the ROOT files. The driver was never the problem; both cycles' findings were
about the test net around it.

#### The orchestrator caught a scope defect before dispatch, which is the cheap way
The task entry scoped B-011 to `driver.py` + `tests/test_driver.py`, but its own acceptance clause
"cancelling mid-run returns a `RunResult` marked cancelled with partial output" **could not be
satisfied inside that scope** — `RunResult` is frozen and carried only `processed_any` and
`cutflow_ready`. Scout found it; `runs.py` went into scope at dispatch. §2's question 3 paying for
itself, where B-005 cycle 1 is the precedent for what it costs when it does not.

#### The Required — third variant of one family, and the family is now named
Criterion 2's test computed `expected` **from `driver._ENGINE_PROGRESS_SHARE`**, so the assertion
self-adjusted to whatever the constant was. Setting it to `1.0` — removing the driver-owned scaling
entirely, the exact property the criterion protects — left all 15 tests green.

| | the defect | how it stayed green |
|---|---|---|
| B-009 c1 | the run never reached the code under test | only two literal endpoints recorded |
| B-011 c1 | the expectation is computed from the implementation | `expected` derived from the constant |

> **A check must not be computed from the thing it checks.** Together with B-009's lesson — ask
> whether the run a check drives even reaches the code the property is about — this is the shape to
> look for when a mutation criterion is satisfied and the property is still false.

Cycle 2 hard-coded `expected = [0.0, 0.3, 0.6, 0.9, 0.9, 1.0]`, and the reviewer re-ran the exact
mutation that had slipped through: red at `1.0`, restored green.

#### An authorised exception to the never-shrink floor — the only one so far
Three of the 15 new tests asserted against locally re-implemented copies of `run_analysis`, or a
hand-built `RunResult` that never reached `driver.py`; one was
`with pytest.raises(AssertionError): assert '<path>' in 'Run failed.'`, true by construction.
**None could fail from any change to the driver**, demonstrated per-test by the reviewer. The §5.3
floor guards properties that stop being guarded; it does not cover checks that never guarded
anything. Removal was authorised in writing, the count moved 401 -> 398 with the accounting stated
in the PR body, and the cycle-2 reviewer **independently verified the removal set by diffing test
function names between the two heads** — exactly the three, nothing else, no surviving assertion
softened. That verification is what makes the exception safe to grant again.

#### The finding that mattered most was the missing net, not a bug
`run_physics_loop` was stubbed in every test that called `run_analysis`, so
`config.to_dict()` -> `run_physics_loop(cfg, active_samples, ctx)` was never executed by the suite —
and **B-012 is built directly on that seam.** Cycle 2 added one real end-to-end test; the reviewer
then mutated `RunConfig.to_dict` to rename `detector` -> `detector_name` and confirmed **that test
is the only one in the suite that catches it.**

#### Process ruling recorded here because it changed a role manual
The cycle-1 coder mutated the tracked `driver.py` for four mutations, against
`.claude/backend/CLAUDE.md` §2, and disclosed it; the gate confirmed no residue. The tension was
real — inline seams have no symbol to rebind — so the manual's "Do" list gained the **in-memory
module copy** technique (read the source, substitute in the string, `exec` into a fresh module
object), which is how B-009's cycle-2 reviewer mutated an inline call site. "Nothing to patch" is
never a reason to edit a tracked file.

#### Carried into B-012 — read this before dispatching the parity proof
`analytical_loop.py:241` calls `get_fce_home()` **with no `env`**, so the engine's cache and output
always resolve against the real process environment even when a caller passes an isolated one,
while the driver's own `_dataset_dir` **is** env-aware. Consequence measured by the reviewer: a
cold e2e run writes a multi-hundred-MB cache into the developer's real `~/.fce`. For B-012 this is
not a tidiness issue — **the cache is content-addressed by a hash of the analysis config, so if the
reference run and ours hash alike, one can serve the other a cached result and the parity proof
becomes circular.** Subprocess isolation with an explicit `FCE_HOME` in the child environment is
what defeats this, which is why B-012's entry mandates a subprocess.


### B-009 — `RunContext`, replacing `RUN_STATE` in `analytical_loop.py`
- **Scope:** `src/fce_web/runs.py`, `src/fce_web/engine/analytical_loop.py`,
  `tests/test_run_context.py`
- **Branch / PR:** `task/b-009-run-context` — #13, merged `1689b27`
- **Result:** 2 cycles, **clean gate — 0 required, 0 suggested-major**; 3 suggested-minor
  backlogged (1 from cycle 1, 2 from cycle 2). Suite 376 -> **386**.

#### What it eliminated
The reference drove its physics loop through a single module-level `ui.state.RUN_STATE` dict
guarded by one `RLock` — one of the two named defects this project exists to fix. The coupling
surface was **27 call-site lines across five names**, enumerated by scout before dispatch:
`get_run_state` (7), `update_run_state` (17), `add_completed_node`/`add_active_node`/
`mark_nodes_completed` (1 each). The three node functions were **entirely uncounted** by the
"~24 RUN_STATE sites" figure this entry carried for weeks; they turned out cheap, because
`analytical_loop.py` is their only caller anywhere in the reference.

Also killed rather than ported: `progress_ctx`, a live mutable dict sharing two `Lock`s with the
DearPyGui render thread; and the `0.78`/`0.80` UI layout constants baked into the engine's
progress arithmetic. The engine now reports 0..1 of its own work and the driver scales it.
`run_physics_loop`'s dead `samples` and `en` parameters were removed. **The signature B-011
consumes is `run_physics_loop(cfg: dict, active_samples: List[str], ctx: RunContext) -> RunResult`.**

#### The cycle-1 Required, and it was the orchestrator's specification defect
`test_progress_values_are_bounded_monotonic_and_reach_one` **could not fail in the way criterion 4
mattered.** The run it drove had no data files, so `_TaskTracker.increment` never fired and the
recorded sequence was exactly the two literal endpoints `[0.0, 1.0]`. Monkeypatching a `0.78`
factor into the tracker changed nothing — in-range, monotonic and final-`== 1.0` all still passed.

**The defect was the dispatch's, not the coder's.** Criterion 4 named the mutation (`* 0.78` on
the progress value) but did not name the **seam**. The coder applied it at `_report_progress` —
the one place the test does observe — and it went red exactly as asked, while the property stayed
false everywhere else.

> **The generalisable lesson: a mutation criterion must name the seam, or the coder will pick the
> one seam already under observation.** This is §2's "an instrument that structurally cannot
> observe the property it certifies", in a new disguise: the instrument was fine, the *input* was
> degenerate. Ask not only "what does this print if the property is false" but "does the run this
> check drives even reach the code the property is about".

Cycle 2 named all three seams and required red at each independently. The strengthened test now
drives the real `_process_sample` through a fake `uproot` source and asserts the exact sequence
`[0.0, 1/3, 2/3, 1.0, 1.0]`. **§5.4 diagnosis: this was a CYCLE, not a re-specification** —
criterion 4 shipped with both a command and a named mutation, so neither carve-out applied.

#### The suggested-major, resolved against a recorded ruling
`analytical_loop.py` imports `fce_web.engine.cutflow_plotter`, which does not exist, and a bare
`except Exception` swallowed the `ImportError` — so `RunResult.cutflow_ready` was unconditionally
`False` with nothing saying so. The right resolution came from the **user's vendor-scope ruling**
deferring `cutflow_plotter` to M5/M6: the import is dead *by design*, so cycle 2 narrowed the
`except` to `ImportError`, logged the deferral via `ctx.on_log`, and pinned `cutflow_ready is
False` with a test distinguishing "deferred" from "failed". The reviewer independently verified
that provenance against `.claude/tasks/backend.md` rather than taking the PR body's word.

#### What the reviewer did that justified effort: high
Both cycles it built its **own** mutations rather than replaying the coder's. Cycle 1 broke
concurrency with a *shared cancellation `Event`* rather than a shared context, confirming
criterion 2 fails for a defect model the coder had not tested. Cycle 2 reproduced criterion 4's
seam (b) by mutating an inline, non-monkeypatchable call site at source level in an in-memory
module copy, and re-verified isolation against a fresh `__init__` wrapper. It also confirmed
**no test was removed** (`git diff 619dc3c..HEAD -- tests/ | grep -c '^-.*def test_'` -> `0`),
which is the §5.3 check-count floor made mechanical.

#### Orchestrator gate notes
The §5.1 free gate ran on both cycles in a detached worktree `~/fce-gate-b009`, and both times
the extra step that mattered was verifying `import fce_web.engine.analytical_loop` **resolved to
the worktree copy** — a `PYTHONPATH` shadow would otherwise have certified `main`'s code as the
branch's. Cycle 1's criterion-1 grep also carried an orchestrator defect: the pattern's `from ui`
alternative matched English prose, hitting a comment at `engine/runconfig.py:134` reading
`from ui/graph.py:1709-1719`. Anchor such patterns to import syntax — `^\s*(from|import)\s+ui\b`.


### B-003 — Playwright harness and a screenshot helper
- **Scope:** `pyproject.toml` (dev extra), `tests/e2e/__init__.py`,
  `tests/e2e/conftest.py`, `tests/e2e/test_smoke.py`, `scripts/screenshot.py`
- **Accept:** Playwright installs via pip (no npm); a fixture boots the app on an ephemeral
  port and tears it down; one e2e test asserts `/` renders with zero console errors;
  `scripts/screenshot.py <route>` writes PNGs at 1440/1024/768 and prints the paths.
  This is the tool the reviewer and design role depend on, so it must work unattended.
- **Added 2026-08-16, from the B-002 review:** the e2e smoke test must also assert **zero
  requests to non-local hosts**. The unit-level sweep in `tests/test_app.py` cannot see
  inside CSS, so `@import url(https://fonts.googleapis.com/…)` — the likeliest future §3
  breach, arriving with D-002's stylesheets — would pass it. A browser-level assertion
  catches whatever the page actually fetches, which is the guarantee shared §3 needs.
- **Depends on:** B-002 (**done**, merged `ff801fa`)
- **Branch / PR:** `task/b-003-playwright-harness` — #4
- **Status:** **done** (2 cycles) — merged as `a212e42`. Verified on `main` after merging:
  49 tests pass, `flake8 src/ tests/ scripts/` clean.
- **Review, cycle 2:** 0 required, 0 suggested-major, 2 suggested-minor → backlogged.
  The reviewer re-ran the coder's mutation check independently rather than accepting it:
  against the PR's own `_StuckFetchHandler`, an unguarded `page.goto` raises
  `playwright._impl._errors.TimeoutError` while `_goto_or_raise` raises
  `RouteNotServedError: … did not settle within 0.5s`. It then drove the whole failure path
  end to end — `main()` printed one line to stderr, returned `1`, wrote zero files, no
  traceback — which is the user-visible promise the cycle-1 finding actually asked for. It
  ran `tests/e2e` three times to check the new 500 ms-budget tests are not flaky (23 passed
  each), read the PNG IHDR chunks rather than trusting the filenames, opened `index-768.png`
  to confirm it renders the real landing page, and chased one thing nobody had raised —
  `_stuck_fetch_server` calls `shutdown()` without `server_close()` — by probing the port
  afterwards, finding it refused, and reporting it as *not* a finding.
- **Cycle 2 resolution:** suggested-major fixed, not overruled. `_goto_or_raise()` navigates
  and converts a Playwright `TimeoutError` — **specifically that, not any `PlaywrightError`**
  — into a `RouteNotServedError` naming the stuck URL; `capture()` now calls it in place of a
  bare `page.goto`. Three new tests drive a real stdlib `http.server` whose `/hang` route
  never responds, reproducing the reviewer's own repro rather than mocking it. The coder
  then mutation-tested its own fix: reverting to a bare `page.goto` made 2 of the 3 fail with
  exactly the raw `playwright._impl._errors.TimeoutError` the review reported, restored
  before committing. 49 tests pass (46 + 3), flake8 clean, three PNGs still written.
- **Review, cycle 1:** 0 required, 1 suggested-major, 3 suggested-minor.
  - *Suggested-major* — `scripts/screenshot.py:236` (`main`) catches only `ScreenshotError`,
    so any Playwright failure other than a missing browser exits with a raw traceback and no
    PNG. Reproduced by the reviewer against a page holding a long-running `fetch()` open:
    `wait_until="networkidle"` never fires and the run dies after 30 s with a bare
    `playwright._impl._errors.TimeoutError`. **The design role will hit this on the first
    "run in progress" page**, which is exactly what M3 builds. The reviewer also tested SSE
    specifically and found it fine — a page with an open `EventSource` screenshots in 1.6 s
    — so `networkidle` is not the wrong default, it is merely unguarded. Fix is inside scope.
  - *Suggested-minor* ×3 → backlogged.
  - **The review earned its findings by mutation, not by reading.** It rebuilt the exact
    threat the off-origin assertion exists to stop — a scratch `static/css/main.css`
    containing `@import url("https://fonts.googleapis.com/css2?family=Inter")`, linked from
    `base.html` — and watched `test_index_page_requests_nothing_off_origin` fail with the
    Google URL in the diff. That is the D-002 guarantee demonstrated rather than asserted.
    It also broke the console/page-error guards, pointed `PLAYWRIGHT_BROWSERS_PATH` at an
    empty directory to confirm the suite *errors* rather than silently skipping, and opened
    `index-1440.png` to check it showed the real landing page and not an error page.
- **Recovered from an interrupted dispatch.** The 2026-08-16 dispatch was cut off before
  the coder reported. Discovered by the next session reading git rather than the list: two
  commits (`8e4c039`, `1a6ff77`) were already written and pushed, adding all four in-scope
  files (662 lines, 20 tests), but no `gh pr create` ran and no report came back, so the
  review could not start. The main working directory was also left checked out on this
  branch; returned to `main`. `pyproject.toml` was correctly untouched — `playwright` was
  already in the `dev` extra from B-001, so that part of the scope was satisfied before the
  task began.
- **Second dispatch added no code.** It was told explicitly not to trust the inherited work,
  and it did not: it stood up a fresh `.venv` and installed Chromium in its worktree
  (worktrees share no untracked files with the main checkout), then ran every criterion
  rather than reading the code and agreeing with it. It found nothing to fix — no vacuous
  assertions, no missed teardown path — so it opened PR #4 on the two inherited commits
  unchanged. A no-change PR is the honest outcome here; the work had simply never been
  verified by anyone, and now it has been once, by someone other than its author.
- **Verification reported:** 46 tests pass repo-wide (20 in `tests/e2e/`), `flake8 src/
  tests/ scripts/` clean, `scripts/screenshot.py /` writes three valid PNGs at exactly
  1440×900, 1024×900, 768×900. Non-vacuity is carried by dedicated guard tests: one forces a
  real `console.error`, another makes the page actually fetch
  `https://blocked.invalid/probe.png` and asserts the checker reports exactly that URL —
  which is what makes the off-origin assertion worth anything to D-002.
- **Environment note for the reviewer and design role:** this container's default Playwright
  browser cache (`/cache`) is not writable, so `PLAYWRIGHT_BROWSERS_PATH` must be exported
  before `playwright install chromium`. `screenshot.py`'s own `CHROMIUM_MISSING_HINT`
  already documents this; no code change was needed.

### B-002 — FastAPI app factory and a served index route
- **Scope:** `src/fce_web/app.py`, `src/fce_web/routes/__init__.py`,
  `src/fce_web/routes/pages.py`, `tests/test_app.py`
- **Accept:** `create_app()` returns a FastAPI instance; `GET /` returns 200 with
  `text/html`, rendering `templates/index.html` with `title`; `StaticFiles` mounted at
  `/static` from `src/fce_web/static/` with `name="static"`, so `GET /static/js/app.js`
  returns 200; `Jinja2Templates` configured against `src/fce_web/templates/`; tested via
  `TestClient`, no live server needed
- **Depends on:** B-001 (done) and F-001 (**done**, merged `176f7d5`) — `templates/` and
  `static/` are front-end owned (shared §4) and now exist on `main`
- **Contract from F-001, not negotiable:** render `index.html` with exactly
  `{"title": <str>}` — the templates use `StrictUndefined`-clean single-variable context and
  reference static assets as the literal path `/static/js/app.js`, so the mount must be at
  `/static` from `src/fce_web/static/` or the page 404s its own script.
- **Branch / PR:** `task/b-002-app-factory` — #3
- **Status:** **done** (2 cycles) — merged as `ff801fa`. Verified on `main` after merging:
  26 tests pass, `/` → 200 HTML, `/static/js/app.js` → 200 JS, `/docs` and `/redoc` → 404.
- **Review, cycle 2:** 0 required, 0 suggested-major, 1 suggested-minor → backlogged (the
  external-host sweep does not cover static CSS; partly mitigated by the assertion added to
  B-003). The reviewer re-verified the fix against a live socket, probed the static mount
  for traversal and directory listing (all 404), mutation-tested both guards, and checked
  the cycle-1 overrule by opening `backlog.md` rather than taking it on trust — concluding
  that fixing it in scope would itself have been a `Required` scope finding.
- **Cycle 2 resolution:** required finding fixed — `docs_url=None, redoc_url=None`, which
  also removed a fourth remote-asset route the review had not spotted,
  `/docs/oauth2-redirect` (registered only when `docs_url` is set). `/openapi.json` kept
  deliberately: its body contains no absolute URL, so it breaches nothing in §3 — the
  offence was the two HTML pages that *render* the schema — and it is the machine-readable
  check that `docs/api.md` matches the routes that actually exist. Making the API surface
  non-enumerable is an API-policy call, not a §3 fix, so it was not made unilaterally →
  backlogged. Suggested-major overruled in writing → recorded in `backlog.md`.
  Suggested-minor left untouched as instructed, to keep the diff about the one required
  change.
- **Review, cycle 1:** 1 required, 1 suggested-major, 1 suggested-minor.
  - *Required* — `create_app()` left FastAPI's default `/docs` and `/redoc` enabled, and
    those pages pull Swagger UI and ReDoc from `cdn.jsdelivr.net` plus a Google-hosted font.
    That is a CDN link, a remote script and a runtime external font — three of the hard
    prohibitions in shared §3 — on an app whose whole point is to run in a classroom with no
    internet. Verified live by the reviewer, not inferred. Fix is inside scope:
    `docs_url=None, redoc_url=None`.
  - *Suggested-major* — the built wheel ships no `templates/` or `static/`, so under a
    non-editable install `create_app()` raises at the mount. Real, and already recorded in
    the backlog from the F-001 review; the fix needs `package-data`, which this task's
    `pyproject.toml` scope ("only add httpx") excludes. Expected resolution: coder overrules
    it as belonging to a follow-up packaging task.
  - *Suggested-minor* → backlogged (the module-state guard enumerates types, so it is
    allow-by-default).
- **Dependency sign-off:** `httpx` added to the `dev` extra **only**, approved by the user
  2026-08-15 (`TestClient` requires it). Test tooling; it must never become a runtime
  dependency. This is the first exercise of the new-dependency gate — record future ones
  the same way.

### B-001 — Python package skeleton, packaging, and a green test suite
- **Scope:** `pyproject.toml`, `.flake8`, `.gitignore`, `src/fce_web/__init__.py`,
  `tests/__init__.py`, `tests/test_skeleton.py`
- **Accept:** all five criteria met and independently re-verified by review
- **Depends on:** nothing
- **Branch / PR:** none — **B-001 predates the branch-per-task policy** (added
  2026-08-15, `.claude/orchestrator/CLAUDE.md` §4). Its files were written directly in the
  working tree. B-002 is the first back-end task to go through branch → PR → review →
  merge.
- **Status:** **done** (1 cycle, no rework)
- **Review:** 0 required, 0 suggested-major, 2 suggested-minor → backlogged
- **Notes:** venv at `.venv/bin/python` (Ubuntu system Python is PEP 668
  externally-managed) — later back-end tasks must use it, not `python3`. Python 3.12.3.
  `tests/` is a package, so `tests/e2e/` needs its own `__init__.py`. Reviewer
  mutation-tested all 8 tests: none are no-ops.


---



## M2 sequencing and the Done summaries, as they stood 2026-08-22

*Moved verbatim from `.claude/tasks/backend.md` when `## Done` was compacted to one line per
task. The load-bearing facts were promoted to a "Contracts in force" block in the active list;
this is the full text.*

#### M2 sequencing — RE-ORDERED 2026-08-22 on the user's ruling
```
wave 1   B-005  vendor paths + systematics      -+ parallel     DONE, merged dca1a09
         B-006  safe_eval                       -+              DONE, merged ce4dcd6
wave 2   B-007  vendor path_filter (decoupled)  -+ parallel  <- NEXT
         B-010  RunConfig + cache keys          -+
wave 3   B-009  RunContext + analytical_loop
wave 4   B-011  headless driver
wave 5   B-012  parity proof            <- M2 CHECKPOINT
wave 6   B-008  path_filter -> safe_eval        -+ after the checkpoint
         B-013  close B-006's open findings     -+
         B-014  close B-004's open findings     -+
```
**B-008 moved out of wave 3 and behind the checkpoint.** Nothing depends on B-008 — B-011 depends
on B-009 and B-010, B-009 depends on B-007 — so it was never on the critical path, and the
sequencing above had it there by habit. Running it *after* B-012 means the golden file is already
committed and becomes the regression net that proves the `safe_eval` swap changes no number a
student sees. That is what a parity proof is for, and B-008 is the one M2 task with no
verification of its own that a physics number survived.

**B-013 and B-014 deferred behind the checkpoint** for the same reason: neither blocks B-012, and
nothing on the chain touches `safe_eval.py` or `tests/test_api_contract.py`, so the open findings
cannot rot further while they wait.

Both rulings are the user's, 2026-08-22. Do not re-order back without asking.
**Every agent gets `isolation: "worktree"`, including single dispatches.** The 2026-08-18
D-004 incident was a *single* coder checking a task branch out in the main working directory,
and it put the orchestrator's own bookkeeping commits onto a task branch and into the diff the
reviewer read. Check `git symbolic-ref --short HEAD` before every bookkeeping commit.

## Done

Full entries — scope, criteria, and the cycle-by-cycle review record — are in
[`archive/backend.md`](backend.md). Read it only when a task's history is actually in
question.

- **B-011** — The headless driver — `task/b-011-headless-driver` #14, merged `82ef336`
  (2 cycles, **clean gate — 0 required, 0 suggested-major**; 4 suggested-minor backlogged).
  Ships `run_analysis(config, ctx, env=None) -> RunResult`; stops before plotting/fitting per the
  vendor-scope ruling, enforced by a grep. Suite 386 → 401 → **398**, the fall being an
  **authorised** removal of three tests the reviewer proved could not fail — the only exception to
  the §5.3 floor granted so far, and the cycle-2 reviewer verified the removal set independently.
  Cycle 1's Required was the second instance of "a check computed from the thing it checks".
  **The reviewer ran the driver end to end against the real 91 GeV data, cold, 33.3s.**
  **Read the archive entry before dispatching B-012** — the engine's `get_fce_home()` ignores a
  caller's `env`, and a shared content-addressed cache could make the parity proof circular.
- **B-009** — `RunContext`, replacing `RUN_STATE` in `analytical_loop.py` —
  `task/b-009-run-context` #13, merged `1689b27` (2 cycles, **clean gate — 0 required,
  0 suggested-major**; 3 suggested-minor backlogged). Suite 376 → **386**. Eliminated the
  27-call-site `ui.state.RUN_STATE` coupling across **five** names — the three node-highlighting
  functions were uncounted by the old "~24 sites" figure. `progress_ctx` and the `0.78`/`0.80` UI
  constants killed rather than ported. **The signature B-011 consumes:**
  `run_physics_loop(cfg: dict, active_samples: List[str], ctx: RunContext) -> RunResult`.
  Cycle 1's Required was an orchestrator specification defect — a mutation criterion that named
  the mutation but not the **seam**, so the check went red exactly as asked while the property
  stayed false elsewhere. Lesson recorded in the archive.
- **B-004** — Histogram, cutflow and fit payload contracts — `task/b-004-api-contract` #10,
  merged `d4ddec8` (**3 cycles + 2 re-specifications, §5.7 limit; 1 required + 1 suggested-major
  still open → became B-014 on the user's ruling**; 2 suggested-minor folded into B-014). Grew
  `docs/api.md` from a 71-line stub to 13 sections, and shipped `tests/test_api_contract.py` — 18
  functions / 134 cases, four parametrised families where each guard is paired 1:1 with a
  meta-test that mutates and asserts red. Suite 236 → 329. **All three specification defects were
  the orchestrator's**, same shape each time; the table is in the archive.
- **B-010** — `RunConfig` loader and the content-addressed cache keys —
  `task/b-010-runconfig` #11, merged `d017ead` (2 cycles, **clean gate — 0 required,
  0 suggested-major**; 2 suggested-minor backlogged). Ships `RunConfig` (frozen dataclasses),
  the hand-authored 13-key fixture `content/analyses/zpeak-dilepton.json`, and 25 tests.
  **The digests B-011 and B-012 consume:** `h5_sel=c9873a70ca371612fc24cf976ff7fd5c`,
  `h5=fbb913c18c34530d355fdd949974ac58` — verified independently three times (coder, reviewer,
  orchestrator) from the reference formula rather than from the loader's own code.
  **`from_dict` RAISES `RunConfigError`** on any digest mismatch, top-level or nested — B-011
  and B-012 must expect that rather than a warning.
- **B-007** — Vendor `path_filter.py` and `path_final.py`, decoupled from `ui.state` —
  `task/b-007-vendor-path-filter` #12, merged `d906b59` (2 cycles, **clean gate — 0 required,
  0 suggested-major**; 3 suggested-minor backlogged). Suite 329 → **351**. The cycle-1 review
  `diff -u`'d the vendored file against the reference and found **no numerical or control-flow
  change** in 348 diff lines; 10 of 11 ported tests byte-identical. Cancellation seam for B-009
  and B-011 is `cancel: Optional[threading.Event] = None` on `fill_histogram_from_cache` and
  `filter_raw_event_data`. **Effective cancellation granularity is one basket, not one event** —
  the vectorized fast path has no poll at all.
- **B-006** — `safe_eval.py`, the AST-whitelist expression evaluator — `task/b-006-safe-eval` #9,
  merged `ce4dcd6` (**3 cycles + 1 re-specification, §5.7 limit; 1 required + 1 suggested-major
  still open → became B-013 on the user's ruling**; 2 suggested-minor folded into B-013). The
  evaluator itself was found strong under direct attack — 26 escape payloads, no route to a class
  object, module or builtin, and no big-int bomb constructible inside the caps.
- **B-005** — Vendor `paths.py` and `engine/systematics.py` — `task/b-005-vendor-paths-systematics`
  #8, merged `dca1a09` (3 cycles, **clean gate — 0 required, 0 suggested-major**; 1 carry-forward
  to B-007, 2 suggested-minor backlogged)
- **B-003** — Playwright harness and a screenshot helper — `task/b-003-playwright-harness` #4,
  merged `a212e42` (2 cycles, clean gate)
- **B-002** — FastAPI app factory and a served index route — `task/b-002-app-factory` #3,
  merged `ff801fa` (2 cycles, clean gate)
- **B-001** — Python package skeleton, packaging, and a green test suite — no PR; predates the
  branch-per-task policy (1 cycle, no rework)


## Dossiers for deferred and blocked tasks

*Moved verbatim from `.claude/tasks/backend.md` 2026-08-22 when the active entries were compacted
to the seven-bullet form (orchestrator §6). Nothing here was edited. Each active entry links here.*


### B-014 — Close B-004's two open findings: falsify the presence/nullability halves, guard the doc columns
- **Scope:** `tests/test_api_contract.py`, `docs/api.md`
- **Accept:** (1) `test_corrupting_field_makes_schema_check_fail` gains presence and nullability
  mutations, not only type — for every path with `may_be_missing == False`, delete the first
  occurrence and require a raise **naming that path**; for every path with `may_be_null == False`,
  set it to `None` and require the same. Both are no-ops for `fit.method` (`OPTIONAL_NULLABLE`).
  (2) The `Type` and `Nullable` columns of `docs/api.md` are compared against the schema tuples by a
  parametrised row-parity test, with its own falsifiability meta-test. (3) `systUp`'s key set is
  asserted against `systSources`. (4) The two `nxt.extend(...) if ... else nxt.append(...)`
  conditional expressions become `if`/`else` statements.
- **The mutation IS the criterion, and it is the one that decides (1).** Rebind
  `_check_path_conformant` to a version that keeps the `isinstance` assert and drops both
  `assert may_be_missing` and `assert may_be_null`. Today that yields **`134 passed`**. After this
  task it must yield a large number of failures. Paste both transcripts. Monkeypatch only — no
  tracked file is edited to prove an assertion can fail.
- **Why it exists — the user's ruling 2026-08-22.** B-004 hit the §5.7 limit with these open and
  was merged rather than cycled a fourth time, on the B-006 → B-013 precedent. **The contract
  itself is correct**; what is missing is proof that two of its three enforcement halves will keep
  working.
- **The required finding, stated so it is not re-litigated.** The schema meta-test corrupts only
  the **type** (`_wrong_type_value`), so the presence and nullability halves of
  `_check_path_conformant` have no falsifiability test in the suite. The enforcement that a
  `REQUIRED` field must exist and must not be `null` can be deleted wholesale with nothing going
  red — which silently re-opens B-004's own cycle-2 Required, where a payload missing
  `cutflow.totalRaw` passed the checker. Gutting the *type* half turns 30 red and gutting the doc
  checker turns 30 red, so the pattern is already established in the file; only this sub-part is
  unguarded. All four mutations pass through the existing `_set_first_occurrence` seam.
- **The suggested-major is latent, not live.** The doc↔schema check is name-level only:
  `_documented_paths` takes the first backticked cell of each row and compares path sets, so the
  `Type` and `Nullable` columns are never checked. The reviewer verified **all 30 rows agree
  today** — `no (when the key is present)` ↔ `OPTIONAL`, `**yes**` ↔ `NULLABLE`, and the type words
  match — so nothing shipped wrong. It is a drift surface, and it is the last unguarded half of
  the thing B-004 existed to close. Give the two columns a canonical vocabulary mapped to the four
  presence states. **If you judge the canonicalisation not worth it, overrule it in writing** with
  the argument, rather than leaving it implicit.
- **Both suggested-minor, named individually per §5.6** — neither is lost:
  (a) `docs/api.md:111` documents `samples[].systUp` as "one key per source in `systSources`" and
  nothing enforces the key set; adding `systUp["totallyMadeUp"]` leaves `134 passed`. Harmless for
  the band, since `_compute_band` iterates `systSources` exactly as the reference iterates its
  fixed `SYST_SOURCES`, so a stray key is ignored rather than mis-drawn — but a producer bug of
  that shape ships undetected. One assertion in `_check_sample_array_lengths_coherent` covers it.
  (b) `tests/test_api_contract.py:207,220` use a conditional *expression* purely for side effects,
  twice. Style only; behaviour is correct.
- **Floors — a fall in any is a `Required`:** 18 test functions / **134** collected cases;
  `docs/api.md` at **13** `^##` headings; full suite at **329 passed**.
- **Depends on:** nothing — B-004 is merged. **Deferred behind B-012** (user's ruling
  2026-08-22). Can run in parallel with B-013; both touch only their
  own test file. **Not** in parallel with anything editing `docs/api.md`.
- **Branch / PR:** not yet opened


### B-013 — Close B-006's two open findings: isolate the length cap, end the docstring contradiction
- **Scope:** `src/fce_web/safe_eval.py`, `tests/test_safe_eval.py`
- **Accept:** (1) `test_expression_over_length_cap_is_rejected` fails when `MAX_EXPR_LENGTH` is
  raised — payload over the length cap but **under** `MAX_AST_NODES`, plus the isolation assertion
  the sibling node-cap test already carries at `:316`; (2) `_ValidationProof`'s docstring no longer
  says "An unforgeable token"; (3) the two bypass tests stop pinning the weakness; (4) the
  `_ASSERT_STRIPPING_ENV_VARS` note recorded so a later cleanup does not read it as dead code.
- **Every criterion is mutation-tested, and the mutation is the criterion.** Each of the four is
  "an assertion that cannot fail" — so the check is always: break the thing, show the named test
  goes red, restore, show green. Paste all four transcript pairs.
- **Why it exists — the user's ruling 2026-08-21.** B-006 hit the §5.7 limit with these open and
  was merged rather than cycled a fourth time. **The caps themselves work**; what is missing is
  proof they will keep working.
- **The required finding, stated so it is not re-litigated.**
  `test_expression_over_length_cap_is_rejected`'s payload is 2809 chars **and** 1410 AST nodes, so
  `MAX_AST_NODES` (limit 200) rejects it unaided: with `MAX_EXPR_LENGTH = 10**9` the suite still
  reports `118 passed`. The length cap guards a surface the node cap **structurally cannot**,
  because `ast.parse` runs before any node counting — the reviewer measured a 5.6 MB expression
  parsing in **1.68 s into a 2.8 M-node tree** before `_validate` is reached, once per submission
  on a shared classroom host. A single 501-digit numeric literal is over the length cap and only
  **3 nodes**; that is the payload.
- **The docstring contradiction matters to B-008 specifically.** `_ValidationProof` says "An
  unforgeable token … no way to construct a `CompiledExpr` that skipped validation"; thirty lines
  below, `CompiledExpr`'s own docstring retracts exactly that. `object.__new__` needs no sentinel
  at all, and `dataclasses.replace` forges one too — both confirmed by the reviewer, both
  producing a `CompiledExpr` that `evaluate` will run. **B-008 must not treat this type as a
  safety certificate**; see the correction in B-008's entry.
- **Depends on:** nothing — B-006 is merged. **Deferred behind B-012** (user's ruling
  2026-08-22). Can then run in parallel with B-007 and B-010.
- **Branch / PR:** not yet opened


### B-008 — Route `path_filter.py`'s expressions through `safe_eval`
- **Scope:** `src/fce_web/engine/path_filter.py`, `tests/test_path_filter_exprs.py`
- **Accept:** `grep -rnE "\beval\(|\bcompile\(" src/fce_web/engine/` returns nothing —
  that is **seven** `eval` sites plus one `compile`, not eight; the count in this entry was
  wrong until B-006 checked the reference and reported it. **Re-enumerated and CONFIRMED
  2026-08-22:** `eval` at `path_filter.py:255,296,368,426,606,615,630` (seven), `compile` at
  `:393` (one); `path_final.py` has neither. A scout summed the same enumeration to "8 eval" by
  bucketing the `compile` line wrongly — the enumeration is authoritative, its total was not.
  Do not "correct" seven to eight;
  golden value tests prove the vectorised path and the per-event fallback produce **identical
  numbers** on the same events; an `UnsafeExpression` propagates to the caller and is **not**
  swallowed by the bare `except Exception: pass` at `:262`; the escape expression fed in as a
  selection is refused before any event is read; mutation-tested
- **New ground, not a port:** the reference suite has zero tests asserting what any expression
  evaluates to, so it would pass against a broken evaluator. That gap is why criterion 2 exists.
- **RESOLVED 2026-08-21 — dropping `ast.Pow` breaks nothing, and B-006 is cleared to merge on
  a clean review.** Scout enumerated the reference:
  - The **7 genuine `**` sites** are all in *Python source* — `plotter.py:110,114` (the
    quadrature sum for the systematics band) and `path_filter.py:60,65,73,81,113` (the `_P`
    helper's `mass`, `pt`, `p`, and two `deltaR` implementations). They compile as ordinary
    Python and **never pass through `eval`**, so `safe_eval` never sees them.
  - **No saved config uses `**`.** All four (`test_systs.json`,
    `test_selection_obs_bounds.json`, `test_selection_cutflow.json`, `config/samples.json`)
    carry expression fields like `"l1.pt > 20"` and `"(l1.p4 + l2.p4).mass"`.
  - The reference's own `_SAFE_BUILTINS` (`path_filter.py:18-24`) is
    `abs, max, min, len, float, int, bool, sqrt, cos, sin, tan, pi, exp, log, True, False,
    None` — **`sqrt` and `abs` are present, `pow` is not.**
  - **Scout's own closing paragraph is wrong and I am not accepting it.** It wrote that
    blocking `**` "will break all 7 physical exponentiation sites", then said in the same
    sentence that those sites are "not in eval'd strings". The second clause is the true one
    and it refutes the first. The sites are Python source; nothing breaks.
- **What is genuinely given up, and it is small.** The reference's `eval` would have accepted
  `l1.pt**2` in a student expression, because `**` is an operator rather than a builtin. Ours
  now refuses it. Nothing in the project uses it, and `sqrt` is available, so the parity proof
  (B-012) is unaffected. Backlogged rather than blocking: if the expression language should
  offer exponentiation to students in M4, the resolution is to **bound the exponent, not to
  re-admit the operator unbounded** — that is what the DoS finding was about.
- **Superseded open question, kept for the record:** B-006 removed `ast.Pow` from the whitelist outright, so `**` is now
  rejected at compile time. That was sound for B-006, whose corpus never used `**`. But this
  task routes the reference's own seven `eval` sites through that evaluator, and **nobody has
  yet checked whether any reference expression, saved config, or default selection uses `**`.**
  If one does, B-008 breaks it and the failure is a student-visible physics change, not a
  refactor. A scout was dispatched to answer exactly this and died on the session limit before
  reporting. **Re-dispatch that scout before B-008 is specified**; if `**` is in use, the
  resolution is to bound the exponent rather than to forbid the operator, and that is a change
  to `safe_eval.py` — i.e. it goes back to B-006 while its PR is still open, which is cheap
  now and expensive after the merge.
- **CORRECTION 2026-08-21 — `CompiledExpr` is NOT a safety certificate, and this entry used to
  assume it was.** B-006's cycle-4 review confirmed that `dataclasses.replace` and
  `object.__new__` both produce a `CompiledExpr` wrapping arbitrary code, with no sentinel
  required; `safe_eval.py`'s own `CompiledExpr` docstring now documents this under "what this
  does not defend against". So **holding a `CompiledExpr` proves nothing about its contents** —
  this task must route expressions through `compile_expr` and never accept a pre-built
  `CompiledExpr` from a caller as evidence of validation. B-013 ends the contradictory
  `_ValidationProof` docstring but does **not** close the forging routes.
- **THE LINE NUMBERS THIS TASK NAVIGATES BY, authoritative as of B-007 cycle 2 (`6457e45`).**
  In **our** `src/fce_web/engine/path_filter.py` — *not* the reference's — the seven `eval`
  sites are at **335, 377, 456, 515, 718, 730, 748** and the one `compile` is at **481**.
  Enumerated by the orchestrator with an independent `ast.walk` over the file, and matching the
  coder's own re-derivation. **They will shift again** the moment B-008 edits the file, which is
  why B-007 cycle 2 added `test_docstring_eval_compile_line_numbers_match_this_file` — an `ast`
  test that re-derives them and fails if the module docstring's claim drifts. **B-008 must keep
  that test green**, and a fall in it is a Required. Do not navigate by the reference's numbers
  (255, 296, 368, 426, 606, 615, 630 / 393); the cycle-1 review caught exactly that confusion
  baked into our docstring.
- **Depends on:** ~~B-006~~ (merged `ce4dcd6`), B-007
- **Branch / PR:** not yet opened


#### What M2 does not do, recorded so it is not lost
- **Vectorising `and` / `or`.** Any expression containing `and` raises "truth value ambiguous"
  in the vectorised path, is swallowed by a bare `except`, and silently falls back to the
  per-event loop — so the most common student expression shape never hits the fast path.
  `safe_eval` could rewrite `and`/`or` to `&`/`|` for array operands: real speedup, no change
  to any number a student sees. Offered to the user 2026-08-20 and not chosen for M2 ->
  `backlog.md`.
- **`objects.py` is dead code** in the reference — nothing imports it and `path_filter.py`
  reimplements it as `_P` and friends. Shared §2's vendor table lists it as "unchanged"; that
  row should be struck rather than honoured.
- `fitter.py`, `plotter.py`, `cutflow_plotter.py`, `downloader.py`, and the import-time global
  `hdir` in all four — deferred to M5/M6 by the user's vendor-scope ruling.
- `filter_selection_cache` (`path_filter.py:222`) has no callers anywhere in the reference, and
  `analytical_loop.py:82-86` documents that it always re-reads ROOT instead. Vendor it, but
  flag it as unexercised.
- The cache key covers neither `BTAG_WP` nor the 45-column `_CACHE_KEYS` schema, so bumping
  either silently reuses stale caches — `path_filter.py:306,354` already carry back-compat
  shims for exactly that symptom.


## Post-mortems — tasks still in flight


### B-012 — The parity proof — **M2 checkpoint** (in flight)

*Moved verbatim from `.claude/tasks/backend.md` 2026-08-22 when the active entry was
compacted to the seven-bullet form (orchestrator §6). Nothing here was edited. The active
entry points at this section; the dispatched coder was given the criteria that matter as
acceptance criteria, so this is the reasoning behind them, not the task itself.*

- **Scope:** `scripts/render_reference.py`, `tests/fixtures/golden/zpeak-dilepton.json`,
  `tests/test_engine_parity.py`
- **Accept:** every bin matches within a **stated** numeric tolerance, justified rather than
  tuned; the per-source `h_{src}_up` variation histograms match too, not only the nominal;
  perturbing one bin in the golden file makes the test fail **naming that bin**
  (mutation-tested); the test skips with a named reason when either the datasets or the
  reference checkout is absent; `pytest tests/` green on this machine with both present
- **Method ruled by the user 2026-08-20: render the reference and diff.**
  `render_reference.py` drives the **reference checkout's own** `run_physics_loop` from the
  same `content/analyses/zpeak-dilepton.json` and dumps bin edges, bin contents and the
  per-source variations to JSON, which is committed as the golden file. **The point of the
  separate script is that the fix and its verification must not share a hand** — the rule
  D-003 cycle 4 was made to follow, and the technique the D-003 cycle-3 review invented.
  Rejected alternatives: reusing the unexplained `h5_*.root` files already in `~/.fce/output`
  (nobody knows which config produced which hash), and driving the real dearpygui app by hand
  (not repeatable in review).
- **Runnable here, and only here:** 1.3 GB of IDEA datasets including 91 GeV are at
  `~/.fce/datasets/`, and the reference checkout is at
  `~/Documents/Phd/teaching/fce-project/fce/`. Neither is in git and neither ever will be
  (shared §3), which is why the skip path is an acceptance criterion rather than a nicety.
- **FEASIBILITY ESTABLISHED 2026-08-22 — the reference can be driven headlessly.** This was the
  open risk on the whole milestone and it is closed. Scout built the transitive import closure of
  the reference's `engine/analytical_loop.py`: it is `ui.state`, `engine.path_filter`,
  `engine.path_final`, `engine.systematics`, `paths` — and **not one of them imports `dearpygui`**
  (`ui/state.py` imports only `queue` and `threading`; dearpygui appears only in `ui/tutorial.py`,
  `ui/components.py`, `ui/graph.py`, `fce.py`, none of which are reachable). Their third-party
  needs are `uproot`, `boost_histogram`, `numpy`, `vector`, **all four present in our venv**
  (verified 2026-08-22: uproot 5.7.5, boost_histogram 1.8.0, vector 1.8.1, numpy 2.5.2).
  `dearpygui` is absent from our venv and does not need to be. Datasets confirmed at
  `~/.fce/datasets/IDEA/91GeV/` — `X1..X6.root` and `data.root`, 4.8M–159M.
- **Two hazards that become acceptance criteria, not footnotes.**
  (1) `render_reference.py` **runs as a subprocess**, never in-process with pytest. Importing the
  reference puts `ui.state`, `engine.*` and `paths` into `sys.modules` under **bare top-level
  names**; B-006's cycle-2 review already caught exactly this leak leaving `ui.state` resolvable
  for the rest of a session, and `ui.state` is the global-state module this project exists to
  eliminate. The test asserts `"ui" not in sys.modules` after the golden file is produced.
  (2) The reference's `analytical_loop.py:17` runs `hdir = get_fce_home()` **at import time**,
  which `os.makedirs` its candidate and writes a `.write_test` probe (`paths.py:32-36`). Harmless
  here — `~/.fce` exists and is writable — but importing the reference has side effects on disk,
  so the script sets `FCE_HOME` explicitly rather than inheriting it by accident.
- **PROVEN BY EXECUTION 2026-08-22, not merely by static analysis.** The orchestrator ran, in
  the primary checkout under `./.venv/bin/python`, a script that prepends the reference checkout
  to `sys.path` and imports the reference's own entry point. Real output:
  ```
  IMPORT OK
  signature: (cfg, samples, active_samples, en)
  hdir at import time: /home/julvdnbr/.fce
  dearpygui loaded? False
  ui.state loaded? True
  ```
  So `render_reference.py` is viable exactly as B-012 specifies it. Two things that transcript
  settles: `dearpygui` is genuinely never imported, and **`ui.state` IS pulled into `sys.modules`**
  — which is the contamination hazard stated above, now observed rather than predicted. That is
  the evidence for the subprocess criterion; do not relax it.
- **The reference checkout has no venv and no installed deps** (no `.venv`, no `pyvenv.cfg`,
  `import uproot` fails under system python). So the script runs under **our** interpreter,
  `./.venv/bin/python`, with the reference checkout prepended to `sys.path`. There is no
  `conftest.py` in the reference `tests/` either — nothing there to copy.
- **Depends on:** ~~B-011~~ (merged `82ef336`) — **UNBLOCKED 2026-08-22.** Every dependency in
  M2 is now merged; this is the last task before the checkpoint.
- **THE CACHE HAZARD, promoted from a footnote to a criterion by B-011's cycle-2 review.**
  `analytical_loop.py:241` calls `get_fce_home()` **with no `env`**, so the engine's cache and
  output always resolve against the real process environment even when a caller passes an
  isolated one. The reviewer measured the consequence: a cold end-to-end run writes a
  multi-hundred-MB cache into the real `~/.fce`. **For a parity proof this is not tidiness —
  the cache is content-addressed by a hash of the analysis config, so if the reference run and
  ours hash alike, one can serve the other a cached result and the proof becomes circular:
  it would compare a number against itself and pass.** Subprocess isolation with an explicit
  `FCE_HOME` in the child environment is what defeats it. **This must be an acceptance
  criterion with its own mutation, not a note** — point both runs at the same `FCE_HOME` and
  show the proof still distinguishes them, or show it does not and fix the isolation.
- **CYCLE 1 REVIEW, 2026-08-22 — 3 required, 2 suggested-major, 4 suggested-minor.** Verbatim at
  https://github.com/JulesVandenbroeck/fce-site/pull/15#issuecomment-5381713608. The work landed
  as `199a6ac` in a session that ended before opening a PR; a resumed dispatch verified C1-C6 and
  opened #15 without needing fixes, so this is still cycle 1. The §5.1 gate passed first — 406
  passed, flake8 0, both reproduced in a detached `$HOME` worktree against the branch.
  - **R1 — the proof was one step short of circular.** `reference_render` pays a full ~80s
    reference render and then *nothing compares its output to the committed golden*. The only
    assertions on it are `returncode == 0` and the `ui`-leak check. A golden regenerated from our
    own engine would leave all 8 tests green. The reviewer confirmed externally that the fixture
    genuinely is the reference's output today (2525 values, worst |dev| 0), so the number is right
    and the instrument is broken. → **C7.**
  - **R2** — `test_skip_reason_names_a_missing_datasets_dir` asserts on the datasets branch, but
    `_skip_reason_if_unavailable` tests the reference checkout first and returns early, so on any
    machine without the reference checkout the suite goes *red* instead of skipping — the exact
    case C3 exists to cover.
  - **R3** — none of C1-C6 carried a `Check:`/`Expect:` into the PR body; the reviewer derived
    and ran all six itself. Fixed in the cycle-2 dispatch text.
  - **M1** → C8; **M2** → C9. Minors m1-m4 in `backlog.md`.
- **DIAGNOSIS (§5.4): a cycle, not a re-specification.** R2 and M1 are coder defects against
  standards held elsewhere — a test red in the normal case, and a probe writing into a fixture its
  own docstring documents as never mutated between tests. R1 is the orchestrator's failure as much
  as the coder's: C1's `Check:` was "run the parity test", which passes whether or not the fresh
  reference render is ever consulted. That is §2's *instrument that structurally cannot observe the
  property it certifies*, one level up from a missing command, and C7 is the corrected instrument.
  Under §5.4 clause 1 nothing was *dropped* from an earlier cycle, so the carve-out does not apply.
- **C4 IS ANSWERED, and the answer is the alarming one.** Pointed at a shared `FCE_HOME`, our
  engine finishes in **0.08 s** against **78.9 s** for a genuinely fresh run — it is served the
  reference's cached result. The fixtures' separate `tmp_path_factory` homes are what stands
  between this proof and a comparison of a number against itself. Do not relax them, and do not
  let a later task treat that isolation as tidiness.
- **Branch / PR:** `task/b-012-parity-proof` — PR not yet opened
- **Status:** in progress (cycle 1) — dispatched 2026-08-22, `backend-coder`, worktree,
  effort medium. **This is the M2 checkpoint task**; the orchestrator stops and reports to the
  user when it merges.
- **Floors:** full suite at **398 passed** (measured in the primary checkout at `c9eb879`);
  flake8 exits 0 across `src/ tests/ scripts/`.
- **The coder is forbidden from touching `src/fce_web/` on this task, deliberately.** A parity
  proof whose author adjusted the implementation until it matched proves nothing. If our engine
  genuinely disagrees with the reference, the coder **stops and reports** — that is a §7
  checkpoint and the most valuable output this task can produce, not a failure.
- **Criterion 4 is the one that decides whether the proof means anything**, and its answer is
  genuinely unknown to me. The coder is asked to report which of two things it found — that the
  cache cannot cross between the two runs, with evidence, or that the isolation is load-bearing
  and must fail loudly when removed. It was explicitly told I am not asking it to make the
  answer come out a particular way.
- **Tolerance discipline:** stated and justified from a physical or floating-point cause, with
  the observed worst-case deviation shown next to it, and a second mutation *just under* the
  tolerance to prove the tolerance does work rather than decorate. A tolerance widened until the
  test passed is the failure the criterion exists to prevent.

These entries were moved out of the active list to keep `/orchestrate` cheap.
The tasks are **not done**; their live status is in `.claude/tasks/backend.md`. Read
these when you are writing the next cycle's dispatch for one of them.

### B-005 — Vendor `paths.py` and `engine/systematics.py`
- **Scope:** `src/fce_web/paths.py`, `src/fce_web/engine/__init__.py`,
  `src/fce_web/engine/systematics.py`, `tests/test_paths.py`, `tests/test_systematics.py`
- **Accept:** both modules import with zero `ui.*` and zero `dearpygui`; the 23 ported
  reference tests pass (20 systematics + 3 paths); `get_fce_home` holds no module-level state
  and two calls with different `FCE_HOME` return different paths **in the same process**;
  `flake8 src/ tests/` clean
- **Two deliberate deviations from "vendor unchanged".** (1) The reference `paths.py`
  memoises into a module global `_fce_home`, which shared §6 forbids outright — and which is
  exactly why the reference's own tests have to poke `paths._fce_home = None` before each
  case. Replaced by a pure `get_fce_home(env=None)`. (2) `configure_cache_env()` is dropped:
  it is a Mesa shader-cache workaround for a desktop GL app and means nothing to a web server.
- **Why it goes first:** `systematics.py` is 48 lines with zero imports and zero global state —
  the only already-perfect module in the reference engine. It is the cheapest possible place
  to establish the vendoring pattern and the test-porting pattern.
- **Depends on:** nothing
- **Branch / PR:** `task/b-005-vendor-paths-systematics` — #8
- **Status:** cycle 2 in progress. **Review, cycle 1: 1 required, 3 suggested-major, 1
  suggested-minor** — and the required one is a criterion I wrote wrong, not a code defect.
- **Review, cycle 1 — it found a real concurrency defect that my own instructed deviation
  created.**
  - *Required* — criterion 2 ("All 23 reference tests are ported and pass") is **unsatisfiable
    given this task's other instructions**, so the reviewer correctly refused to grant it and
    escalated. Porting `test_fill_histogram_syst_keys_created` needs `path_filter.py` and
    `analytical_loop.py`, which the file scope forbids; `test_configure_cache_env_sets_writable_path`
    tests a function I instructed the coder to delete. **Waiver granted 2026-08-20: criterion
    amended to 21, both omissions justified, no code change warranted.** My error — I wrote a
    count into a criterion that my own file scope made impossible. Same shape as the `eval`
    miscount on B-006, on the same day: **counts in criteria are a liability; name the items.**
  - *Suggested-major 1 — real, and it is downstream of my deviation 1.* `paths.py:62-66`
    probes writability with a **fixed shared filename** `.write_test`, and `probe.unlink()`
    raises `FileNotFoundError` — an `OSError` — when a concurrent caller removed it first.
    That is swallowed by `except OSError: continue`, so a perfectly writable directory is
    misclassified and the resolver falls through to the next candidate. **The reviewer
    instrumented it: 523/1280 probes on a writable dir failed this way; end to end, 47% of
    concurrent calls returned the *wrong* home and 12% raised a false "No writable location
    found".** Removing the reference's memoisation turned a once-per-process probe into a
    per-call probe, which is what exposed it — so the PR body's "write-probe behaviour
    preserved exactly" is untrue at the level that matters. **Consequence: students silently
    resolve to different FCE homes and fragment the content-addressed cache that shared §2
    says must not break** — which is the exact scenario this whole project exists to support.
    **Being fixed in cycle 2, not deferred:** the fix is one line (`missing_ok=True`, or a
    unique probe name via `tempfile.mkstemp`), both verified by the reviewer at 1280/1280, it
    is inside scope, and B-007 lands the first caller.
  - *Suggested-major 2 — the manual asks for a test nobody wrote.* `.claude/backend/CLAUDE.md`
    §3.1 says in as many words: "`import fce_web.engine` must pull in **zero** UI or
    `dearpygui` dependencies. A test should assert this." The two existing guards in
    `test_skeleton.py` check declared requirements and `pyproject.toml` text — neither walks
    the import graph, neither covers `ui.*`. A grep is a one-time check that decays, and
    B-007…B-012 will copy this package's pattern. **Scope extended for cycle 2** to add it.
  - *Suggested-major 3 — accepted as a carry-forward, not a cycle-2 fix.*
    `tests/test_systematics.py:137-160` reimplements `_count_bjets` locally and five tests
    assert against that copy, so they exercise no `fce_web` production code and cannot catch
    divergence from the real thing. The reviewer says porting it was right under criterion 2,
    and I agree — **repoint it at `filter_raw_event_data` when B-007 lands that function.**
  - *Suggested-minor — folded into cycle 2, not backlogged.* `systematics.py:3-4` says
    "vendored unchanged … zero imports" while the vendored copy adds `typing`, `numpy`, a
    `Count` alias and type hints. The arithmetic genuinely is unchanged — the reviewer proved
    it over 3888 scalar combinations and 5000×3 array events with zero mismatches — so only
    the prose is false. **This is the sixth false self-describing claim on this project, and
    this module is the template every later vendoring task will read**, which is why it gets
    fixed now rather than filed.
  - **What the review verified rather than read:** a differential test against the real
    reference module (7 constants identical, 3888 scalar combinations → 0 mismatches, array
    paths bit-identical, `ValueError` message identical); an **import-graph walk** over
    `sys.modules` (167 modules, zero matching `dearpygui` or `ui.*`) rather than trusting the
    grep; a `vars()` sweep for module-level mutable state; a **mutation check** replaying the
    no-memoisation test against a memoised wrapper to prove the test has teeth; and a
    test-count audit confirming the PR body's accounting is truthful.
- **Sent back once before review, and it was not a review cycle** — no reviewer had seen it,
  so B-005's cycle count against the §5 limit is unaffected. The correction was PR-body-only;
  the branch head did not move (`28d5644`, one commit) and the code was already right.
- **Correction verified by me before dispatching the review:** the false paragraph is gone
  (`grep -c "pre-date this branch\|pre-existing"` → 0), the real transcript is in
  (**72 passed**, which reconciles exactly against the 49 I measured on `main` plus 23 new),
  and the `PLAYWRIGHT_BROWSERS_PATH` requirement is recorded in Deviations for the next
  reader. Scope still exactly the five files.
- **Scope verified by me, clean:** `git diff --name-only main...origin/task/b-005-vendor-paths-systematics`
  is exactly the five scoped files, `+361/-0`; the diff against `docs/`, `.claude/`,
  `pyproject.toml`, `content/` and `scripts/` is empty.
- **Delivered:** `get_fce_home(env=None) -> Path`, pure, same resolution order and write-probe
  behaviour; `configure_cache_env()` dropped; `systematics.py` arithmetic untouched with type
  hints added; 23 tests passing, including the one the reference cannot write — two calls in
  **one process** with different `FCE_HOME` returning different paths. Two reference tests
  dropped, both named and justified: `test_fill_histogram_syst_keys_created` needs
  `path_filter`/`analytical_loop`, which are not vendored until B-007, and
  `test_configure_cache_env_sets_writable_path` tests the function I instructed it to drop.
- **The false claim, and it is the failure class this project keeps hitting.** PR #8's
  verification paragraph says the full suite shows "4 failed, 11 errors" which "pre-date this
  branch", from "Chromium not being installed for Playwright in this environment". **I ran
  `tests/` on `main` in the primary checkout with `PLAYWRIGHT_BROWSERS_PATH` exported: 49
  passed, 0 failed, 0 errors.** There is no pre-existing failure. The coder did compare
  against a baseline honestly, but both sides of its comparison were broken the same way —
  its fresh worktree venv had no browsers path — so the comparison was valid and the
  conclusion drawn from it is not. A reviewer reading that paragraph either accepts a false
  statement about the repo or burns a cycle disproving it.
- **My error, not the coder's.** The B-003 entry below already records this environment
  requirement in writing — "this container's default Playwright browser cache (`/cache`) is
  not writable, so `PLAYWRIGHT_BROWSERS_PATH` must be exported" — and I left it out of the
  dispatch. **Every future back-end dispatch carries that line**, and every dispatch into a
  fresh worktree must say that the worktree needs its own venv and that the browser cache is
  shared at `~/.cache/ms-playwright`.


### B-006 — `safe_eval.py`, the AST-whitelist expression evaluator
- **Scope:** `src/fce_web/safe_eval.py`, `tests/test_safe_eval.py`
- **Accept:**
  1. The whitelist is enforced **at compile time**, not at eval time: names limited to the 14
     event names plus the 15 safe functions; attribute access limited to the named set;
     everything else raises `UnsafeExpression`.
  2. The escape is rejected — `l1.__class__.__init__.__globals__` and every
     underscore-prefixed attribute — as are `Subscript`, `Lambda`, comprehensions, f-strings,
     `:=` and `import`. Each rejection has its own test.
  3. A corpus fixture drawn from the reference is committed; every entry is asserted accepted
     **and** its evaluated value asserted against an independently computed number.
  4. Per-event cost within 2x of raw `eval` on a pre-compiled code object, reported as
     measured numbers from a real benchmark.
  5. Every new assertion mutation-tested against a deliberately broken whitelist, then restored.
- **Design ruled by the user 2026-08-20: AST-validate, then compile.** Walk the tree once,
  reject anything outside the whitelist, then `compile()` the validated tree and `eval` the
  code object. Rejected alternative: a pure tree-walking interpreter, 10-50x slower in a loop
  (`filter_raw_event_data`, a per-event Python loop over millions of events) that already
  dominates runtime.
- **Why this defect is not theoretical.** `_P` (`engine/path_filter.py:28`) and `_ArrayProxy`
  (`:82`) are ordinary Python objects, so
  `l1.__class__.__init__.__globals__['__import__']('os').system(...)` executes today despite
  `{"__builtins__": _SAFE_BUILTINS}`. On a shared classroom host that is remote code execution
  from a text field a student types into.
- **Depends on:** nothing — dispatched alongside B-005 because it is the highest-risk design
  in M2 and touches no vendored file.
- **Branch / PR:** `task/b-006-safe-eval` — #9
- **Status:** in review (cycle 1), dispatched 2026-08-20.
- **Sent back once before review** for the same false e2e claim as B-005, from the same
  missing env note in my dispatch. **Not a review cycle** — no reviewer had seen it, so
  B-006 stands at cycle 1 against the §5 limit. PR-body-only; branch head never moved
  (`f9433e7`, one commit). Correction verified by me: false paragraph gone, real transcript
  in at **153 passed** — which reconciles exactly against the 49 I measured on `main` plus
  the 104 new.
- **Scope verified by me, clean:** exactly the two scoped files, `+881/-0`.
- **Delivered:** `compile_expr(source) -> CompiledExpr` (validates then compiles, raises
  `UnsafeExpression`) and `evaluate(compiled, names)` (runs a pre-validated code object and
  *cannot* raise `UnsafeExpression`) — the two-stage shape that structurally prevents a bad
  expression from failing inside a hot loop. Zero third-party imports. 104 tests: 24
  escape-rejection tests, a **live demonstration of the escape firing against the real
  reference module**, a 62-entry corpus from `SEL_ALL_VARS` / `fce.py` / the three saved
  analyses each value-checked against hand-derived physics, and three mutation tests shown
  killing their target then restored byte-identically via `diff`.
- **Benchmark: at parity with raw `eval`**, four runs at 0.98x / 0.85x / 1.38x / 0.94x against
  a 2x budget. The validate-then-compile ruling is vindicated — the safety costs nothing.
- **My error #1, caught by the coder: there are seven `eval` sites, not eight.** Confirmed by
  grep: 255, 296, 368, 426, 606, 615, 630, plus one `compile()` at 393. The number came from
  `.claude/backend/CLAUDE.md` §3.2 and I repeated it into the dispatch and into B-008's entry
  below without checking. **Manual corrected 2026-08-20 to name the line numbers instead of a
  count** — a count is precisely the failure shape this project keeps shipping (D-001 ×2,
  D-003, D-004, D-008 cycle 1), and it has now bitten a *workflow* file rather than a source
  comment.
- **My error #2, also caught by the coder: the manual demanded subscripting and it was wrong.**
  §3.2 listed `Subscript` as an allowed node and `jets[0].btag` as an example expression,
  while my dispatch told the coder to reject subscripting. It flagged the tension instead of
  silently picking one, which is the right move. **Checked: the reference eval namespace is
  `l1 l2 j1 j2 ph1 ph2 met` plus five counts — there is no `jets` name at all**, so
  `jets[0].btag` raises `NameError` in the reference today. The design brief's only expression
  example (`docs/design-brief.md:181`) has no subscript either. Manual corrected; the example
  is now `j1.btag > 0.7`, which actually works.
  **The argument that settles it, and the coder found the shape of it:** the manual's own
  canonical escape, `(1).__class__.__bases__[0].__subclasses__()`, **requires a subscript** —
  so rejecting `Subscript` closes that door a second time, independently of the
  underscore-attribute rule. Narrow beats permissive when permissive buys nothing.
  **Flagged to the user as reversible** (§7 — it is a decision about the language students
  will type). If reversed, widening a whitelist is additive and nothing built here is wasted.

---

### B-005 — Vendor `paths.py` and `engine/systematics.py` — **DONE, merged `dca1a09` 2026-08-21**

Three cycles, closed on a **clean gate**: 0 required, 0 suggested-major, scope pass. The first
backend task to close clean after a review that actively tried to break it.

**The cycle-2 finding that earned the third cycle.** The reviewer replaced `get_fce_home` with a
version that had the write-probe **removed entirely** — first candidate returned unconditionally,
writable or not — and re-ran the suite: `5 passed in 0.11s`, `after run, module fn is broken?
True`. Every paths test, including the new concurrency test, passed with the module's central
contract deleted. That contract is the whole reason the file exists, and it was the most-churned
path in it (deviation 1 made the probe per-call; cycle 2 changed its mechanism again) and the
least asserted. **Cycle 3 changed no production code at all** — the implementation was already
correct; only its assertion was missing, and the coder said so rather than inventing a change.

**The concurrency defect, cycle 1 → 2.** Removing the reference's module-level memoisation turned
a once-per-process write probe into a per-call one, and under concurrency two callers raced on a
shared `.write_test` filename: the second `unlink()` raised `FileNotFoundError`, caught by the
coder's own `except OSError: continue`, which then misclassified a **writable** directory as
unwritable. Measured `errors=165/1280 wrong=444/1280`. Fixed with `tempfile.mkstemp(dir=...)`.
The coder chose it over `unlink(missing_ok=True)` on an argument worth preserving: the latter
patches the one interleaving the reviewer instrumented and asserts "a missing probe file is
always fine", which is only true if you have reasoned through every interleaving; `mkstemp`
removes the shared name so there is nothing left to reason about. The reviewer reproduced the
race independently (`146/1280`, `431/1280`) and confirmed the fix is safe **by mechanism**
(`O_CREAT|O_EXCL`, no shared name), not by luck.

**The coder corrected its own false claim without being asked.** Cycle 1's PR said "write-probe
behaviour is preserved exactly". Cycle 2 retracted it: the observable contract was preserved, the
*mechanism* was not. The reviewer called the retraction accurate. Given this project has shipped
four false absolutes in self-describing comments, an unprompted retraction is the behaviour to
copy.

**The overrule that held.** Cycle 1's suggested-major 3 — `tests/test_systematics.py`'s
`_count_bjets` reimplements b-tag counting locally and so exercises no production code — was
overruled in writing on the grounds that `filter_raw_event_data` lives in `path_filter.py`, which
this file scope forbade creating. Both the cycle-2 and cycle-3 reviewers accepted it and neither
re-raised it. **Carried forward to B-007.**

**My defects, both of them.**
1. *Cycle 1's `Required` was my criterion, not the code.* I demanded 23 ported reference tests
   when my own file scope made two of them impossible. The reviewer refused to grant it and
   escalated rather than inventing a resolution — the right call, and the origin of §2's third
   pre-dispatch question.
2. *No criterion carried a command.* Both the cycle-2 and cycle-1 reviewers filed a `Required`
   against the **dispatch**: five criteria written as prose, so the reviewer had to invent the
   checks. §2's criterion contract already existed and I had not applied it to a backend task.
   Fixed in the cycle-3 dispatch — every criterion got a `Check:` and an `Expect:`, and the
   reviewer confirmed each one runs as written.

**The §5.1 gate paid twice.** Cycle 1's PR body reported "4 failed, 11 errors" that "pre-date this
branch"; `main` with `PLAYWRIGHT_BROWSERS_PATH` exported was 49 passed, 0 failed. The coder's
comparison was honest and both sides of it were broken the same way — a fresh worktree venv with
no browsers path — so the comparison was valid and the conclusion drawn from it was not. Cycles 2
and 3 both cleared the gate on the first attempt, exactly. **Cycle 3's gate caught the thing that
mattered:** both new probe tests PASSED rather than SKIPPED. They guard on root, where
`chmod 0o500` does not remove write access, so in the wrong environment they would have certified
nothing while reporting green.

**Lost to a crash, twice.** Cycle 2 landed fully committed and pushed while the task list still
said "in progress"; found by reading git on 2026-08-21, not by reading the list. Cycle 3's first
reviewer died on a session limit having produced nothing. Neither cost work.

**Original active entry, verbatim:**

### B-005 — Vendor `paths.py` and `engine/systematics.py`
- **Scope:** `src/fce_web/paths.py`, `src/fce_web/engine/__init__.py`,
  `src/fce_web/engine/systematics.py`, `tests/test_paths.py`, `tests/test_systematics.py`
  — extended for cycle 2 to add the import-graph test.
- **Accept:** both modules import with zero `ui.*` and zero `dearpygui`; the **21** ported
  reference tests pass (criterion amended from 23 by waiver 2026-08-20 — two were outside
  this file scope); `get_fce_home` holds no module-level state and two calls with different
  `FCE_HOME` return different paths in the same process; `flake8 src/ tests/` clean.
- **Depends on:** nothing
- **Branch / PR:** `task/b-005-vendor-paths-systematics` — #8
- **Status:** **cycle 2 delivered, unreported — reconciled from git 2026-08-21.** The list
  said "in progress"; `origin/task/b-005-vendor-paths-systematics` and PR #8 both carry
  `ae1cc36` "backend: fix write-probe race, add import-graph guard (B-005 cycle 2)", pushed
  2026-08-20 21:36 UTC, with a full `## Cycle 2` section in the PR body. The coder's session
  ended before it reported back. **Fourth time on this project that the disk was right and the
  list was wrong** (B-003, D-008 ×3 — now B-005).
  **Cycle 2 reviewed 2026-08-21 — 1 required, 1 suggested-major, 2 suggested-minor; cycle 3
  dispatched.** The required is *against my dispatch*: none of my five criteria carried a
  `Check:`/`Expect:`, so the reviewer had to invent the checks. All five criteria were **met**.
  The suggested-major is the real one and it is well-earned: the reviewer deleted the
  write-probe from `get_fce_home` entirely — first candidate returned unconditionally — and all
  five paths tests still passed (`5 passed in 0.11s`, `after run, module fn is broken? True`).
  The module's central contract is unasserted, on the most-churned path in the file. Cycle 3
  adds the two probe tests and the `uicontrols` name that makes the import guard's separator
  rule actually assertable. Review posted to PR #8.
  **Cycle 3 delivered `f33c667`, §5.1 gate PASSED 2026-08-21, review dispatched.** Re-ran the
  claims in a clean detached worktree with its own venv: full suite **77 passed** (up from 75),
  targeted **28 passed** (up from 26), flake8 exit 0, grep exit 1 — all exact. **And the check
  that mattered: both new probe tests PASSED rather than SKIPPED.** They carry a
  `pytest.skip` guard for the root case, where `chmod 0o500` does not remove write access, so
  in the wrong environment they would have been vacuous. This container runs as uid 1002, so
  they genuinely run. `src/fce_web/paths.py` was not touched — the implementation was already
  correct; only its assertion was missing.
  **Cycle-3 review dispatched and lost to the session limit 2026-08-21** — the reviewer died
  on its first turn, having produced nothing. No state lost beyond the dispatch; branch head
  unmoved at `f33c667`, coder worktree clean. Re-dispatch needed.
  **§5.1 gate: PASSED, 2026-08-21.** Re-ran all four of the PR body's verification claims in a
  clean detached worktree at `ae1cc36` with its own venv (`~/gate-b005`, since removed —
  detached, so no branch touched) and `PLAYWRIGHT_BROWSERS_PATH` exported. All four reproduce
  exactly: targeted suite **26 passed**, full suite **75 passed**, `flake8 src/ tests/` exit 0,
  `grep -rn "ui\.\|dearpygui" src/fce_web/` exit 1 (no match). First PR to clear this gate on
  the first attempt — #8 cycle 1 and #9 both failed it. Cycle-2 review dispatched 2026-08-21,
  reviewer told to reproduce the race itself rather than accept the PR's account of it.
- **Review:** cycle 1 — 1 required (my bad criterion, waived), 3 suggested-major, 1
  suggested-minor. Cycle 2 fixes the concurrent write-probe defect, adds the import-graph
  test, and corrects the `systematics.py` header prose; suggested-major 3 overruled in writing
  by the coder and carried forward to B-007.
- **History:** [`archive/backend.md` § Post-mortems](backend.md) — the 47%-wrong-home
  concurrency defect, and the false-green PR body that produced the §5.1 pre-review gate.


---

## B-006 — full entry, moved from the active list 2026-08-21 on merge

### B-006 — `safe_eval.py`, the AST-whitelist expression evaluator
- **Scope:** `src/fce_web/safe_eval.py`, `tests/test_safe_eval.py`
- **Accept:** whitelist enforced at **compile** time, not eval time; the
  `__class__.__init__.__globals__` escape and every underscore attribute rejected, plus
  `Subscript`, `Lambda`, comprehensions, f-strings, `:=`, `import`, each with its own test;
  a committed reference corpus with every value asserted against an independently computed
  number; per-event cost within 2× of raw `eval`, reported as measured numbers; every new
  assertion mutation-tested against a broken whitelist, then restored.
- **Depends on:** nothing — dispatched alongside B-005.
- **Branch / PR:** `task/b-006-safe-eval` — #9
- **Status:** **cycle 2 delivered `ab5535a`, §5.1 gate PASSED 2026-08-21; review dispatched
  and lost to the session limit, re-dispatch needed.** Gate re-ran the claims in a clean
  detached worktree: `test_safe_eval.py` **110 passed** (up from 104), full suite **159
  passed** (up from 153), flake8 exit 0, `SAFE_BUILTINS['x']=1` → `TypeError: 'mappingproxy'
  object does not support item assignment`, and **all three DoS payloads now exit 1 inside
  `timeout 15`** — `9**9**9`, `2**64**8`, `2**10000000`. Cycle 1's finding was exit **124**
  (never returned); the class is closed at compile time. The coder dropped `ast.Pow` entirely
  rather than bounding the exponent, on the grounds that no corpus expression uses `**`.
  **The open question that ruling raises is B-008's, not B-006's** — see the B-008 entry.
  **Cycle 2 reviewed 2026-08-21 — 0 required, 1 suggested-major, 3 suggested-minor. NOT
  approved; cycle 3 dispatched, and cycle 3 is the §5.7 limit.**
  - *The suggested-major is a fix-induced regression — cycle 2's own fix created it* (§5.5, and
    the third time on this project that a later cycle caught what a previous fix introduced).
    `monkeypatch.syspath_prepend` undoes the path at teardown but **not the modules it
    enabled**: `engine`, `ui`, `ui.state`, `engine.systematics`, `engine.path_filter` all stay
    in `sys.modules` bound to the reference checkout. `ui.state` is the module holding the
    global `RUN_STATE` this project exists to eliminate, and B-007 lands `path_filter.py` under
    a colliding name.
  - **The criterion was mine and the defect in it is worth naming.** I wrote *"the test suite
    does not mutate `sys.path` process-wide"* — a **mechanism**, not the property. The coder met
    it exactly and the leak simply moved to the vector nothing was checking. §2 now carries the
    rule: state the property in the sentence, the method in the `Check:`.
  - **§5.4 says this is a cycle, not a re-specification**, and I am applying my own test rather
    than the flattering reading: nothing was *dropped* (clause 1 no), criterion 8 shipped with a
    command and that command still passes (clause 2 no), so it falls to clause 3 — a property no
    criterion gated. My criterion set was incomplete, not unenforceable.
  - *Suggested-minor:* (1) the PR body pasted a criterion-1 transcript the command **cannot
    print** — `ast.walk` reaches `Call` first, so the real message is `Cannot call '.system'.`
    That is the D-004 "25 sections / listed 26" defect and it is folded in; (2) the `Pow`
    rejection message tells a student to use "arithmetic", which is what they thought `**` was —
    folded in; (3) `CompiledExpr`'s docstring claims existence proves `compile_expr` accepted it,
    but its constructor is public and the reviewer built one around raw `compile()` in seconds —
    folded in, because **B-008 is told to treat that type as a safety certificate.**
  - *What held, and the review was the hardest this project has run:* the unbounded-cost
    **class** attacked with 14 constructed payloads and found closed, not just the three named
    ones; a 40-payload escape corpus with 39 rejected at compile time and the one acceptance
    (`abs.mass.mass`) reaching nothing; `MappingProxyType` confirmed to restrict at **eval**
    time via a hand-built `CompiledExpr` around raw `compile("__import__")` → `NameError`; all
    five new assertions mutation-tested and each failing as claimed; check count 45 → 51 test
    functions with `comm -23` proving none removed. Benchmark 0.94×.
  **Cycle 3 delivered `7e45f7c`, gate PASSED, reviewed: 1 required, 3 suggested-major, 1
  suggested-minor. RE-SPECIFICATION dispatched (§5.4 clause 2) — B-006 stays at 3 cycles.**
  **The required finding is my check command, and I have direct evidence.** Criterion 10 gave
  `CompiledExpr(compile('1+1','<s>','eval'))` with "adapt to the real signature" — a call with
  the **wrong arity**, which raises `TypeError: missing required positional arguments` whether
  or not any guard exists. The coder adapted it faithfully into a test asserting exactly that
  `TypeError`, so the only test of the new security guard **cannot fail**: the reviewer set
  `__post_init__` to a no-op and got `113 passed`. I hit the same wall running my own §5.1
  probe, corrected it to pass a forged proof, and **never went back to fix the dispatch.**
  Suggested-majors: an assertion made vacuous by the line beneath it; the unforgeability
  docstring falsified by `dataclasses.replace` and `object.__new__` without touching `_PROOF`;
  and the subprocess proof passing under `PYTHONOPTIMIZE=1`, which strips its only `assert`.
  *What held:* a **47-payload** escape corpus with **zero accepted**, `LEAKED MODULES: {}` and
  `LEAKED PATH: []` — cycle 2's leak genuinely closed — the subprocess proof running rather
  than skipping, check count 110 → 113 with nothing retired, and the rewritten reference test
  judged **stricter** than cycle 2's.
  **RE-SPECIFICATION DELIVERED `b058166` — reconciled from git 2026-08-21, the list was
  wrong and the disk was right (§6).** The re-spec agent died on the session limit, but it died
  *after* committing and pushing: "forge the CompiledExpr proof, narrow the docstring, harden the
  subprocess ...". PR #9 head is `b058166`. I gated it in a clean detached worktree at that exact
  commit: **167 passed** (body claims 162), **118 `test_safe_eval.py`** (body claims 113),
  flake8 exit 0, only the two in-scope files touched. So the code work is real and substantial.
  **§5.1 gate FAILED on the body, not the code, and that is not a cycle.** PR #9's body still ends
  at `## Cycle 3` with no re-specification section at all, and its criterion-10 transcript is still
  the wrong-arity `TypeError` the review filed `Required` against. Sent back to the same
  backend-coder to verify at head and append the section with verbatim transcripts — including the
  forgery test that *can* fail, which is the whole point of the required finding.
  **Body corrected 2026-08-21, no code change needed; §5.1 gate PASSED at unchanged head
  `b058166`; review dispatched (cycle 4 of the coder's work, but B-006 stays at 3 cycles —
  §5.4 clause 2, the required finding was my broken check command).** Every number in the new
  `## Re-specification` section reproduces exactly what I measured independently at that commit:
  167 / 118 / flake8 0, `comm -23` empty so no cycle-3 test was retired, diff stat identical,
  scope respected. The coder verified the crashed agent's code against the review line by line
  and found it already closed every finding.
  - **One resolution the reviewer must weigh, and I am not pre-judging it.** The forgery guard
    catches a hand-built `_ValidationProof`, but **`dataclasses.replace` and `object.__new__`
    still forge a `CompiledExpr`.** The coder chose to *narrow the docstring* — adding an explicit
    "what this does not defend against" section — rather than close those two routes. That is the
    honest option and it is the one this task keeps asking for. But **B-008 is told to treat this
    type as a safety certificate**, so if the reviewer judges the residue unacceptable, the fix is
    cheap now and expensive after the merge. Whichever way it lands, B-008's entry must be
    corrected to match what the certificate actually guarantees.
  **REVIEWED 2026-08-21 — 1 required, 2 suggested-major, 2 suggested-minor. NOT approved, and
  this is the §5.7 LIMIT: 3 cycles are spent and I am not dispatching a fourth. ESCALATED TO
  THE USER.** Review posted to PR #9. Cycle ledger: c1 (`f9433e7`), c2 (`ab5535a`), c3
  (`7e45f7c`), then the re-specification (`b058166`) which §5.4 clause 2 correctly excluded.
  Four coder passes, three cycles.
  - **§5.4 diagnosis, applying the strict test rather than the flattering one — this is a
    CYCLE, clause 3.** Clause 1: nothing was dropped; criterion 6 ("no accepted expression can
    run unbounded") was restated in every dispatch from cycle 2 on. Clause 2: my re-spec
    criterion 6 *did* ship with a command. So it falls to clause 3 — my criterion set was
    incomplete, not unenforceable. Had clause 2 applied this would have been free, and the
    temptation to read it that way is exactly what §5.4's carve-out warns about.
  - *Required — the one cap with a real DoS job is the one cap with no test that can fail.*
    `test_expression_over_length_cap_is_rejected`'s payload is 2809 chars **and** 1410 AST
    nodes, so `MAX_AST_NODES` (limit 200) rejects it unaided: with `MAX_EXPR_LENGTH` set to
    `10**9` the suite still reports `118 passed`. And the length cap guards a surface the node
    cap **structurally cannot**, because `ast.parse` runs before any node counting — the
    reviewer measured a 5.6 MB expression parsing in **1.68 s into a 2.8 M-node tree** before
    `_validate` is reached, once per submission on a shared classroom host. The fix is small
    and the reviewer specified it: a payload over the length cap but under the node cap (a
    single 501-digit literal is 3 nodes), plus the isolation assertion the sibling node-cap
    test already carries at `:316`.
  - *Suggested-major 1:* `_ValidationProof`'s docstring still says "An unforgeable token" —
    the exact overclaim `CompiledExpr`'s docstring 30 lines below now retracts. Two docstrings
    contradict each other about the same security property, and the reader hits the wrong one
    first because it is the class named "proof".
  - *Suggested-major 2 — mine, and it is the fifth instrument failure on this project.* My
    criterion-2 command `comm -23 <(grep -o '^def test_...')` sees only the **10 module-level**
    tests and is blind to the **49 class-scoped** ones — which is every escape assertion in the
    PR. The reviewer re-ran it against a HEAD with all class-scoped tests stripped: still
    empty. Nothing was actually lost (one documented rename), but the instrument certifying
    "nothing stopped being checked" cannot detect what it exists to detect. **Replace it
    everywhere with `pytest --collect-only -q`.**
  - *Suggested-minor:* (1) the two bypass tests assert the bypass *succeeds*, so closing the
    gap later turns a security improvement into a red suite — `xfail(strict=False)` instead;
    (2) `_ASSERT_STRIPPING_ENV_VARS` has no assertion of its own, the sentinel carries the
    property. Both to `backlog.md` unless the user authorises another cycle.
  - *What held, and it is most of the task.* The reviewer attacked the evaluator directly with
    **26 escape payloads** and found no route to a class object, a module or a builtin; could
    not build a big-int bomb inside the caps; and faithfully mutated the two hardest cycle-3
    fixes — neutering `CompiledExpr.__post_init__` gave `1 failed, 117 passed` naming the
    forgery test, and reverting the subprocess proof gave `2 failed`. Both are genuinely
    closed. Scope pass. All body numbers reproduced.
  Previously: cycle-1 review dispatched, result lost — reconciled from git 2026-08-21. `main`
  carries `4f78550` "B-006 PR body corrected, dispatched to review (cycle 1)", so the reviewer
  ran, but the session ended before it reported and a sub-agent's context does not survive.
  PR #9 carries **zero comments**, so nothing was captured there either — which is precisely
  the loss §6's *post the review to the PR* rule exists to prevent, and it has now cost a
  whole review. Branch head unmoved at `f9433e7`. **Cycle 1 is being re-dispatched**, and that
  re-dispatch is not a second cycle: no coder work happened between the two.
- **Review:** cycle 1 re-dispatched and returned 2026-08-21 — **2 required, 2
  suggested-major, 3 suggested-minor**; cycle 2 dispatched. Review posted to PR #9.
  - *Required 1 — a live denial of service, and the best finding of the session.* `ast.Pow`
    is whitelisted with no bound on the exponent, so the 500-char / 200-node size caps do not
    bound **cost**. `9**9**9` is 7 characters and 8 AST nodes, is **accepted**, and then never
    returns — reviewer measured `exit=124` after 15s. `evaluate` runs once per event over
    millions of events, on a teacher's laptop with thirty students connected. This is exactly
    the billion-laughs case `.claude/backend/CLAUDE.md` §3.2 asks to be bounded; the coder
    implemented size caps and stopped one step short of cost caps.
  - *Required 2 — against my dispatch*, same as B-005: no criterion carried a command.
  - *Suggested-major:* `tests/test_safe_eval.py:325` mutates `sys.path` process-wide with a
    hard-coded home directory that shadows `engine/`, `objects.py` and `paths.py` — **latent
    until B-007 lands those exact names**; and `SAFE_BUILTINS` is module-level mutable state
    handed to `eval` as `__builtins__`, which shared §6 forbids unqualified.
  - *Suggested-minor:* (a) docstring still says "eight `eval()` call sites" — folded in;
    (b) `import re` inside `preprocess_hep_expr` — folded in; (c) `ast.walk` reaching `Call`
    before `Attribute` so the canonical escape gets the least legible of three correct
    messages — **backlogged**, not for this cycle.
  - *What held:* 22 hand-written escape payloads all rejected; a 0.1% perturbation of
    `evaluate()` fails 50 of 104 tests, so the corpus assertions are load-bearing; the two
    locks are independent as claimed. Parity with raw `eval` (0.85–1.38×) reproduced.
- **History:** [`archive/backend.md` § Post-mortems](backend.md) — the coder caught
  two errors in my dispatch (seven `eval` sites, not eight; `Subscript` contradiction), both
  since corrected in `.claude/backend/CLAUDE.md` §3.2.


---

## B-004 — Histogram, cutflow and fit payload contracts

- **Branch / PR:** `task/b-004-api-contract` — #10, merged `d4ddec8` on 2026-08-22
- **Cycles:** 3 coder→reviewer cycles, plus 2 re-specifications and 1 pre-review send-back, none of
  which counted. Closed at the §5.7 limit on the user's ruling, with 1 required and 1
  suggested-major open → **B-014**.
- **Final scope:** `docs/api.md`, `tests/test_api_contract.py`. Nothing else, on any cycle.

### What shipped

`docs/api.md` went from a 71-line stub documenting three fields — `edges`,
`samples[{name, counts, weightsSquared}]`, `data` — to 13 sections covering all 30 schema paths
with type, nullability and meaning, plus eight documented semantics of the reference engine that
existed nowhere in writing before. `tests/test_api_contract.py` is new: 18 test functions / 134
collected cases. Full suite 236 → 329.

The architecture that emerged is worth reusing: **four parametrised families, each paired 1:1 with
a meta-test that mutates and asserts red.**

| Guard | Meta-test | Cases |
|---|---|---|
| `test_payload_conforms_to_schema_field` | `test_corrupting_field_makes_schema_check_fail` | 30 |
| `test_documented_schema_field_appears_in_api_md` | `test_removing_field_row_makes_documented_check_fail` | 30 |
| `test_no_orphan_schema_table_rows` | `test_appending_orphan_row_makes_no_orphan_check_fail` | 1 |

Falsifiability stopped being a transcript somebody pasted once and became a property of the suite.
That is the transferable result.

### The scope correction, before any code was written

The entry said "`docs/api.md`, plus the run-pipeline plumbing that has to persist the per-source
variation histograms". There was no run pipeline — `path_filter.py`, `path_final.py`,
`analytical_loop.py`, `runs.py`, `driver.py` all absent — and the files that would persist
`h_{src}_up` were already inside **B-007's** scope. Ruled contract-only; three criteria moved to
B-007. Two further user rulings: `weightsSquared` and `fit.muErr` are nullable with no producer
(the reference uses default `Double()` storage and `run_fit` returns a bare tuple), and cutflow
efficiency is MC-only, a deliberate divergence from `cutflow_plotter.py:70-83`.

### The three specification defects, all mine, all one shape

| Cycle | Criterion | Its `Check:` | Why it could not see the defect |
|---|---|---|---|
| 1 | c1 — "deleting any field name makes it fail" | `pytest -k documented` | runs the *unmutated* doc; prints `28 passed` either way |
| 1 | c5 — "one pair per assertion" | prose, no command | denominator ambiguous between 14 functions and 41 cases; **I resolved it in the coder's favour at the gate** |
| 2 | c2 — presence/type/nullability | *I deleted the clause on re-dispatch* | §5.3 substitution, my act, while writing "cumulative" above it |
| 3 | c6 — "falsifiability proven by a test in the suite" | `--collect-only` counts | counts cases; cannot see a family mutating one of three halves |

Each names a real property and pairs it with a command that runs against known-good inputs. **The
rule this earns: when a criterion says "X is checked", the `Check:` must be a mutation that makes
the check fail — not a run of the check.** Ask what the command prints when the property is false.
If the answer is "the same thing", it is not a criterion.

### What each cycle found

- **Send-back (§5.1, not a cycle).** All six numbers reproduced, but the 14 mutation entries were
  prose with no pytest output anywhere, and the body admitted the mutations called `_check_*`
  helpers directly rather than running the tests. A helper raising was shown; the named test going
  red was not. Branch head never moved.
- **Cycle 1 — required.** `_check_field_documented` grepped `\b<leaf name>\b` across the whole
  document, so five parametrised cases could not detect the field disappearing: `data` survives in
  "pseudo-data", `samples` in "over MC samples first", `edges` in "41 edges / 40 bins", plus `name`
  and `stages`. The reviewer built a **negative control** — deleted every documenting line for
  `data` and showed `…[data]` still passing. Also: a fabricated `static/js/chart.js` citation.
- **Cycle 2 — required.** The 30 `(type, nullable)` tuples were **never read**; the dicts were
  consumed only as `set(...)` of keys. Deleting `cutflow.totalRaw` and setting `samples[0].name` to
  `42`, both declared non-nullable, gave `76 passed`. The paired suggested-major was a landmine the
  cycle-1 fix had laid: `systUp.*` declared `(list, False)` contradicted the partial-presence rule
  added the same cycle, so wiring the tuples up naively would have re-broken it. The coder fixed
  the declaration first.
- **Cycle 3 — required.** The schema meta-test corrupts only the **type**, leaving the presence and
  nullability halves unfalsified: gut both asserts and the suite still reports `134 passed`. Same
  shape, one level deeper. → B-014.

Every cycle's Required was found in the *previous* cycle's fix. §5.5's "later cycles are where
fix-induced regressions live" held three times out of three.

### What the reviewer did that is worth copying

- Built **negative controls**, not just positive ones — the `data` case is the whole cycle-1
  finding, and "delete `systUp.jec` → `134 passed`, correct by design" is how you show a check is
  calibrated rather than merely loud.
- Diffed every *retained* checker for softening across revisions, confirming `>=` logic unchanged
  and all 28 old leaf cases still covered inside the new 30 — the §5.3 regression check, actually
  performed.
- Re-verified every physics citation at the reference source rather than reading the prose,
  including catching `plotter.py:52-64` as really `58-67`, where `52-57` is the `uproot.open` guard
  and `65-67` is the cross-sample accumulation the rule is about.
- Mutated only by monkeypatch, via pytest plugins on `PYTHONPATH` outside the repo. Tree clean
  every cycle.

### Coder behaviour worth noting

Independently re-verified every finding at the reference before implementing, on all three cycles,
and reported none technically wrong — `receiving-code-review` as intended rather than capitulation.
Disclosed unprompted that two assertions could not be falsified by payload-only mutation. Fixed the
suggested-major *before* the Required when told the order mattered. Scope was clean on every cycle;
`src/` was never touched.

### Left open, deliberately

The run-request contract (`nodes[] + edges[]` with coordinates in a separate `ui` object) is
`POST /api/run`, not the histogram response, and is **blocked on the user's D-007 choice** —
Beamline, Bench and Board persist structurally different things. Backlogged: a producer for
`fit.method`; producers for `weightsSquared` and `fit.muErr`.

---

## B-007 — Vendor `path_filter.py` and `path_final.py` (merged `d906b59`, 2 cycles)

### B-007 — Vendor `path_filter.py` and `path_final.py`, decoupled from `ui.state`
- **Scope:** `src/fce_web/engine/path_filter.py`, `src/fce_web/engine/path_final.py`,
  `tests/test_path_filter.py`
- **Accept:** the decoupling is proven by BOTH checks in the correction below (not by the old
  `ui\.` grep); the 11 ported reference tests pass; a new test drives a real cancellation
  mid-loop and asserts the loop stops — the reference has no such test; `flake8` clean
- **CORRECTION 2026-08-22 — the old criterion could not see the property it certified.** It was
  `grep -rn "ui\." src/fce_web/engine/path_filter.py` returns empty. Scout enumerated the
  reference: `path_filter.py` contains **exactly one** literal `ui.` occurrence, the import at
  `:5` (`from ui.state import get_run_state`). Every real coupling is a **bare**
  `get_run_state(...)` call the grep is structurally blind to, so deleting one import line
  satisfies it. This is orchestrator §2's "instrument that structurally cannot observe the
  property it certifies". Replaced by two checks, both required:
  (a) `grep -rnE "\bui\.|get_run_state|update_run_state|RUN_STATE" src/fce_web/engine/` → empty;
  (b) a **subprocess** import test that sets `sys.modules["ui"] = None` before importing
  `fce_web.engine.path_filter`, and requires the import and a real filter call to still succeed.
  (b) is the one that goes red when the property is false; (a) alone does not.
- **The whole coupling is two lines — line numbers VERIFIED 2026-08-22, but the description of
  them was wrong.** `get_run_state("stop")` at `path_filter.py:406` and `:453` are the only two
  call sites in the file (`grep -n get_run_state`, 2 hits). They are **not** both "inside hot
  loops":
  - `:406` is inside `fill_histogram_from_cache` (def at `:336`), inside `for i in range(n)` at
    `:404`, polled every `_step = max(1, n // 100)` iterations. Truthy branch → bare `return`.
  - `:453` is the **first statement of** `filter_raw_event_data` (def at `:451`) — a single
    entry guard, no loop. Truthy branch → `return [], [], True`.
  Both become an explicit `cancel: threading.Event | None` threaded through the public functions.
  **The mid-loop cancellation test must target `:406`'s site specifically** — a test that only
  exercises the `:453` entry guard proves nothing about stopping a run already in progress, and
  that is the criterion's actual point.
- **`SYST_SOURCES` is already imported, never literal — so criterion (2) is nearly free and must
  be gated by a mutation, not by a run.** The reference imports it at `path_filter.py:6`
  (`from engine.systematics import BTAG_WP, SYST_SOURCES, event_syst_factor`) and loops it at
  `:382,400,439`; scout found **no hard-coded `["jec","lep","btag"]` anywhere** in the file. A
  faithful port satisfies "keyed from SYST_SOURCES" by doing nothing, so the check is: monkeypatch
  `systematics.SYST_SOURCES` to add a fourth source and require the written ROOT file to gain the
  matching `h_{src}_up` key. `BTAG_WP` is used at `:511`.
- **File sizes, for the file scope:** reference `path_filter.py` is **643** lines,
  `path_final.py` is **20**.
- **The `eval` sites stay untouched in this task** — B-008 swaps them. This must be said in
  the PR body so the reviewer does not raise it as a finding.
- **Two carry-forwards owed from B-005's cycle-1 review, both to be discharged here.**
  (1) Port `test_fill_histogram_syst_keys_created` from the reference's
  `tests/test_systematics.py` — it was dropped from B-005 because it needs `path_filter.py`,
  which this task creates, and it is the only reference test covering the `h_{src}_up`
  systematic keys. (2) Repoint `tests/test_systematics.py:137-160` — five `test_nbjets_*`
  tests currently assert against a **local reimplementation** of `_count_bjets` and so
  exercise no production code at all. Point them at the real b-jet counting inside
  `filter_raw_event_data` once it exists here.
- **Three criteria added 2026-08-21, moved here from B-004** when B-004 was ruled contract-only.
  This task already owns both files where the variation histograms are produced and persisted.
  (1) `write_final_histograms` persists **every** key in `outHist.h`; a test asserts the written
  ROOT file carries `h` plus `h_jec_up`, `h_lep_up`, `h_btag_up` for an MC sample and `h` alone for
  `data` — the reference gates this with `with_syst=(s != "data")` at `analytical_loop.py:199`.
  (2) The variation histograms are keyed from the already-vendored `systematics.SYST_SOURCES`,
  never a local literal list.
  (3) **sumw2 stays absent** — `bh.Histogram(ax)` keeps its default `Double()` storage per the
  user's ruling, and `weightsSquared` is contract-nullable in `docs/api.md`. Say so in the PR body
  so the reviewer does not raise its absence as a finding.
- **Depends on:** ~~B-005~~ — **unblocked 2026-08-21**, B-005 merged `dca1a09`.
- **Branch / PR:** `task/b-007-vendor-path-filter` — #12 @ `0578c89`
- **Status:** in review (cycle 2) — gate passed, reviewer re-dispatched 2026-08-22
- **§5.1 gate, cycle 2: PASSED** at `6457e45`. grep empty, flake8 silent, **351 passed**,
  `test_path_filter.py` + `test_systematics.py` 41 together, both new docstring tests pass.
- **Review (cycle 1):** 0 required, **1 suggested-major**, 5 suggested-minor. Posted verbatim to
  PR #12. The reviewer's verdict line read `verdict=approve` while reporting `major=1` — that is
  self-contradictory and I did **not** merge on it; §5.6 requires suggested-major = 0. Recording
  this because a verdict string that disagrees with its own counts will recur, and the counts win.
- **The suggested-major, and it is a real trap for B-008:** `path_filter.py:23-24`'s docstring
  cites the seven `eval` lines and one `compile` line as *"this file's"*. They are the
  **reference's**. In our file they are `328,370,449,508,711,723,741` and `474`. That docstring
  is the artifact B-008 navigates by, and backend §3.2 makes line numbers authoritative over
  counts. Cycle 2 makes the claim **checkable by an `ast` test** rather than a comment that rots.
- **The five suggested-minor, named individually per §5.6 — all folded into cycle 2, none lost:**
  (a) `path_filter.py:4-5` and `filter_raw_event_data`'s docstring carry a duplicated broken
  sentence left by grep-avoidance rewording; (b) `path_filter.py:46-50`'s `#:` doc-comment is
  attached to nothing; (c) `tests/test_path_filter.py:212-214` claims `_obj_from_cache` is called
  once per iteration when it is called **six times per event**, so the cancel fires at event ~19
  (5.5%), not ~117 (33%) — the PR body repeats the false claim; (d) the cycle-1 criterion-3
  mutation transcript proves the *setup guard* failing, not `assert 0 < filled < n`;
  (e) the vectorized fast path has **no cancellation poll at all**, so effective granularity is
  one *basket*, not one event — B-009 and B-011 must not assume per-event responsiveness.
- **What the review established positively, so it is not re-litigated:** a `diff -u` against the
  reference showed **no numerical or control-flow change** in 348 diff lines — only formatting,
  docstrings, type hints, the import style, the two `cancel` sites and the `_count_bjets`
  extraction. 10 of the 11 ported tests are byte-identical to the reference, the 11th differs
  only in its import path, and no assertion was softened. Two-thread cancellation isolation was
  verified independently: `A(cancelled)=0.0 B(untouched)=3000.0`.
- **§5.1 gate: PASSED.** Re-run in a detached worktree at the PR head under the *primary* venv,
  `PYTHONPATH` confirmed resolving `path_filter` into the worktree: the widened grep is empty
  (exit 1), flake8 silent, **349 passed**, `test_path_filter.py` 19, `test_systematics.py` 20.
  All reproduce the PR body exactly.
- **The coder caught a bad count of MINE, and it was right.** Criterion 5 said *"Expect: the
  collected count is 21 (20 today + the one ported test)"*. Our `tests/test_systematics.py`
  collects **19** on `main`, not 20 — I had transposed the **reference's** count (which is
  genuinely 20) onto our file. 19 + 1 = 20, which is what shipped. Verified with
  `pytest --collect-only -q` on both revisions, **not** `grep '^def test_'`, which is blind to
  class-scoped tests (the B-006 cycle-4 lesson). `test_fill_histogram_syst_keys_created` is
  genuinely present. **This is the fifth wrong count in the §2 table and the second this
  session** — the rule is not "enumerate our code", it is "enumerate the code the number is
  about". A scout enumerated the reference for me and I applied its number to us.
- **Three deviations the coder declared, all sound, none needing a ruling:** `systematics` is now
  accessed module-qualified rather than via `from ... import`, and `_count_bjets` was extracted
  as its own function — both *required* to make my own mandated monkeypatch mutations exercise
  production code instead of a dead-bound name, so my criteria forced these. Several vendored
  `E701`/`E702` lines were reformatted one-statement-per-line with arithmetic untouched.
- **The seam B-009 and B-011 plug into:** `cancel: Optional[threading.Event] = None` on both
  `fill_histogram_from_cache` and `filter_raw_event_data`.

### Cycle-by-cycle
- **Cycle 1** — 0 required, 1 suggested-major, 5 suggested-minor. The major: the module
  docstring cited the *reference's* `eval`/`compile` line numbers as this file's, and that
  docstring is the artifact B-008 navigates by. The reviewer's verdict string read
  `approve` while reporting `major=1`; the orchestrator went with the counts, not the string.
- **Cycle 2** — 0 required, 0 suggested-major, 3 suggested-minor. The coder chose to
  re-derive our own line numbers and guard them with an `ast` test rather than label them as
  the reference's. The reviewer mutated that check in **both** directions — docstring rot and
  code motion — and it went red for each.
- **The orchestrator's own defect, for the §2 table:** criterion 5 demanded `21` collected in
  `tests/test_systematics.py`. Our file has **19** on `main`; the *reference's* has 20, and
  the count was transposed from a scout report about the reference onto our file. The coder
  flagged it rather than padding to hit the number. Fifth wrong count on this project.

---

## B-010 — `RunConfig` loader and cache keys (merged `d017ead`, 2 cycles)

### B-010 — `RunConfig` loader and the content-addressed cache keys
- **Scope:** `src/fce_web/engine/runconfig.py`, `content/analyses/zpeak-dilepton.json`,
  `tests/test_runconfig.py`
- **Accept:** the loader round-trips the fixture; `h5_sel` and `h5` computed from the fixture
  match digests computed independently from the reference's own formula, shown side by side;
  changing any covered field changes the digest **and** changing an uncovered field does not —
  both asserted, which is what "content-addressed" actually means; a config carrying an
  unknown field is rejected rather than silently ignored
- **This is the gap the milestone map missed.** The `cfg` dict has **no headless producer**: it
  is built only by `compile_graph_topology()` at `ui/graph.py:1696`, ~230 lines of
  `dpg.get_value()` calls. Without something to build it, M2 has nothing to run and therefore
  no proof. **This is not a reimplementation of that function** — that is M4's job. We take
  only the six lines that compute the two md5 keys (`ui/graph.py:1866-1884`), and a
  hand-authored fixture reproducing one of the reference's saved pipelines.
- **CORRECTION 2026-08-22 — the fixture cannot be lifted from a saved config, and the digest
  has a trap.** Scout enumerated the reference. (1) The saved pipelines
  (`test_selection_cutflow.json`, `test_selection_obs_bounds.json`, `test_systs.json`) are
  **node-graph serialisations** — top-level keys `{version, next_id, nodes[], links[]}` — **not**
  `cfg`-shaped. So `content/analyses/zpeak-dilepton.json` is **hand-authored** to the `cfg` shape,
  which is the 13-key return at `ui/graph.py:1914-1923`: `energy, detector, observable, bins, min,
  max, target, h5, h5_sel, mult_cuts, sel_exprs, histograms, selections`. (2) The md5 inputs are
  **raw string concatenation with no separators**, and `bins`/`min`/`max`/`target` are **strings**
  (they come from dpg text widgets), never numbers:
  ```python
  mult_h5_base = energy + detector + str(mult_cuts)                          # ui/graph.py:1866
  h5_sel = hashlib.md5((mult_h5_base + str(sel_exprs)).encode()).hexdigest() # :1877
  h5_full = hashlib.md5(
      (h5_sel + hcfg_raw["observable"] + hcfg_raw["bins"]
       + hcfg_raw["min"] + hcfg_raw["max"] + hcfg_raw["target"]).encode()
  ).hexdigest()                                                              # :1881-1884
  ```
  If `RunConfig` normalises `bins` to `int`, the digest changes and the content-addressed cache
  silently misses every entry the desktop app wrote. The criterion asserts our digest **equals**
  one computed independently from the formula above, both shown side by side.
- **What the keys cover, and it must not drift:** `h5_sel` = energy + detector +
  `str(mult_cuts)` + `str(sel_exprs)`; `h5` extends it with observable, bins, min, max, target.
  Shared §2 says do not break this — on a shared server it is why the second student to try the
  same cuts gets an instant result.
- **The dpg node IDs** currently threaded through `cfg` purely so the engine can colour nodes
  green (`nid`, `prefix_nids`, `obs_nid`, `hist_nid`) become optional.
- **Depends on:** ~~B-005~~ — **unblocked 2026-08-21**, B-005 merged `dca1a09`.
- **Branch / PR:** `task/b-010-runconfig` — #11 @ `ae239f5`
- **Status:** in review (cycle 2) — gate passed, reviewer re-dispatched 2026-08-22
- **Review (cycle 1):** 0 required, **2 suggested-major**, 3 suggested-minor. Both majors were
  against properties **no criterion of mine gated** — §5.4 clause 3, so a cycle, not a
  re-specification. (i) `from_dict` validated only the *top-level* `h5`/`h5_sel`, while the engine
  addresses the cache with the **nested** `selections[i].h5_sel` (`analytical_loop.py:68,79`) —
  so the loud-failure guarantee missed the digests that matter. (ii) `mult_cuts` element types
  were unchecked, so `["2", ...]` instead of `[2, ...]` gives a *self-consistent* config hashing
  to `a68ec198…` instead of `c9873a70…` — a permanent silent cache miss. Both fixed in cycle 2.
- **§5.1 gate, cycle 2: PASSED** at `b7119a9`. flake8 silent, **354 passed**, `test_runconfig.py`
  25. Verified independently, not just by re-running their tests: both digests **unchanged** at
  `c9873a70…`/`fbb913c1…`; the reviewer's `a68ec198…` string-`mult_cuts` claim reproduced from
  scratch; and a direct probe confirmed a wrong nested `h5_sel` and a wrong nested `h5` are now
  each rejected with a `RunConfigError` **naming the offending path**.
- **Push-path anomaly, checked and clean.** The cycle-2 coder found the branch already checked
  out in the cycle-1 agent's worktree, so it worked on a local `work-b010-cycle2` and pushed
  `work-b010-cycle2:task/b-010-runconfig`. Verified: `ae239f5` is still an ancestor of `b7119a9`
  (`git merge-base --is-ancestor` → true), PR #11 shows 2 commits, no second PR was opened. **Not
  a force-push, no history rewritten.** The `work-b010-cycle2` branch stays, per never-delete.
- **§5.1 gate: PASSED**, and it went beyond re-running the coder's numbers. All reproduced in a
  detached worktree at the PR head under the *primary* venv (`PYTHONPATH` confirmed resolving
  `fce_web` to the worktree, not the primary checkout): flake8 silent, **350 passed**, both
  digests identical, 15 parametrised covered/uncovered cases collected. The coder also
  re-verified the 329 baseline itself and matched — no baseline mismatch, unlike PR #8 and #9.
- **Digests independently confirmed by the orchestrator**, computed straight from the reference
  formula without touching the coder's test file — the fix and its verification do not share a
  hand here. `h5_sel=c9873a70ca371612fc24cf976ff7fd5c`, `h5=fbb913c18c34530d355fdd949974ac58`,
  both matching the committed fixture. All six digest inputs confirmed `str` at hash time, so
  the normalisation trap this entry warns about was avoided.
- **One design addition the coder flagged, needing a ruling if the reviewer disputes it:**
  `from_dict` *verifies* the stored `h5`/`h5_sel` against the recomputed digest and raises on
  mismatch, rather than trusting the file. Stricter than the criteria asked. It catches a
  mis-authored fixture at load time instead of silently missing the cache forever, which is the
  failure shared §2 warns about — I am inclined to keep it. B-011/B-012 must know it raises.

### Cycle-by-cycle
- **Cycle 1** — 0 required, 2 suggested-major, 3 suggested-minor. Both majors were against
  properties **no criterion of the orchestrator's ever gated** (§5.4 clause 3 — a cycle, not a
  re-specification): nested digests unvalidated while the engine addresses the cache with them,
  and `mult_cuts` element types unchecked so `["2", ...]` yields a self-consistent config with a
  different digest. The orchestrator's criterion 3 had enumerated only *top-level* covered
  fields and never noticed the config is nested.
- **Cycle 2** — 0 required, 0 suggested-major, 2 suggested-minor. Coder independently verified
  both findings against the reference before implementing, and pushed back on neither because
  both were real.
- **Push-path anomaly, checked and benign:** the cycle-2 coder found the branch held by the
  cycle-1 agent's worktree, so it pushed `work-b010-cycle2:task/b-010-runconfig`. Verified
  `ae239f5` still an ancestor of `b7119a9` — not a force-push. This will recur whenever a
  harness worktree outlives its agent; check it, do not assume it.

### B-012 — The parity proof — cycle-by-cycle record

- **Cycle 1** (`199a6ac`): 3 required / 2 suggested-major / 4 suggested-minor —
  [comment 5381713608](https://github.com/JulesVandenbroeck/fce-site/pull/15#issuecomment-5381713608).
  R1 the `reference_render` fixture rendered the reference and never compared it to the golden —
  the circular proof C4 exists to preclude, present as a *broken instrument* rather than a wrong
  number. R2 the reference-checkout skip test failed instead of skipping on any machine without
  the checkout. R3 none of C1–C6 shipped a `Check:`/`Expect:` — a finding against the dispatch.
  M1 the cache probe wrote our engine's output over the reference render's. M2 the coverage guard
  aggregated variation keys across samples. Diagnosed a **cycle** (§5.4 clause 3). → C7, C8, C9.
- **Interrupted.** The session dispatching cycle 2 died at its context limit with 177 uncommitted
  lines in `.claude/worktrees/b012-resume`, and C7–C9's verbatim text existed nowhere but that
  dead dispatch. Recovered: the diff was snapshotted to
  `.claude/handoff/b-012-cycle2-interrupted.patch`, the criteria were rewritten with commands, and
  the coder was told to judge the recovered work rather than trust it. It kept all of it. **Not a
  cycle** — no review had seen it. *Lesson: the criteria's only durable copy is the PR body. C7–C9
  were written into a dispatch and nowhere else, and a crash erased them.*
- **Cycle 2** (`5a2a91a`): 1 required / 1 suggested-major / 1 suggested-minor —
  [comment 5381993475](https://github.com/JulesVandenbroeck/fce-site/pull/15#issuecomment-5381993475).
  R1/R2/M1/M2 fixed, each mutation-gated by the reviewer *independently of the coder's transcript*.
  R3 carried: the body claimed the commands were "carried forward unedited" and they were not.
  **M3 was created by M1's own fix** — `shutil.copytree(dirs_exist_ok=True)` defaults to
  `symlinks=False` and so dereferenced the dataset symlink, writing 376.3 MB per suite run. This
  is §5.5's whole argument in one finding: a scope narrowed to the previous cycle's findings would
  have missed a defect that the previous cycle's fix introduced. Diagnosed a **cycle** under
  clause 3 — no criterion had ever gated the probe's footprint. → C10.
- **Cycle 3** (`57939b5`): **0 / 0 / 1**, `scope=pass`, `verdict=approve` —
  [comment 5382168276](https://github.com/JulesVandenbroeck/fce-site/pull/15#issuecomment-5382168276).
  R3 closed by writing all ten `Check:`/`Expect:` pairs into the body; M3 closed by `symlinks=True`
  gated by C10, whose *instrument* the reviewer also mutation-tested — replacing the
  non-following size walk with a following one turns the gate red, so the measurement cannot
  launder a dereferenced copy under the cap. m6 backlogged.

**Suite floor:** 398 → 406 → 411 → **413**. Parity module 8 → 13 → 15 tests. checks 6 → 9 → **10**.

**What this task taught the process.** Three things, all of them cheap next time:
1. **A criterion that lives only in a dispatch is one crash from gone.** C7–C9 had to be
   reconstructed. The PR body is the durable copy; get new criteria into it the same cycle.
2. **R3 is the §5.4 carve-out working as designed.** A `Required` filed against the dispatch did
   not make either cycle a re-specification, because the *unmet* properties (R1, R2, M1, M2, M3)
   were coder defects or new ground. The limit stayed reachable and the task converged on cycle 3.
3. **Mutation-gate the instrument, not only the assertion.** Cycle 3's reviewer mutated the size
   walk itself. That is the §2 lesson — "an instrument that structurally cannot observe the
   property it certifies" — applied one level deeper than the task asked for.


---

## B-013 — post-mortem, three cycles, stopped at the §5.7 limit 2026-09-03

**The shape: every Required was against the instrument, never against the shipped behaviour.**
The production change — correcting `_ValidationProof` and `CompiledExpr`'s account of the two
forgery routes — has been correct since cycle 2 and is independently pinned by C5, which the
cycle-3 reviewer confirmed is genuinely sensitive (it swapped `dataclasses.replace` for a shim
bypassing `__init__` and the test went red). What has cycled three times is the *meta-test* that
tries to stop a false account being written into that docstring again.

| cycle | Required | the instrument at the time | how the reviewer defeated it |
|---|---|---|---|
| 1 | R1 (my dispatch: no `Check:`/`Expect:` pairs) + M1 | the docstring itself | instrumented `dataclasses.replace` and showed it *does* call `__init__`/`__post_init__` — only `object.__new__` skips them, so cycle 1's "both routes never call them" was false |
| 2 | R2 | keyword presence in a 400-char window | restated M1's false claim in different words → `1 passed`. The windows also overlapped (`replace_at=1124`, `new_at=1396`), so one arm could be satisfied by the other route's text |
| 3 | R3 + M2 | negation-polarity scan over a six-cue substring list, windows bounded at the other route's offset | "at no point invokes `__init__`" and "elides the constructor entirely … are sidestepped" both pass (false green); and a *true* clearer wording — "**does** call `__init__` … the identity check simply does not fire" — goes red (false red) |

**My defect, stated plainly, because it is the same one three times.** Each cycle I wrote an
`Expect:` that enumerated *specific mutations* rather than requiring a *decidable instrument*.
Cycle 2's Expect named one mutation — restore cycle 1's verbatim wording — which is the weakest
gate available. Cycle 3's Expect named three wordings; the reviewer defeated it with a fourth. An
enumeration of adversarial examples is a floor, never a proof, and against a prose-parsing check
the enumeration can always be extended by one. §2 already says *ask what the check prints if the
property is false* — but the missing question was **"is this property decidable by this
instrument at all?"** A regex over English is not, in either direction, and R3 and M2 are the two
directions of that one fact.

**The recommendation put to the user:** replace prose-parsing with an exact-string pin — hold the
two route clauses as a golden literal in the test and compare. Any edit to that paragraph then
fails until someone deliberately updates the golden, which is the drift guard actually wanted,
and it is decidable. It also dissolves M2: a better wording is no longer a red suite, it is a
deliberate golden update.
