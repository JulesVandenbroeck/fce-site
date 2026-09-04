# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

**RELEASED BY THE USER 2026-09-02.** The hold placed on 2026-09-01 — pending the M1 style
choice — is lifted for all three. **The user's instruction is explicit: DO NOT run them in
parallel.** One at a time, each to completion before the next is dispatched, in the standing
merge order **B-013 (#17), then B-008 (#19), then B-014 (#18)** — **B-008 merged out of that
order on 2026-09-04**, because B-013 is escalated and blocked on a user ruling and the two PRs'
file sets are disjoint (`safe_eval.py`/`test_safe_eval.py` vs `path_filter.py` + its two test
files), so the ordering bought nothing once B-013 stalled. **B-013's branch is now behind `main`:
merge `main` into it before the next cycle. Never rebase.** This overrides the
2026-08-31 parallel dispatch pattern; the reason is the user's token budget, not a file
conflict. Each still gets `isolation: "worktree"`.

Where each one stands when it is picked up: **B-013 (#17)** cycle-1 review was dispatched
2026-08-31 and never returned a verdict — re-dispatch the reviewer, still cycle 1, gate already
reproduced. **B-014 (#18)** the same — reviewer re-dispatch, still cycle 1, gate reproduced.
**B-008 (#19)** is at the §5.7 limit: cycle 2 came back `0R / 1M / 2m` with M3 open, the cycle-3
dispatch was lost and never landed, and the branch head is still `fba2ad6`. Re-dispatching it is
**cycle 3, not cycle 4**, and if it does not close at 0R/0M, stop and escalate rather than
dispatch a fourth.

**2026-09-04:** B-008 merged. **B-013 (#17) is escalated** — cycle 4 came back `0R / 2M / 1m`;
awaiting the user's ruling between a re-specification adding C9 and merging with M2 open.
**B-014 (#18)** is next in the queue: reviewer re-dispatch, still cycle 1, gate reproduced.
Counts in the entries below were enumerated by `scout` at `fe8dd2d`, not inherited.

### B-013 — Close B-006's two open findings
- **Scope:** `src/fce_web/safe_eval.py`, `tests/test_safe_eval.py`
- **Accept:** **checks=7.** C1 length cap isolated from the node cap in both directions; C2 the
  "unforgeable token" claim dropped; C3 the bypass tests stop blessing the weakness;
  C4 `_ASSERT_STRIPPING_ENV_VARS` says what breaks without it; C5 each forgery route's mechanism
  pinned by observation; C6 the `CompiledExpr` docstring asserted against that mechanism; C7 that
  assertion gated by paraphrase mutations, not by a verbatim restore. Verbatim in PR #17's body.
- **Depends on:** nothing (B-006 merged).
- **Branch / PR:** `task/b-013-safe-eval-findings` — **#17**, `ae1efcf`
- **Status:** **cycle 4 reviewed 2026-09-04: `0R / 2M / 1m`, `verdict=rework`, scope pass.
  ESCALATED to the user — past the §5.7 limit, awaiting a ruling.** Comment `5537939571`.
  R3 **fixed** and proven not to be a marker-presence check: the reviewer built its own mutation
  with all four markers preserved and the golden equality still went red on both arms, plus a
  whitespace-only positive control that passed. M2 (cycle 3) **resolved by design** — the truer
  wording fails on the golden, which is correct under a pin. m3 fixed.
  **M1 is PR-body-only.** The pasted (a)-(c) failure messages are start-marker lookups and do not
  reproduce; (c)'s names the wrong arm entirely. The instrument is sound — the reviewer
  established that independently — but the *recorded evidence* never exercises
  `tests/test_safe_eval.py:865,875`, the assertions C8 exists for. No code change; re-run the gate
  with a marker-preserving mutation and paste it.
  **M2 is a §5.3 substitution and it is my act, not the coder's.** The golden pins two bounded
  clauses, so a contradicting sentence *elsewhere* in `CompiledExpr.__doc__` passes silently —
  verified: appending a blanket "neither route ever executes `__init__`" gives `1 passed`. That is
  cycle 1's M1 error re-entering undetected. Cycle 2's meta-test rejected a blanket phrase;
  retiring C6/C7 for the golden dropped that guard. The user's ruling was to replace the
  *instrument*, not to stop guarding the property. **So the fix is a RE-SPECIFICATION under §5.4
  clause 1 — adding C9 (the blanket-claim shape absent from the whole docstring, or the golden
  anchored to the enclosing paragraph) — and it does NOT count as cycle 5.** checks 6 -> 7.
  The user ruled at the §5.7 limit (2026-09-03) to spend a fourth cycle on a **golden-string pin**
  rather than merge with the instrument open. **C6 and C7 are RETIRED and replaced by C8 — my
  substitution, on that ruling, and the one deliberate one in this task's history.** The property
  is gated more strongly, not abandoned: the two route clauses of `CompiledExpr.__doc__` are now
  literal goldens compared after whitespace normalisation, so prose-parsing is gone entirely
  (`grep '_polarity\|_NEGATION_CUES'` exits 1). **checks=6** — C1-C5, C8.
  **Next move: dispatch the cycle-4 reviewer on #17.** Tell it two things: (i) under a golden pin
  a *truer* wording going red is CORRECT behaviour, not a finding — that was M2 and it is resolved
  by design, not by evasion; (ii) the coder reports mutations (a)-(d) failing by "naming the
  missing route-clause marker" — check the golden comparison itself can fail, not only the marker
  lookup, or C8 is a marker-presence check wearing a golden's hat.
- **Review:** cycle 1 `1R/1M/1m`, cycle 2 `1R/0M/1m`, cycle 3 `1R/1M/1m`, cycle 4 not yet run.
  R3 and M2 are what cycle 4 answers. m1 backlogged; m2, m3 fixed.
- **Gate:** `ae1efcf` reproduced 2026-09-03 — 415 passed / 0 failed (floor 413), flake8 0,
  `-k docstring` 1 passed, `grep` exit 1, diff = the two scoped files. Earlier: `5782fa8` reproduced — 415 passed (floor 413), flake8 0, diff = the two scoped files.
- **History:** [`archive/backend.md`](archive/backend.md)

### B-014 — Close B-004's two open findings
- **Branch / PR:** `task/b-014-api-contract-findings` — **#18**, `3e3550f`
- **Status:** cycle 1 in review. §5.1 gate in `~/fce-gate-b014`: **286** collected (from 134),
  **565 passed**, flake8 0, **13** `^##` headings, diff touches only `tests/test_api_contract.py`
  — reproduced exactly. C2 **implemented, not overruled**: schema tuples extended to
  `(type, presence, doc_type_label)`, and `docs/api.md` needed no edit because it already agreed
  in every cell. **Suite floor becomes 565 when this merges**, not before. **checks=4.** C1 presence + nullability mutations, parametrised
  1:1 with the schema tuples; C2 `docs/api.md` Type/Nullable row parity (**overrulable in
  writing**); C3 `systUp` keys ⊆ `systSources`, per sample; C4 the two ternary statements.
- **Enumerated:** 18 test functions / 134 cases / 13 `^##` headings. The entry's old "329 passed"
  suite floor was **stale** — it is **413**.

## Ready


**Released 2026-08-31 by the B-012 merge (`928c1ba`); all three dispatched in parallel
2026-08-31, one worktree each.** They share no files. B-008 and B-013 do share a *symbol*:
B-008 routes `path_filter.py` through `safe_eval`, and B-013 edits `safe_eval.py`. B-013's edits
are a docstring, a test isolation assertion and a comment — no behaviour change — so the two
cannot corrupt each other while in flight, only at the merge.
**Merge order: B-013, then B-008, then B-014.** If B-008's branch has fallen behind by then,
merge `main` into the branch. Never rebase.

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

### B-015 — Bound and validate the expression reaching `analytical_loop.py:290`
- **Scope:** `src/fce_web/engine/analytical_loop.py`, plus tests. Opened 2026-09-01 out of
  B-008's cycle-1 review (R2), which found C1 unsatisfiable within B-008's file scope.
- **Why:** `compile(preprocess_hep_expr(e), '<sel>', 'eval')` at `analytical_loop.py:290` is the
  last live `compile()` in `src/fce_web/engine/`. It is **functionally inert today** — verified,
  not assumed: the list it builds reaches only `branch_cfg["compiled_sel_exprs"]`
  (`analytical_loop.py:132`), `path_filter` no longer reads that key, and an instrumented golden
  run put all 1,424,355 evaluations through `safe_eval`. `compile()` alone executes nothing, so
  there is no RCE at that line today. **What is not inert:** the expression reaching it has had
  no validation and no size bound, so `safe_eval.py:75-80`'s `MAX_EXPR_LENGTH` /
  `MAX_AST_NODES` caps do not protect that path — a deeply nested student expression still
  reaches the parser unbounded.
- **Accept:** either the call site goes, or the expression reaching it is bounded by the same caps
  as every other path, with a test that fails if the bound is removed.
- **Depends on:** ~~B-008~~ **merged `7d5fa0a` 2026-09-04 — RELEASED.** B-008's own C1 deviation
  points here, and the reviewer confirmed the line is inert but unbounded.

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
- Suite floor **426 passed**; flake8 0 across `src/ tests/ scripts/`. (413 before the B-008 merge.)
- **`src/fce_web/engine/path_filter.py` contains zero `eval()`/`compile()` call sites**, asserted
  against `ast` by `tests/test_path_filter.py`, with a perturbation twin (B-008). The last live
  `compile()` in `engine/` is `analytical_loop.py:290` — inert today, unbounded, and B-015's job.