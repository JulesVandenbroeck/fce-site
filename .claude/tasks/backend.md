# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

### B-020 — Connection allowlist and graph -> RunConfig (**CONTRACT TASK**)
- **Scope:** `src/fce_web/graph.py`, `tests/test_graph.py`, `docs/api.md` (`## Endpoints`, :27)
- **Accept:** C1-C10 in the plan. Allowlist matches brief §4's five rows and the reference's
  `_VALID_CONNECTIONS` when `FCE_PARITY_REFERENCE_ROOT` resolves (skips otherwise);
  `DataSource` synthesised and rejected if submitted; `Observable` mode resolved; output
  accepted by `RunConfig.from_dict` without raising.
- **Depends on:** nothing. **F-005 and F-007 consume this read-only** — not merged with an open
  finding against the payload shape; reviewed at raised effort.
- **Branch / PR:** `task/b-020-graph-allowlist` at `0a6831a` — **#33, open**
- **Status:** **in review — cycle 3 re-review dispatched at raised effort**, head `5c38457`.
  Resumed from [`handoff/b-020-backend-3.md`](../handoff/b-020-backend-3.md); the coder applied
  F9 (option B — `_mission1_payload` uses both selection exprs, so the digests are
  `fbb913c1…`/`c9873a70…` and C7's zpeak claim is true again) and F10 (**kept** the multi-path
  branch, covered by one new payload test). **checks 12 → 13.**
  **Cycle-3 gate PASSED** in `~/fce-gate-b020c3` at `5c38457`: `632 passed`, flake8 0,
  `tests/test_graph.py` 17 passed, reference test skips cleanly, scope exactly the three files.
  C13's mutation is evidenced in the PR body: reversing `_selection_exprs` moves the chained
  `h5_sel` to `f44c25e3…` against the pinned `c9873a70…`.
  **Cycle 3 is the §5.7 limit.** A `rework` verdict here goes to the user, not to a cycle 4.
  The coder hit the 90% hard threshold mid-cycle and stopped cleanly. **Cycle 3 is the §5.7 limit
  and it is not yet spent** — the work was interrupted, not exhausted, so resuming it is finishing
  cycle 3, not opening a cycle 4.
  **Done at `0a6831a`:** F11 only (`docs/api.md:64-68`). **Not done:** F9, F10, C13.
  The handoff carries both decisions already made — F9 **option B** (make `_mission1_payload` use
  both selection expressions so the `zpeak-dilepton.json` comparison becomes true again) and F10
  **keep the multi-path branch and add the one payload** — plus the exact digest literals and the
  full re-derivation, so a cold successor recomputes nothing. There is no open question.
  **The suite has not been re-run since `0a6831a`.** Verify before believing anything.
  **checks 12 → 13** (C13: a shipped branch with no failing check is either deleted or given one).
