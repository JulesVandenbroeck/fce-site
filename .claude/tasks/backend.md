# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

### B-012 — The parity proof — **M2 checkpoint**
- **Scope:** `scripts/render_reference.py`, `tests/fixtures/golden/zpeak-dilepton.json`,
  `tests/test_engine_parity.py`. `src/fce_web/` is out of scope deliberately — a parity proof
  whose author adjusted the implementation until it matched proves nothing.
- **Accept:** C1 every bin matches within a stated, justified tolerance, and the per-source
  `h_{src}_up` variations too; C2 perturbing one bin fails the test *naming that bin*, and a
  sub-tolerance perturbation still passes; C3 the test skips with a named reason when either the
  datasets or the reference checkout is absent; C4 the content-addressed cache cannot cross
  between the two runs, mutation-gated; C5 `"ui" not in sys.modules` after the golden is
  produced; C6 `pytest tests/` green, floor **406 passed**, flake8 0 across `src/ tests/ scripts/`;
  **C7** the `reference_render` fixture's own fresh output is diffed against the committed golden
  (closes R1 — today nothing compares them, so a golden regenerated from *our* engine would still
  pass and the proof would be circular); **C8** the cache-crossing probe does not overwrite
  `reference_render`'s output dir (M1); **C9** the variation-key coverage guard asserts per-sample,
  not aggregated across samples (M2). **checks=9.**
- **Depends on:** B-011 (merged `82ef336`). Last task before the M2 checkpoint.
- **Branch / PR:** `task/b-012-parity-proof` — #15
- **Status:** cycle 2 dispatched 2026-08-22. Cycle 1 (work landed `199a6ac` in an interrupted
  session, PR opened on resume): **3 required, 2 suggested-major, 4 suggested-minor** —
  https://github.com/JulesVandenbroeck/fce-site/pull/15#issuecomment-5381713608. §5.1 gate passed
  first: 406 passed, flake8 0, both reproduced in a detached `$HOME` worktree.
  **Diagnosis (§5.4):** a cycle, not a re-specification. R2 (a test that goes red on any machine
  without the reference checkout) and M1 (the probe mutating a fixture documented as immutable)
  are coder defects against standards held elsewhere. R1 is mine as well as the coder's — C1's
  `Check:` ran the parity test, which passes whether or not the reference render is ever
  consulted; that is §2's "instrument that structurally cannot observe the property", and C7 is
  the corrected instrument. R3 (no `Check:`/`Expect:` survived into the PR body) is fixed in the
  cycle-2 dispatch and does not by itself make a re-specification.
  Checkpoint task: stop and report to the user when it merges. **C4's answer, from cycle 1:** the
  cache **does** cross when both runs share one `FCE_HOME` (0.08 s vs 78.9 s), so the fixtures'
  `FCE_HOME` isolation is load-bearing, not decorative.
- **Suggested-minor, all four backlogged individually:** m1 stale ~30s figure in the 10s-bound
  docstring at `:341`; m2 PR body says "6 samples", golden has 7; m3 unused `worst` at `:304,314`;
  m4 `_compare` iterates golden keys only, so an extra key in our output is invisible.
- **History:** [`archive/backend.md`](archive/backend.md) — method ruling and rejected
  alternatives, the headless-feasibility evidence, the observed import transcript, and why C4
  exists (circular-proof hazard). Read it before writing the next cycle's dispatch.

## Ready


**Both entries below are DEFERRED behind the M2 checkpoint by the user's ruling 2026-08-22.**
Neither blocks B-012, and nothing on the B-007 → B-009 → B-011 → B-012 chain touches
`safe_eval.py` or `tests/test_api_contract.py`, so the open findings cannot rot further while
they wait. Do not dispatch either until B-012 has merged. See the sequencing block below.

