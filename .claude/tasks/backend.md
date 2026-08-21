# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

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

- **B-005** — Vendor `paths.py` and `engine/systematics.py` — `task/b-005-vendor-paths-systematics`
  #8, merged `dca1a09` (3 cycles, **clean gate — 0 required, 0 suggested-major**; 1 carry-forward
  to B-007, 2 suggested-minor backlogged)
- **B-003** — Playwright harness and a screenshot helper — `task/b-003-playwright-harness` #4,
  merged `a212e42` (2 cycles, clean gate)
- **B-002** — FastAPI app factory and a served index route — `task/b-002-app-factory` #3,
  merged `ff801fa` (2 cycles, clean gate)
- **B-001** — Python package skeleton, packaging, and a green test suite — no PR; predates the
  branch-per-task policy (1 cycle, no rework)
