# Back end — completed task archive

Full entries for every merged back end task, moved out of `.claude/tasks/backend.md` so that
`/orchestrate` no longer loads the whole project history on every session start.
Nothing here was deleted or edited — these are the entries verbatim.

**Read this file on demand only.** When a task's history is actually in question, open
it. Never at startup.

---

## Done — most recent first


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

## Post-mortems — tasks still in flight

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
- **History:** [`archive/backend.md` § Post-mortems](archive/backend.md) — the 47%-wrong-home
  concurrency defect, and the false-green PR body that produced the §5.1 pre-review gate.