### B-014 — Close B-004's two open findings: falsify the presence/nullability halves, guard the doc columns
- **Scope:** `tests/test_api_contract.py`, `docs/api.md`
- **Accept:** C1 the schema meta-test gains presence and nullability mutations (delete / set
  `None`, require a raise **naming the path**), mutation-gated — rebinding `_check_path_conformant`
  without the two asserts yields `134 passed` today and must yield many failures after; C2 the
  `Type`/`Nullable` columns of `docs/api.md` are row-parity tested against the schema tuples, with
  its own meta-test; C3 `systUp`'s key set asserted against `systSources`; C4 the two
  `nxt.extend(...) if ... else ...` expressions become statements. checks=4.
- **Floors — a fall in any is `Required`:** 18 test functions / **134** cases; `docs/api.md` at
  **13** `^##` headings; full suite **329 passed**.
- **Depends on:** nothing (B-004 merged). **Deferred behind B-012.** Parallel with B-013; never
  with anything editing `docs/api.md`.
- **Branch / PR:** not yet opened
- **History:** [`archive/backend.md`](archive/backend.md) — the two findings stated so they are
  not re-litigated, and the standing invitation to overrule C2 in writing.

### B-013 — Close B-006's two open findings: isolate the length cap, end the docstring contradiction
- **Scope:** `src/fce_web/safe_eval.py`, `tests/test_safe_eval.py`
- **Accept:** C1 `test_expression_over_length_cap_is_rejected` fails when `MAX_EXPR_LENGTH` is
  raised — payload over the length cap but **under** `MAX_AST_NODES`, plus the isolation assertion
  the node-cap sibling carries at `:316`; C2 `_ValidationProof`'s docstring drops "An unforgeable
  token"; C3 the two bypass tests stop pinning the weakness; C4 the `_ASSERT_STRIPPING_ENV_VARS`
  note recorded so a later cleanup does not read it as dead code. Each is an
  assertion-that-cannot-fail, so each is gated by break → named test red → restore → green; paste
  all four transcript pairs. checks=4.
- **Depends on:** nothing (B-006 merged). **Deferred behind B-012.** Then parallel with B-007, B-010.
- **Branch / PR:** not yet opened
- **History:** [`archive/backend.md`](archive/backend.md) — why the length cap guards a surface the
  node cap structurally cannot (the 5.6 MB / 1.68 s measurement, the 501-digit 3-node payload), and
  why the docstring contradiction matters to B-008.

## Blocked

_The rest of M2. Plan: `~/.claude/plans/plan-m2-now-so-jazzy-hummingbird.md`._

### B-008 — Route `path_filter.py`'s expressions through `safe_eval`
- **Scope:** `src/fce_web/engine/path_filter.py`, `tests/test_path_filter_exprs.py`
- **Accept:** C1 `grep -rnE "\beval\(|\bcompile\(" src/fce_web/engine/` returns nothing;
  C2 golden-value tests prove the vectorised path and the per-event fallback produce **identical
  numbers** on the same events — new ground, the reference suite asserts nothing about what any
  expression evaluates to; C3 an `UnsafeExpression` propagates and is **not** swallowed by the bare
  `except Exception: pass`; C4 the escape expression fed in as a selection is refused before any
  event is read; C5 `test_docstring_eval_compile_line_numbers_match_this_file` stays green.
  All mutation-gated. checks=5.
- **Navigate by OUR line numbers, never the reference's.** In `src/fce_web/engine/path_filter.py`
  as of `6457e45`: `eval` at **335, 377, 456, 515, 718, 730, 748**, `compile` at **481**. They
  shift the moment this task edits the file, which is what C5 exists to catch.
- **`CompiledExpr` is not a safety certificate** — `object.__new__` and `dataclasses.replace` both
  forge one. Route through `compile_expr`; never accept a caller's `CompiledExpr` as evidence.
- **Depends on:** ~~B-006~~ (merged `ce4dcd6`), B-007. **Deferred behind B-012** — nothing depends
  on B-008, and running it after the checkpoint makes the golden file its regression net.
