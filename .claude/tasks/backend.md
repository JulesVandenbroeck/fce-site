# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

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
- **Status:** cycle 2 in progress.
- **Review:** cycle 1 — 1 required (my bad criterion, waived), 3 suggested-major, 1
  suggested-minor. Cycle 2 fixes the concurrent write-probe defect, adds the import-graph
  test, and corrects the `systematics.py` header prose; suggested-major 3 carries forward to
  B-007.
- **History:** [`archive/backend.md` § Post-mortems](archive/backend.md) — the 47%-wrong-home
  concurrency defect, and the false-green PR body that produced the §5.1 pre-review gate.

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
- **Status:** in review (cycle 1), dispatched 2026-08-20.
- **Review:** cycle 1 in flight. Delivered at parity with raw `eval` (0.85–1.38×); 104 tests.
- **History:** [`archive/backend.md` § Post-mortems](archive/backend.md) — the coder caught
  two errors in my dispatch (seven `eval` sites, not eight; `Subscript` contradiction), both
  since corrected in `.claude/backend/CLAUDE.md` §3.2.

## Ready

### B-004 — Extend the histogram contract with systematics, cutflow, and fit payloads
- **Scope:** `docs/api.md`, plus the run-pipeline plumbing that has to persist the
  per-source variation histograms
- **Accept:** §Histogram payload carries `systUp` (per-source up-variation counts),
  `lumiUnc`, and `systSources`; the cutflow payload (stage names, per-stage per-sample
  counts, efficiency) and the fit payload (mu, Z) are specified — neither exists anywhere
  today
- **Unblocked 2026-08-20.** Its stated blocker was D-003, which merged as `99ec8f3` on
  2026-08-17; the field names in `docs/design-explorations/payload.json` have been through
  four reviews. The list had simply not been updated. **It belongs to M3, not M2** — it is an
  API-contract task whose consumer is the first vertical slice — so it waits here rather than
  being dispatched with the M2 batch.
- **Why it exists.** The user ruled for full plot parity, and parity commits this. The
  reference `///` "Syst. unc." band is built in `fce-project/fce/engine/plotter.py:105-125`
  from per-source up-variation templates `h_{src}_up` for `jec`, `lep`, `btag`, added in
  quadrature with a flat `LUMI_UNC = 0.025`. `docs/api.md:44` carries `weightsSquared`,
  which is the *statistical* error and **cannot produce that band**. Verified by reading both
  files, not inferred from the docs.
- **Related, and worth settling in the same task:** the run payload should carry a typed
  `nodes[] + edges[]` list only, with coordinates and slot indices in a separate `ui` object
  the engine ignores — so the choice of graph style never leaks into the physics config.
- **Branch / PR:** not yet opened

## Blocked

_The rest of M2. Plan: `~/.claude/plans/plan-m2-now-so-jazzy-hummingbird.md`._

### B-007 — Vendor `path_filter.py` and `path_final.py`, decoupled from `ui.state`
- **Scope:** `src/fce_web/engine/path_filter.py`, `src/fce_web/engine/path_final.py`,
  `tests/test_path_filter.py`
- **Accept:** `grep -rn "ui\." src/fce_web/engine/path_filter.py` empty; the 11 ported
  reference tests pass; a new test drives a real cancellation mid-loop and asserts the loop
  stops — the reference has no such test; `flake8` clean
- **The whole coupling is two lines.** `get_run_state("stop")` at `path_filter.py:406` and
  `:453`, both cooperative cancellation checks inside hot loops. They become an explicit
  `cancel: threading.Event | None` threaded through the public functions.
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
- **Depends on:** B-005
- **Branch / PR:** not yet opened

### B-008 — Route `path_filter.py`'s expressions through `safe_eval`
- **Scope:** `src/fce_web/engine/path_filter.py`, `tests/test_path_filter_exprs.py`
- **Accept:** `grep -rnE "\beval\(|\bcompile\(" src/fce_web/engine/` returns nothing —
  that is **seven** `eval` sites plus one `compile`, not eight; the count in this entry was
  wrong until B-006 checked the reference and reported it;
  golden value tests prove the vectorised path and the per-event fallback produce **identical
  numbers** on the same events; an `UnsafeExpression` propagates to the caller and is **not**
  swallowed by the bare `except Exception: pass` at `:262`; the escape expression fed in as a
  selection is refused before any event is read; mutation-tested
- **New ground, not a port:** the reference suite has zero tests asserting what any expression
  evaluates to, so it would pass against a broken evaluator. That gap is why criterion 2 exists.
- **Depends on:** B-006, B-007
- **Branch / PR:** not yet opened

### B-009 — `RunContext`, replacing `RUN_STATE` in `analytical_loop.py`
- **Scope:** `src/fce_web/runs.py`, `src/fce_web/engine/analytical_loop.py`,
  `tests/test_run_context.py`
