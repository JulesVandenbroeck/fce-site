# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

### B-004 — Define the histogram, cutflow, and fit payload contracts
- **Scope:** `docs/api.md`, `tests/test_api_contract.py`. `docs/design-explorations/payload.json`,
  `plot.js` and `verify.py` are **read-only input** (design-owned).
- **Accept:** every field in the enumeration below documented with type and nullability;
  `payload.json` validates against the contract; the systematics band formula documented verbatim
  and independently re-implemented in the test; the eight reference semantics written as
  actionable prose; every assertion mutation-tested with both transcripts in the PR body;
  `pytest tests/ -q` green and `flake8` clean.
- **Depends on:** nothing. Its stated D-003 blocker was stale bookkeeping — D-003 merged `99ec8f3`
  on 2026-08-17; corrected 2026-08-20.
- **Branch / PR:** `task/b-004-api-contract` — #10, head `372321e`
- **Status:** in review (cycle 1) — reviewer dispatched at raised effort
- **Gate:** passed on the second pass. **The send-back cost no cycle** — branch head never moved
  from `372321e`; both passes were PR-body-only, as §5.1's two precedents were.
  - *Pass 1 failed.* All six numbers reproduced (41 / 28+13 / 4+37 / 236 full suite / flake8 silent
    / 13 `^##` headings, `stub` narrowed to M3+M5), but the 14 mutation entries carried **no pytest
    output anywhere in the body** and the body stated the mutations called the module's `_check_*`
    helpers directly rather than running the tests. A helper raising was shown; the named test
    going red was not. B-006 cycle 4's shape — an instrument that cannot observe what it certifies.
  - *Pass 2 passed.* 14 verbatim pytest pairs, each with a `=== FAILURES ===` block, an
    `E AssertionError`, a `FAILED tests/test_api_contract.py::test_<name>` line and a
    `1 failed, 40 deselected` summary, then a restored `1 passed`. All 14 collected functions
    covered; `md5sum` of the test file identical after every restore; `git status` clean.
- **Delivered counts, recorded so §5.3 can catch a fall:** `tests/test_api_contract.py` has **14
  test functions / 41 collected** (the surplus is parametrisation of the doc-drift check over
  schema field names); `docs/api.md` has **13** `^##` headings, up from 7 on main.
- **Disclosed by the coder, and left for the reviewer to weigh:** 2 of the 14 —
  `test_band_is_nonnegative` and `test_band_frac_zero_where_stack_zero` — cannot be turned red by
  any payload-only mutation, because they are structurally guaranteed by a correct `_compute_band`;
  showing them red required temporarily mutating `_compute_band` itself. The coder said so plainly
  rather than hiding it, which is the behaviour the gate exists to produce.
- **Plan:** `~/.claude/plans/continue-b-004-giggly-hanrahan.md`

**Scope corrected 2026-08-21 (user ruling).** The entry previously read "`docs/api.md`, plus the
run-pipeline plumbing that has to persist the per-source variation histograms". **There is no run
pipeline** — `path_filter.py`, `path_final.py`, `analytical_loop.py`, `runs.py` and `driver.py` do
not exist; `src/fce_web/` is `app.py`, `paths.py`, `safe_eval.py`, `routes/pages.py` and
`engine/systematics.py`. The files that would persist `h_{src}_up` are already inside **B-007's**
file scope. B-004 is contract-only; the persistence requirements moved to B-007.

**The gap this closes.** `docs/api.md` is 71 lines, still marked `Status: **stub.**`, and its
`### Histogram payload` documents three things: `edges`, `samples[{name, counts, weightsSquared}]`,
`data`. `docs/design-explorations/payload.json` — 788 lines, four D-003 review cycles, consumed by
`plot.js` and `verify.py` — carries `meta`, `lumiUnc`, `systSources`, per-sample `systUp`,
`cutflow` and `fit`. The contract and its only concrete instance disagree, and nothing checks that.

**The field enumeration — named, not counted** (41 edges / 40 bins; samples `X1`, `X2`, `X3`; two
cutflow stages): `meta{mission, detector, energy, xLabel, processNames}`, `edges`, `lumiUnc`,
`systSources`, `samples[]{name, counts, weightsSquared, systUp{jec, lep, btag}}`, `data`,
`cutflow{stages, samples, counts, totalRaw, efficiencyPct}`,
`fit{mu, muErr, significanceZ, thresholds{evidence, discovery}}`, plus the new `fit.method`.
`cutflow.counts` is nested `{stage: {sample: int}}`, **not** a flat array. Payload is camelCase
throughout, and the contract says so.

**Why the contract is more than a field list — three traps, none written down anywhere today:**
- The band sums variations **over samples first**, then takes the per-bin fractional delta against
  the summed nominal (`plotter.py:107-118`). Reversing that order gives a different band.
  Variations are **up-only**; the band is mirrored, not separately fitted.
- `significanceZ` is capped at `_SIG_CAP = 10.0` (`fitter.py:13`), in all three code paths.
- `mu` and `significanceZ` come from three statistically distinct paths — a pyhf HistFactory MLE
  fit, a counting ratio `n_tot/s_tot` when there is no background sample (`fitter.py:89-98`), and
  `s/√b` after a bare `except Exception` (`:194-203`) — with **no field saying which**. Hence the
  new `fit.method`.

**Two ghost fields, documented nullable (user ruling).** `weightsSquared` has no producer: the
reference builds `bh.Histogram(ax)` with default `Double()` storage, so no sumw2 is tracked or
written anywhere, and `verify.py:993-1001` already records the field as unconsumed by the rendered
error bars. `fit.muErr` has no producer either — `run_fit` returns a bare `(mu, sig)` tuple and
`fitter.py` is not vendored until M5/M6. Neither triggers an engine change; both are specified
nullable with a written note on what would produce them.

**Cutflow efficiency is MC-only (user ruling)**, matching `payload.json`'s `efficiencyPct`. The
reference divides by all active samples *including* pseudo-data (`cutflow_plotter.py:70-83`) while
computing its stacked-bar composition from MC only (`:64-68`) — two sample sets, two formulas, one
plot. Mixing pseudo-data into an efficiency denominator alongside MC is arithmetically meaningless.
The divergence is deliberate and is written into the contract with its reason.

**Deliberately out of scope: the run-request contract.** This entry used to float "a typed
`nodes[] + edges[]` list with coordinates in a separate `ui` object". That is `POST /api/run`, not
the histogram response, and it is **blocked on the user's D-007 choice** — Beamline, Bench and
Board persist structurally different things (an ordered edge list vs `{x, y}` vs
`{column, slotIndex}`). Specifying it now would guess at the decision the checkpoint exists to make.

## Ready

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
- **Depends on:** nothing — B-006 is merged. Can run in parallel with B-007 and B-010.
- **Branch / PR:** not yet opened

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
- **Depends on:** ~~B-005~~ — **unblocked 2026-08-21**, B-005 merged `dca1a09`.
- **Branch / PR:** not yet opened

## Blocked

_The rest of M2. Plan: `~/.claude/plans/plan-m2-now-so-jazzy-hummingbird.md`._

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
- **Depends on:** ~~B-006~~ (merged `ce4dcd6`), B-007
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