- **Branch / PR:** not yet opened
- **History:** [`archive/backend.md`](archive/backend.md) — the seven-vs-eight `eval` count settled,
  the `ast.Pow` resolution and what is given up by it, and the superseded open question.

#### M2 sequencing — RE-ORDERED 2026-08-22 on the user's ruling
```
wave 1   B-005  vendor paths + systematics      -+ parallel     DONE, merged dca1a09
         B-006  safe_eval                       -+              DONE, merged ce4dcd6
wave 2   B-007  vendor path_filter (decoupled)  -+ parallel     DONE, merged d906b59
         B-010  RunConfig + cache keys          -+              DONE, merged d017ead
wave 3   B-009  RunContext + analytical_loop                    DONE, merged 1689b27
wave 4   B-011  headless driver                                 DONE, merged 82ef336
wave 5   B-012  parity proof            <- M2 CHECKPOINT     <- IN PROGRESS
wave 6   B-008  path_filter -> safe_eval        -+ after the checkpoint
         B-013  close B-006's open findings     -+
         B-014  close B-004's open findings     -+
```
Wave 6 is deferred behind the checkpoint by the user's ruling 2026-08-22 — nothing depends on
those three, and after B-012 the golden file is their regression net. **Do not re-order without
asking.** Rationale in [`archive/backend.md`](archive/backend.md).

**Every agent gets `isolation: "worktree"`, including single dispatches** (the 2026-08-18 D-004
incident). Check `git symbolic-ref --short HEAD` before every bookkeeping commit.

## Done

One line per task. Full entries — scope, criteria, the cycle-by-cycle review record — in
[`archive/backend.md`](archive/backend.md). Read it only when a history is actually in question.

- **B-011** — headless driver — #14, `82ef336`, 2 cycles, clean gate. Suite → **398**.
- **B-009** — `RunContext` replaces `RUN_STATE` — #13, `1689b27`, 2 cycles, clean gate.
- **B-010** — `RunConfig` loader + content-addressed cache keys — #11, `d017ead`, 2 cycles, clean.
- **B-007** — vendored `path_filter.py`/`path_final.py`, decoupled — #12, `d906b59`, 2 cycles, clean.
- **B-006** — `safe_eval.py` — #9, `ce4dcd6`, 3 cycles + 1 re-spec, §5.7 limit; 2 open → **B-013**.
- **B-005** — vendored `paths.py` + `engine/systematics.py` — #8, `dca1a09`, 3 cycles, clean.
- **B-004** — histogram/cutflow/fit payload contracts — #10, `d4ddec8`, 3 cycles + 2 re-specs,
  §5.7 limit; 2 open → **B-014**.
- **B-003** — Playwright harness + screenshot helper — #4, `a212e42`, 2 cycles, clean.
- **B-002** — FastAPI app factory + served index — #3, `ff801fa`, 2 cycles, clean.
- **B-001** — package skeleton, packaging, green suite — no PR (predates branch-per-task).

## Contracts in force

The facts a future dispatch consumes. Everything else about these tasks is in the archive.

- `run_physics_loop(cfg: dict, active_samples: List[str], ctx: RunContext) -> RunResult` (B-009)
- `run_analysis(config, ctx, env=None) -> RunResult` — stops before plotting/fitting (B-011)
- Cache digests: `h5_sel=c9873a70ca371612fc24cf976ff7fd5c`, `h5=fbb913c18c34530d355fdd949974ac58`
  (B-010, verified three ways from the reference formula, not from the loader)
- `RunConfig.from_dict` **raises** `RunConfigError` on any digest mismatch — never warns (B-010)
- Cancellation seam: `cancel: Optional[threading.Event] = None` on `fill_histogram_from_cache`
  and `filter_raw_event_data`. Granularity is one **basket**; the vectorised path never polls (B-007)
- Suite floor **398 passed**; flake8 0 across `src/ tests/ scripts/`