- **Accept:** `grep -rn "ui\." src/fce_web/engine/` empty across the whole package; two
  concurrent `run_physics_loop` calls with different contexts keep separate progress **and**
  separate cancellation, proven by a real two-thread test; no module-level mutable state
  (reuse the guard already in `tests/test_app.py`); the dead `samples` and `en` parameters
  removed or their retention justified in writing; `flake8` clean
- **The ~22 `RUN_STATE` sites grouped by what they are for** — this grouping *is* the
  `RunContext` design, and it came from reading the code, not from the milestone map:
  cancellation (`:76,118,126,139,182,319`) -> a `threading.Event`; cancellation
  *acknowledgement* (`:119,127,145,183,322`) -> **deleted**, driver-owned and already
  redundant; progress (`:172-175,270,274,341`) -> `on_progress` / `on_worker`; status and
  phase (`:92,115,151,192,304,328`) -> `on_log` / `on_phase`; node highlighting
  (`:300,303,339`) -> `on_node`; `n_workers` (`:225`) -> a field; `cutflow_ready`
  (`:348-350`) -> a returned `RunResult`.
- **Two things to kill rather than port.** `progress_ctx` (`:258-267`) is a live mutable dict
  sharing **two `threading.Lock`s** with the DPG render thread; its slot-pool machinery exists
  only to drive N stacked progress bars and has no physics meaning. And the hard-coded `0.78`
  / `0.80` in the progress arithmetic are *UI layout constants baked into the engine* — the
  engine reports 0..1 of its own work and the driver scales it.
- **A bug fixed for free:** the status consumer at `ui/components.py:385-387` reads-then-blanks
  `status_msg`, making it a single-slot mailbox with lossy overwrite — under N workers,
  messages are silently dropped. A real sink has no such behaviour.
- **Depends on:** B-007
- **Branch / PR:** not yet opened

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
- **What the keys cover, and it must not drift:** `h5_sel` = energy + detector +
  `str(mult_cuts)` + `str(sel_exprs)`; `h5` extends it with observable, bins, min, max, target.
  Shared §2 says do not break this — on a shared server it is why the second student to try the
  same cuts gets an instant result.
- **The dpg node IDs** currently threaded through `cfg` purely so the engine can colour nodes
  green (`nid`, `prefix_nids`, `obs_nid`, `hist_nid`) become optional.
- **Depends on:** B-005
- **Branch / PR:** not yet opened

### B-011 — Headless driver
- **Scope:** `src/fce_web/engine/driver.py`, `tests/test_driver.py`
- **Accept:** a run driven entirely from Python with no `ui` import anywhere in the process;
  progress callbacks fire monotonically from 0 to 1; cancelling mid-run returns a `RunResult`
  marked cancelled with partial output; skips cleanly with a **named reason** when
  `~/.fce/datasets/` is absent
- `run_analysis(config: RunConfig, ctx: RunContext) -> RunResult`, replacing
  `run_engine.execute_analysis` — which is already dearpygui-free and already headless, and
  whose only real defect is that it returns `None` and puts its answers in globals. Per the
  vendor-scope ruling it stops once the histogram ROOT files are written: no plotting, no fit.
- **Depends on:** B-009, B-010
- **Branch / PR:** not yet opened

### B-012 — The parity proof — **M2 checkpoint**
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
- **Depends on:** B-011
- **Branch / PR:** not yet opened

#### M2 sequencing, and the one rule that is not negotiable
```
wave 1   B-005  vendor paths + systematics      -+ parallel
         B-006  safe_eval                       -+
wave 2   B-007  vendor path_filter (decoupled)  -+ parallel
         B-010  RunConfig + cache keys          -+
wave 3   B-008  path_filter -> safe_eval        -+ parallel
         B-009  RunContext + analytical_loop    -+
wave 4   B-011  headless driver
wave 5   B-012  parity proof            <- CHECKPOINT
```
**Every agent gets `isolation: "worktree"`, including single dispatches.** The 2026-08-18
D-004 incident was a *single* coder checking a task branch out in the main working directory,
and it put the orchestrator's own bookkeeping commits onto a task branch and into the diff the
reviewer read. Check `git symbolic-ref --short HEAD` before every bookkeeping commit.

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

## Done

Full entries — scope, criteria, and the cycle-by-cycle review record — are in
[`archive/backend.md`](archive/backend.md). Read it only when a task's history is actually in
question.

- **B-003** — Playwright harness and a screenshot helper — `task/b-003-playwright-harness` #4,
  merged `a212e42` (2 cycles, clean gate)
- **B-002** — FastAPI app factory and a served index route — `task/b-002-app-factory` #3,
  merged `ff801fa` (2 cycles, clean gate)
- **B-001** — Python package skeleton, packaging, and a green test suite — no PR; predates the
  branch-per-task policy (1 cycle, no rework)
