# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

### B-009 — `RunContext`, replacing `RUN_STATE` in `analytical_loop.py`
- **Scope:** `src/fce_web/runs.py`, `src/fce_web/engine/analytical_loop.py`,
  `tests/test_run_context.py`
- **Accept:** `grep -rn "ui\." src/fce_web/engine/` empty across the whole package; two
  concurrent `run_physics_loop` calls with different contexts keep separate progress **and**
  separate cancellation, proven by a real two-thread test; no module-level mutable state
  (reuse the guard already in `tests/test_app.py`); the dead `samples` and `en` parameters
  removed or their retention justified in writing; `flake8` clean
- **RESOLVED 2026-08-22 — the coupling surface is fully enumerated. 27 call-site lines across
  FIVE names, not 24 across two.** The scout the last session drafted has now been run, against
  the reference's `engine/analytical_loop.py` (353 lines). The import at `:9-10` is the only
  `ui` reference in the file, and there is **no bare `ui.` attribute access anywhere** (`ui.state.X`
  never appears), so the five imported names are the entire surface:
  - `get_run_state` (7) — `:76,118,126,139,182,225,319`
  - `update_run_state` (17) — `:92,115,119,127,145,151,172,192,270,274,304,305,322,328,341,348,350`
  - `add_completed_node` (1) — `:300`
  - `add_active_node` (1) — `:303`
  - `mark_nodes_completed` (1) — `:339`
- **One unreconciled line, recorded rather than smoothed over.** This entry previously listed
  `update_run_state` at `:183`; the scout's grep reports `:305` in that slot and not `:183`.
  A line-level grep counts a line carrying two calls once, so both readings may be true. **Do not
  resolve this by picking one — the criteria below are gated on a grep and a poison test, neither
  of which depends on the count being right.** That is why they are written that way.
- **What the three node functions actually are, and why they are cheap.** From `ui/state.py:78-96`,
  all three mutate two sets in `RUN_STATE` under a shared `threading.RLock` (`STATE_LOCK`, `:4`):
  `add_active_node` unions `active_nodes`; `add_completed_node` moves one id from `active_nodes`
  to `completed_nodes`; `mark_nodes_completed` does the same for a collection, atomically.
  **`analytical_loop.py` is their ONLY caller in the entire reference** — scout grepped the whole
  repo and found definitions in `ui/state.py` and call sites in `analytical_loop.py`, nothing else.
  So they collapse to a single `on_node` callback with no second consumer to satisfy.
- **The grouping — this IS the `RunContext` design**, and it came from reading the code:
  cancellation (`:76,118,126,139,182,319`) -> a `threading.Event`; cancellation
  *acknowledgement* (`:119,127,145,183,322`) -> **deleted**, driver-owned and already
  redundant; progress (`:172-175,270,274,341`) -> `on_progress` / `on_worker`; status and
  phase (`:92,115,151,192,304,328`) -> `on_log` / `on_phase`; node highlighting
  (`:300,303,339`) -> `on_node`; `n_workers` (`:225`) -> a field; `cutflow_ready`
  (`:348-350`) -> a returned `RunResult`.
- **Two things to kill rather than port.** `progress_ctx` (`:258-267`) is a live mutable dict
  sharing **two `threading.Lock`s** with the DPG render thread; its slot-pool machinery exists
  only to drive N stacked progress bars and has no physics meaning. And the hard-coded UI layout
  constants baked into the engine — `0.78` at `:174` (twice) and `:274`, `0.80` at `:341` —
  the engine reports 0..1 of its own work and the driver scales it.
- **A bug fixed for free:** the status consumer at `ui/components.py:385-387` reads-then-blanks
  `status_msg` (written at `:92,115,151,192,328`), making it a single-slot mailbox with lossy
  overwrite — under N workers, messages are silently dropped. A real sink has no such behaviour.
- **The entry point:** `run_physics_loop(cfg, samples, active_samples, en)` at `:205`.
- **Depends on:** ~~B-007~~ (merged `d906b59`)
- **Branch / PR:** `task/b-009-run-context` — #13, head `619dc3c`
- **Status:** in progress (cycle 2) — review returned rework, re-dispatched 2026-08-22
- **Review (cycle 1):** 1 required, 1 suggested-major, 3 suggested-minor, **scope pass**.
  Posted verbatim to PR #13 as `issuecomment-5379780960`.