- **Cycle-2 review:** `findings=3, scope=pass, verdict=rework`
  ([comment](https://github.com/JulesVandenbroeck/fce-site/pull/33#issuecomment-5582721933)).
  All eight cycle-1 findings confirmed fixed, none overruled. The reviewer **independently
  re-derived both digest literals** from `runconfig.py:362-375` without calling `graph.py` and
  confirmed them, and the field-order mutation that was green on cycle 1 is now red. The code is
  not what is in question. F9: C7's PR-body claim that the fixture matches
  `content/analyses/zpeak-dilepton.json` bit-for-bit is **reproducibly false** — `_sel_node`
  defaults to one expression, so the fixture yields `2b8e2826…`/`1d1f518b…` against the JSON's
  `fbb913c1…`/`c9873a70…`. That body is the only verbatim contract record F-005/F-007 read.
  F10: the multi-path half of the translator has no check that can fail — reversing
  `_selection_exprs` leaves all 16 green — and mission 1 is single-histogram, so it is put to the
  coder as a ladder rung-1 question, with deletion named as the preferred answer. F11: one
  missing clause in `docs/api.md`.
- **Do not confuse the two digest pairs.** `fbb913c1…`/`c9873a70…` in `## Contracts in force` are
  B-010's, for the *reference* config; `2b8e2826…`/`1d1f518b…` are B-020's mission-1 fixture.
  Different configs, no contradiction — F9 is a stale claim in a PR body, not a contract breach.
- **Cycle-2 gate (still the record):** `code-reviewer` re-dispatched 2026-09-08 **at raised effort**
  with the cycle-1 review URL and F1-F8. Cycle-2 head `1ab1bf3`. §5.1 gate **PASSED** in
  `~/fce-gate-b020`: `621 passed` (605 floor + 16), flake8 0, `tests/test_graph.py` 16 passed,
  reference test skips cleanly, scope exactly three files. Coder reports F1-F6 and F8 fixed,
  **none overruled**, F7 backlogged. `graphlib.TopologicalSorter` replaced the hand-rolled DFS.
- **Cycle-1 record:** re-dispatched 2026-09-08 with the review URL and F1-F8.
  Review `findings=8, scope=pass, verdict=rework`
  ([comment](https://github.com/JulesVandenbroeck/fce-site/pull/33#issuecomment-5582447530)).
  **checks 10 → 12**: C11 pins the mission-1 digests, C12 makes client type errors `GraphError`.
- **Review:** 8 findings, verdict=rework. **Raising the reviewer's effort paid, and this is the
  evidence to cite next time the question comes up.** F1: `RunConfig.from_dict` checks only that
  a payload's digests agree with its own fields, never that the fields are right — so swapping
  two mult-cut fields left all 14 tests GREEN, a mistranslation that would silently change the
  selection and permanently miss the content-addressed cache. F2: the purity check asserts only
  that no module-level name is assigned twice, so a textbook `CACHE = {}` mutated in a function
  passes. F3/F4: a client sending `"bins": 50` as a JSON int gets `TypeError`, and `"nlep": "2"`
  gets `RunConfigError` — both 500s under this PR's own `api.md`, for ordinary client payloads.
  F5/F6/F8 deletions (`graphlib.TopologicalSorter` replaces a hand-rolled tri-colour DFS).
  **F7 backlogged, not fixed** — the digest formula is transcribed a third time, and exporting it
  from `runconfig.py` is outside this PR's file scope. The reviewer said so itself.
- **§5.4 diagnosis — a CYCLE, clause 3, and the drafting defect is mine, the same one as F-004's.**
  Nothing was dropped (clause 1 no); C7 and C8 both shipped with commands and are met *as written*
  (clause 2 no). But C7 said "accepted by `RunConfig.from_dict` without raising" — a **method**,
  and the method became the ceiling. The property is that the translation is *correct*. Twice in
  one wave, so it is not bad luck: §2's rule is to write the property in the sentence and the
  method in the `Check:`, and I wrote only the method both times.
- **Cycle-1 gate (still the record):** §5.1 free gate **PASSED** in `~/fce-gate-b020` (detached off
  `origin/task/b-020-graph-allowlist`): `610 passed, 0 failed`, `flake8 src/ tests/ scripts/` → 0,
  `pytest tests/test_graph.py -q` → 14 passed, and the reference test skips cleanly with
  `FCE_PARITY_REFERENCE_ROOT=/nonexistent` (1 skipped, 13 deselected).
  `git diff origin/main...HEAD --name-only` returns exactly the three scoped files. Every number
  in the PR body reproduced; C1-C10 all carry IDs and evidence there — §4 rule 3 satisfied.
  **Gate note, so it is not misread later:** my *first* full-suite run in this worktree reported
  15 collection errors. That was my own environment — the wait loop started pytest before `pip
  install -e .[dev]` had finished. Re-run after install completed: 610 passed. The branch was
  never red. This is §5.1's own warning ("a check run in the same broken environment reproduces
  the error and then certifies it") landing on the gate rather than the coder.
  **The first dispatch of this task died producing nothing** (branch at `main`, clean worktree,
  no PR); confirmed against git, so **this is cycle 1, not cycle 2.**
- **Deviations reported:** `Dataset` is a plain value object the caller constructs — no
  `missions.py` or `content/missions/*.yaml` exists yet to derive it from. Flagged in the PR
  body: the digest formula imposes a global `mult_cuts` constraint on multi-branch graphs.
- **Worktree:** `.claude/worktrees/agent-a9c0de01733f3ab0c`, reused from the dead dispatch — the
  branch is checked out there, so a fresh `worktree add` would fail. The coder is told not to.

### B-019 — Engine output -> `HISTOGRAM_SCHEMA` payload (**CONTRACT TASK**)
- **Scope:** create `src/fce_web/payload.py`, `tests/test_payload.py` — nothing else.
  `docs/api.md`'s histogram section is already complete and row-parity tested.
- **Accept:** C1-C9 in the plan. Valid against all 18 `HISTOGRAM_SCHEMA` rows; bins read the
  reference's way (`uproot.open`/`f_res["h"]`/`.values()`/`.axes[0].edges()`); `systUp` keys
  absent when there are no variations; `len(counts) == len(edges) - 1`; **C5 is the crux** —
  `run_analysis` on B-018's fixture through this function peaks X1 at the Z mass within 3 GeV.
- **Depends on:** B-018 (merged). **F-008 consumes it read-only** — not merged with an open
  finding against the payload shape; reviewed at raised effort. Wave 2.
- **Branch / PR:** `task/b-019-histogram-payload` at `f9209ee` — **#34, open**
- **Status:** **in review (cycle 1)**, reviewer at raised effort. checks=9, all 9 met per the body.
  Ships `build_histogram_payload(hdir, plot_idx, mc_samples, meta, data_sample="data",
  lumi_unc=LUMI_UNC)` and `PayloadError`; the read path is ported from the reference
  `plotter.py:51-63`, not invented. **Cycle-1 gate PASSED** in `~/fce-gate-b019`:
  `621 passed` (615 floor + 6), flake8 0, scope exactly the two files.
- **Backlog candidate reported:** `run_physics_loop` resolves `get_fce_home()` with no `env`
  argument, independently of `driver.run_analysis`'s `env=` — already documented by B-018, out of
  this task's read-only scope.

## Ready

_none — B-020 (wave 1) and B-019 (wave 2) are both in progress._
Plan: [`docs/plan-m3-vertical-slice.md`](../../docs/plan-m3-vertical-slice.md).

## Blocked

### B-021 — Job registry + `POST /api/run` + `GET /api/run/{id}/result`
- **Depends on:** B-019, B-020. Wave 3.
### B-022 — SSE `GET /api/run/{id}/events` + the progress-event contract
- **Depends on:** B-021. Wave 4, closes checkpoint 1.

M2 plan (historical): `~/.claude/plans/plan-m2-now-so-jazzy-hummingbird.md`.

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
wave 7   B-015  bound analytical_loop.py:290       -+ parallel   DONE, merged 4761d9a
         B-016  close B-013's open findings        -+            DONE, merged 900dce8
```
Wave 6 is deferred behind the checkpoint by the user's ruling 2026-08-22 — nothing depends on
those three, and after B-012 the golden file is their regression net. **Do not re-order without
asking.** Rationale in [`archive/backend.md`](archive/backend.md).

**Every agent gets `isolation: "worktree"`, including single dispatches** (the 2026-08-18 D-004
incident). Check `git symbolic-ref --short HEAD` before every bookkeeping commit.

## Done

One line per task. Full entries — scope, criteria, the cycle-by-cycle review record — in
[`archive/backend.md`](archive/backend.md). Read it only when a history is actually in question.

- **B-018** — a committed, downsampled ROOT fixture the pipeline can run on — #31, `9c4c98f`,
  1 cycle, clean gate (`findings=6, verdict=approve`). checks=8, all 8 met. Suite floor → **605**.
  4 files, ~0.72 MB, 2000 events each, **downsampled from the real 91 GeV datasets, not
  synthesised** — branch names, element dtypes and values identical to the source for those
  events. X1 modal bin **90.5 GeV**, X3 **75.5 GeV**. F1-F5 backlogged (two dead assertions,
  three documentation-accuracy fixes; none touches a fixture byte or a physics number).
  **F6 is against me, not the coder:** commits `3f3e4e2`/`ca8655c` put orchestrator bookkeeping
  on the task branch, so eight `.claude/` and `docs/` files merged through this PR. The §4
  carve-out says bookkeeping goes straight to `main`; it must not ride a task branch.
  **B-019 and B-021 are released by this merge.**
- **B-017** — response-status probe for the e2e harness (**CONTRACT TASK**) — #28, `aef697f`,
  2 cycles + 1 re-spec, clean gate (`findings=1, verdict=approve`; F2 was a stale count in the
  body, corrected before merge). checks=7. Suite floor → **594**.
  **Contract, cited verbatim by F-002:** `PageActivity.bad_responses: list[tuple[str, int]]` in
  `tests/e2e/conftest.py`, each entry `(url, status)`, collected iff
  `is_bad_response_status(status)` — i.e. **status >= 400**, so redirects are not failures.
  **F-002 is released by this merge.**
- **B-015** — bounded the last live `compile()` in `engine/` — #26, `4761d9a`, 3 cycles +
  1 re-spec, clean gate at the §5.7 limit (`findings=3, verdict=approve`). checks=11. The dead
  call site at `analytical_loop.py:290` is removed and replaced by `_validate_sel_exprs`, called
  once at the top of `run_physics_loop`, routing every `sel_expr` through `safe_eval.compile_expr`
  — the early syntax gate `main` had, now bounded, which the bare `compile()` never was.
  Suite floor → **592**. **M2 is complete.** F1/F2/F3 backlogged — all three are simplifications
  of the test instrument, none is a defect in the shipped guard.
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
- Suite floor **605 passed**; flake8 0 across `src/ tests/ scripts/`. Confirmed on `main` at
  `9c4c98f`, 2026-09-08. (596 after F-002; 594 after B-017; 592 after B-015; 582 after B-016.)
- **Fixture dataset** (B-018): `tests/fixtures/datasets/IDEA/91GeV/{X1,X2,X3,data}.root`, 2000
  events each, 30 branches, regenerated byte-identically by `tests/fixtures/make_fixture.py`
  (which may fetch; the suite must not). Point `FCE_HOME` at a tmp dir when running the engine
  against it — `get_fce_home` resolves `output/` from the same root and would write into the tree.
- **e2e page observation** (`tests/e2e/conftest.py`, B-017): `PageActivity` carries
  `console_errors`, `requested_urls`, and `bad_responses: list[tuple[str, int]]` — the last
  populated by `page.on("response", ...)` in `observe()` and gated by `is_bad_response_status`,
  **status >= 400**. Redirects are deliberately not failures. Fixtures: `live_server`, `browser`,
  `page`, `index`. 25 nodeids under `tests/e2e/`.
- `docs/api.md` at **13** `^##` headings, **30** schema rows, and its `Type`/`Nullable` columns
  are row-parity tested against the schema tuples with their own meta-test (B-014). An edit to
  either the doc or the schema that breaks agreement fails `tests/test_api_contract.py`.
- **`src/fce_web/engine/path_filter.py` contains zero `eval()`/`compile()` call sites**, asserted
  against `ast` by `tests/test_path_filter.py`, with a perturbation twin (B-008).
- **`engine/analytical_loop.py` contains zero `eval()`/`compile()` call sites**, asserted against
  `ast` with a perturbation twin (B-015). `_validate_sel_exprs` (`analytical_loop.py:217-245`) is
  the single gate: it is called once at the top of `run_physics_loop`, before any cache directory
  is touched, and raises `UnsafeExpression` naming the offending expression. **`engine/` now holds
  no unbounded expression path.**