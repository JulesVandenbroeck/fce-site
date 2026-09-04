# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

### B-016 — Close B-013's two open findings: anchor the docstring golden, correct the C8 record
- **Scope:** `src/fce_web/safe_eval.py`, `tests/test_safe_eval.py`
- **Accept:** C1 a contradicting statement anywhere in `CompiledExpr.__doc__` makes the meta-test
  fail (mutation applied by a pytest plugin at three positions, never by editing the repo);
  C2 B-013's C8 evidence re-run so a mutation preserving all four route markers shows the golden
  equality failing, pasted here and commented on PR #17; C3 suite >= 580 + flake8 0; C4 scope by
  `git diff main...HEAD --name-only`. **C1-C4, checks=4.**
- **Depends on:** ~~B-013~~ merged `87428ee`.
- **Branch / PR:** `task/b-016-safe-eval-doc-anchor` — PR not yet opened
- **Status:** dispatched 2026-09-04 (cycle 1), `backend-coder`, own worktree
- **History:** [`archive/backend.md`](archive/backend.md)

### B-015 — Bound or remove the expression reaching `analytical_loop.py:290`
- **Scope:** `src/fce_web/engine/analytical_loop.py`, `tests/test_analytical_loop_expr_bound.py`
  (new), `tests/test_run_context.py`
- **Accept:** C1 zero `eval()`/`compile()` call sites in `analytical_loop.py` asserted against
  `ast` — or, if a live consumer is found, the expression bounded by `MAX_EXPR_LENGTH` /
  `MAX_AST_NODES` with `UnsafeExpression` raised; C2 a perturbation twin proving C1's checker
  fires on a source that does contain `compile(...)`; C3 suite >= 580; C4 flake8 0; C5 scope by
  `git diff main...HEAD --name-only`. **C1-C5, checks=5.**
- **Facts given at dispatch (scout, 2026-09-04):** `:290` is the file's only `compile(` site,
  inside `run_physics_loop` (`:217`); its list reaches only `branch_cfg["compiled_sel_exprs"]`
  (`:132`), and **that key has zero readers** in `src/` or `tests/` — so removal is the primary
  outcome and bounding is the written fallback. `preprocess_hep_expr` is defined **twice**
  (`path_filter.py:70`, `safe_eval.py:257`). Only `tests/test_run_context.py:25` imports the module.
- **Depends on:** ~~B-008~~ merged `7d5fa0a`.
- **Branch / PR:** `task/b-015-bound-loop-expr` — PR not yet opened
- **Status:** dispatched 2026-09-04 (cycle 1), `backend-coder`, own worktree
- **History:** [`archive/backend.md`](archive/backend.md)

## Ready

_none — wave 7 is the last of M2, and both of it are in progress._

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
wave 6   B-008  path_filter -> safe_eval        -+ DONE, merged 7d5fa0a
         B-013  close B-006's open findings     -+ DONE, merged 87428ee
         B-014  close B-004's open findings     -+ DONE, merged db085dd
wave 7   B-015  bound analytical_loop.py:290       -+ parallel   DISPATCHED 2026-09-04
         B-016  close B-013's open findings        -+            DISPATCHED 2026-09-04
```
Wave 6 is deferred behind the checkpoint by the user's ruling 2026-08-22 — nothing depends on
those three, and after B-012 the golden file is their regression net. **Do not re-order without
asking.** Rationale in [`archive/backend.md`](archive/backend.md).

**Every agent gets `isolation: "worktree"`, including single dispatches** (the 2026-08-18 D-004
incident). Check `git symbolic-ref --short HEAD` before every bookkeeping commit.

## Done

One line per task. Full entries — scope, criteria, the cycle-by-cycle review record — in
[`archive/backend.md`](archive/backend.md). Read it only when a history is actually in question.

- **B-014** — closed B-004's presence/nullability + doc-parity findings — #18, `db085dd`,
  1 cycle, clean gate (0R/0M/3m). checks=4; C2 **implemented, not overruled**. 134 → 286 cases,
  18 → 25 test functions, none dropped or softened. Suite floor → **580**. m1/m2/m3 backlogged.
- **B-013** — closed B-006's two open findings on `safe_eval` — #17, `87428ee`, 4 cycles + 1
  re-spec, **merged on the user's ruling with M1 and M2 open** (PR #17 comment `5539...`).
  checks=6 (C6/C7 retired for C8, the one deliberate substitution in the task's history, on the
  user's §5.7 ruling). Suite floor → **415** on its own; **426** after B-008. 2 open → **B-016**.
- **B-008** — `path_filter.py` routed through `safe_eval` — #19, `7d5fa0a`, 3 cycles + 1 re-spec,
  clean gate (0R/0M/0m). checks=5. Suite floor → **426**. C1 **deviated in writing and accepted**:
  `analytical_loop.py:290`'s live `compile()` is out of scope and is now **B-015**. **B-015 is
  released by this merge.**
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
- **`DataSource` is synthesised at submit, not sent by the client** (M1 ruling, 2026-09-01). It
  left the node palette — V1 is 91 GeV only and the mission declares its dataset — but the
  vendored engine's `_VALID_CONNECTIONS` still makes it the root of every chain. So the
  `POST /api/run` builder adds one from the mission's dataset before the payload reaches the
  engine. **The engine is not modified.** The student's graph and the engine's graph are
  deliberately not the same object; M3 owns writing this into `docs/api.md:29-34`, which still
  marks that endpoint undefined. Full ruling: `design.md` `## Decisions in force`.
- Suite floor **580 passed**; flake8 0 across `src/ tests/ scripts/`. Confirmed on `main` at
  `db085dd`, 2026-09-04. (413 before B-008; 426 after B-008 + B-013.)
- `docs/api.md` at **13** `^##` headings, **30** schema rows, and its `Type`/`Nullable` columns
  are row-parity tested against the schema tuples with their own meta-test (B-014). An edit to
  either the doc or the schema that breaks agreement fails `tests/test_api_contract.py`.
- **`src/fce_web/engine/path_filter.py` contains zero `eval()`/`compile()` call sites**, asserted
  against `ast` by `tests/test_path_filter.py`, with a perturbation twin (B-008). The last live
  `compile()` in `engine/` is `analytical_loop.py:290` — inert today, unbounded, and B-015's job.