- **§5.4 diagnosis — this IS a cycle, not a re-specification, and the mechanical test says so.**
  Criterion 4 shipped with a command *and* a named mutation, so clause 2 does not apply; the
  property was gated from cycle 1, so clause 1 does not apply either. **But the specification
  defect underneath it is still mine**, and it is §2's own failure shape: I named the mutation
  (`* 0.78` on the progress value) without naming the *seam*, so the coder applied it at
  `_report_progress` — the one place the test does observe — and it went red exactly as I asked
  while the property stayed false everywhere else. The check could not fail at
  `_TaskTracker.increment` or at the mid-run call site, because the test drives a run with no
  data files and therefore records only the two literal endpoints `[0.0, 1.0]`.
  **The lesson, and it generalises: a mutation criterion must name the seam, or the coder will
  pick the one seam already under observation.** Cycle 2 names all three.
- **The suggested-major resolves against a recorded user ruling.** `cutflow_plotter` is deferred
  to M5/M6 by the vendor-scope ruling (see "What M2 does not do" below), so the import is dead
  *by design* rather than by accident. The reviewer's second option — document the deferral and
  pin `cutflow_ready is False` with a test — is the correct one, and cycle 2 takes it.
- **All three suggested-minor named individually (§5.6), none lost:**
  (a) `analytical_loop.py:210` does not pass `ctx.cancel` to `fill_histogram_from_cache`, so
  B-007's cancellation seam has no caller and latency is one full histogram fill — **folded
  into cycle 2**, because B-011 is built on this cancellation and shipping it uncalled would
  hand B-011 a capability nothing exercises.
  (b) `analytical_loop.py:353` reports `1.0` even when `processed_any` is `False`, so a run that
  did nothing reads as 100% success in B-011's SSE stream — **folded into cycle 2**, adjacent to
  the Required's own rework.
  (c) `runs.py:92`'s magic `n_workers = 4` — **backlogged**, because the right value probably
  comes from B-011, the first code that actually picks a worker count.
- **§5.1 gate PASSED**, re-run by the orchestrator in a detached worktree `~/fce-gate-b009`:
  suite **383 passed** / 0 failed (floor 376, +7); flake8 exit 0; criterion-4 grep empty.
  Import verified to resolve to the worktree copy, not the primary checkout — a `PYTHONPATH`
  shadow would otherwise have certified `main`'s code as the branch's.
- **Criterion 1's grep is MY specification defect, and it is not a finding against the code.**
  The pattern's `from ui` alternative matches prose, so it hits `engine/runconfig.py:134`, a
  comment reading `from ui/graph.py:1709-1719`. **Present verbatim on `origin/main`** — it
  predates the branch and is outside B-009's file scope. The coder reported it rather than
  reaching outside scope to silence it. If this recurs, anchor the pattern to import syntax
  (`^\s*(from|import)\s+ui\b`) rather than the bare words.
- **New signature, which B-011 consumes:** `run_physics_loop(cfg: dict, active_samples: List[str],
  ctx: RunContext) -> RunResult` at `analytical_loop.py:217`. `samples` and `en` removed.
- **Floors — a fall in any is a `Required`:** full suite at **376 passed** (measured by the
  orchestrator in the primary checkout at `57a2d6b`); flake8 exits 0.
- **Feasibility settled before dispatch.** All seven non-`ui` names `analytical_loop.py`
  imports already exist in our tree — `filter_raw_event_data:551`, `fill_histogram_from_cache:417`,
  `make_cache_acc:223`, `save_cache:291`, `preprocess_hep_expr:55` in `engine/path_filter.py`;
  `write_final_histograms:13` in `engine/path_final.py`; `get_fce_home:27` in `paths.py`.
  So this is vendor-plus-decouple with no dependency cascade.
- **The poison-test pattern to copy is `tests/test_path_filter.py:165`**
  (`test_path_filter_imports_with_ui_poisoned`), and the module-level-state guard to extend is
  `tests/test_app.py:142` (`test_no_module_level_mutable_state_in_the_app_module`, via its
  `_module_level_state` helper — `tests/` is a package, so it imports).


## Ready

**Both entries below are DEFERRED behind the M2 checkpoint by the user's ruling 2026-08-22.**
Neither blocks B-012, and nothing on the B-007 → B-009 → B-011 → B-012 chain touches
`safe_eval.py` or `tests/test_api_contract.py`, so the open findings cannot rot further while
they wait. Do not dispatch either until B-012 has merged. See the sequencing block below.

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

## Blocked

_The rest of M2. Plan: `~/.claude/plans/plan-m2-now-so-jazzy-hummingbird.md`._

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
- **Depends on:** B-011
- **Branch / PR:** not yet opened

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
