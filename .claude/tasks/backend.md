# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

### B-015 — Bound or remove the expression reaching `analytical_loop.py:290`
- **Scope:** `src/fce_web/engine/analytical_loop.py`, `tests/test_analytical_loop_expr_bound.py`,
  `tests/test_run_context.py`
- **Branch / PR:** `task/b-015-bound-loop-expr` — **#26**, cycle-1 head `7899231`
- **Status:** **cycle 3 dispatched** 2026-09-04 — the §5.7 limit. **C1-C11, checks=11.**
- **Review (cycle 2):** 1R / 0M / 2m — [PR #26 comment](https://github.com/JulesVandenbroeck/fce-site/pull/26#issuecomment-5540111544).
  R1 and M1 fixed. `_validate_sel_exprs` (`analytical_loop.py:217-245`, called at `:270`) restores
  the early gate *and* bounds it — strictly stronger than `main`'s bare `compile()`, and the
  reviewer's mutation 3 proved C8 is **not** satisfiable by reinstating the old call. 588 passed.
  **R2:** the m1 fix narrowed the guard — `_compiled_sel_exprs_reference_sites` misses a read via
  `cfg.get("compiled_sel_exprs", [])`, the idiom this codebase actually uses. Instrument, not code;
  the property holds today. → C10. m3 (C8's `-k bound` selects the whole file) → C11.
  **m2 backlogged:** the gate covers `sel_exprs` only — a mistyped *observable* still hits the
  `except Exception` swallow in a worker. Pre-existing, outside B-015's remit.
- **Three blind instruments on this one task, all mine:** C3 (`pytest tests/ -q` prints 583 either
  way), C8 (`-k bound` matches the file name), C9 (enumerated "assignment or subscript" without
  enumerating how this codebase reads cfg keys). Counting cycle 2 as a **cycle**, not a third
  consecutive re-specification — C9 shipped with commands, and declaring re-spec again would put
  the §5.7 limit permanently out of reach. **If cycle 3 does not converge, escalate to the user.**
- **Review (cycle 1):** 1R / 1M / 1m — [PR #26 comment](https://github.com/JulesVandenbroeck/fce-site/pull/26#issuecomment-5540011186).
  M1: the deleted `compile()` was dead as an *optimisation* but live as an early **syntax gate** —
  `sel_exprs=["l1.pt >>> 20"]` raised `SyntaxError` on `main` and now returns a completed-looking
  `RunResult(processed_any=False)`, the real failure swallowed by `analytical_loop.py:314-317`.
  Security is not weakened; `path_filter` still validates before any event is touched.
  R1: the PR body dropped the `Check:`/`Expect:` lines my dispatch carried. m1 folded into C9.
- **Why a re-specification, not a cycle:** C3 *did* ship with a command — but `pytest tests/ -q`
  prints `583 passed` whether or not the syntax gate exists, so the instrument was structurally
  blind to the property it certified (§2). My defect. I also framed "dead" as *zero readers of the
  produced value* and never asked what the **call** did.
- **Resolution wanted:** validate `sel_exprs` once at the top of `run_physics_loop` through
  `safe_eval.compile_expr` — restores the gate *and* bounds it, which the old `compile()` never was.
- **Gate history:** cycle 1's first gate failed on a fabricated transcript (`5 passed` for a file
  that never held more than 3 tests); corrected body-only, head unmoved. Also not a cycle.
- **Depends on:** ~~B-008~~ merged `7d5fa0a`.
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

- **B-016** — closed B-013's two open findings on the `safe_eval` docstring pin — #27, `900dce8`,
  2 cycles, clean gate (0R/0M/0m). checks=6. Test-side only. The pin is now anchored to the
  **whole docstring**, so a contradicting claim anywhere reddens it, not only inside the two
  pinned route clauses; `_assert_whole_docstring_pinned` is the single shared comparison and
  `test_route_goldens_agree_with_full_docstring_golden` stops the three goldens drifting apart.
  C8's record on PR #17 is corrected with a marker-preserving mutation. Suite floor → **582**.
  **B-013's findings are closed; nothing carries forward.**
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