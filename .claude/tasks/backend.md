# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

_none_ — M2 is complete. Wave 6 (B-008, B-013, B-014) is released by the
B-012 merge; see the sequencing block below.

## Ready


**Released 2026-08-31 by the B-012 merge (`928c1ba`).** Both are dispatchable. They share no
files with each other and none with B-008, so all three of wave 6 may run in parallel — one
worktree each.

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
- **Depends on:** ~~B-006~~ (merged `ce4dcd6`), ~~B-007~~ (merged `d906b59`), ~~B-012~~ (merged
  `928c1ba`). **Released 2026-08-31.** The golden file `tests/fixtures/golden/zpeak-dilepton.json`
  and `tests/test_engine_parity.py` are now this task's regression net — a routing change that
  alters any bin fails parity.
- **Branch / PR:** not yet opened
- **History:** [`archive/backend.md`](archive/backend.md) — the seven-vs-eight `eval` count settled,
  the `ast.Pow` resolution and what is given up by it, and the superseded open question.

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

_none._ Plan: `~/.claude/plans/plan-m2-now-so-jazzy-hummingbird.md`.

#### M2 sequencing — RE-ORDERED 2026-08-22 on the user's ruling
```
wave 1   B-005  vendor paths + systematics      -+ parallel     DONE, merged dca1a09
         B-006  safe_eval                       -+              DONE, merged ce4dcd6
wave 2   B-007  vendor path_filter (decoupled)  -+ parallel     DONE, merged d906b59
         B-010  RunConfig + cache keys          -+              DONE, merged d017ead
wave 3   B-009  RunContext + analytical_loop                    DONE, merged 1689b27
wave 4   B-011  headless driver                                 DONE, merged 82ef336
wave 5   B-012  parity proof            <- M2 CHECKPOINT     DONE, merged 928c1ba
wave 6   B-008  path_filter -> safe_eval        -+ RELEASED by the B-012 merge
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

- **B-012** — the parity proof (**M2 checkpoint**) — #15, `928c1ba`, 3 cycles, clean gate
  (0R/0M/1m), converged on the §5.7 limit. Suite floor → **413**. m6 backlogged.
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
- Suite floor **413 passed**; flake8 0 across `src/ tests/ scripts/`