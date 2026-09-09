# Back-end tasks

Owned by `backend-coder`. Maintained by the orchestrator — see
`.claude/orchestrator/CLAUDE.md` §6 for the entry format and the rules.

IDs are `B-nnn`, allocated in order and never reused.

---

## In progress

### B-021 — Job registry + `POST /api/run` + `GET /api/run/{id}/result`
- **Scope:** create `src/fce_web/jobs.py`, `routes/api.py`, `tests/test_jobs.py`,
  `tests/test_api_run.py`; modify `app.py`, `docs/api.md`
- **Accept:** C1-C9 (cycle 1, verbatim in PR #35) + **C10** (cycle 2: the `Job.events` contract
  B-022 consumes is asserted, not only documented). checks=10. Suite floor 639 -> 649 on the branch.
- **Depends on:** B-019, B-020 — both merged.
- **Branch / PR:** `task/b-021-run-api` — #35, head `73dc1de` (pushed, **RED**)
- **Status:** **in review loop — cycle 2 re-dispatched 2026-09-09** (worktree). Prior stop: see [`handoff/b-021-backend-2.md`](../handoff/b-021-backend-2.md),
  which is **on the task branch, not on `main`**. The coder stopped at 90% of the 5h limit with
  `src/fce_web/jobs.py` **not importing**: F9's `_dataset_dir`/`_discover_active_samples` imports
  were removed while `_mc_samples()` still calls them. F6 is done and committed, F10 partial,
  `_retag_payload` (F2) exists but is not wired in. F1/F7/F8/F3/F5/F4 are planned in the handoff
  and not written. **No test or flake8 run since `9b5527b` — do not trust "649 passed" for cycle 2.**
  Resume at the handoff's step 1. Cycle 1 review: `findings=11, verdict=rework`, posted to the PR
  (`#issuecomment-5584607751`). §5.1 gate passed (649 passed, flake8 0, reproduces the body).
- **Review:** 11 findings. **F1 a permanent hang** — the worker's `try/except` wrapped only
  `run_analysis`, so a later exception left `status="running"` with **no sentinel**, hanging
  B-022's drain loop forever. **F2** a cache-hit job returned the *first* submitter's
  `meta.mission` to a different student. **F3/F5** C1 and C6 were certified by checks that
  structurally could not fail (the reviewer's Mutation C passed against C1's checks). **F4** the
  progress-queue contract was documented in three places and asserted in none -> **C10**.
  F6-F10 cheap, riding cycle 2. **This is a cycle, not a re-specification** (§0 ruling 1: a
  missing `Check:` no longer makes one, and nothing was dropped from an earlier cycle).
- **Watch:** the coder serialised engine execution through `JobRegistry._run_lock` after finding
  a real cross-run corruption (`output/hist{plot_idx}_{sample}.root` is addressed by `plot_idx`
  alone and resolves `get_fce_home()` from the real process env, ignoring the registry's `env`).
  Argued in writing in the PR body; the per-job output dir needs `analytical_loop.py`, out of scope.
- **Ruling on F11, 2026-09-08:** an anchor written by a coder working in a **worktree** may ride
  the task branch. Shared §8 mandates writing it, and it cannot reach the primary checkout from
  inside a worktree without reaching outside its own tree, which is worse. The §4 carve-out still
  forbids everything else on a task branch. Add `.claude/handoff/<id>-<role>.anchor.md` to the
  standard dispatch file scope.
- **Against me, 2026-09-08:** I dispatched cycle 2 into the **primary working directory**, so the
  coder checked the branch out there and my next bookkeeping edit landed on the task branch's
  HEAD instead of `main`. Recovered with a `main` worktree at `~/fce-bookkeeping`, which is where
  bookkeeping is written for the rest of this session. **A serial dispatch still needs a worktree
  — the primary checkout is the orchestrator's, not a free workspace.**
- **Note:** wave 3 is running **in series** on the user's instruction, not parallel.
- Plan: [`docs/plan-m3-vertical-slice.md`](../../docs/plan-m3-vertical-slice.md).

## Ready

_none — F-005 and F-006 are wave 3 but frontend; see `frontend.md`._

## Blocked

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

- **B-020** — connection allowlist and graph -> `RunConfig` (**CONTRACT TASK**) — #33,
  `1909046`, **4 cycles** (the 4th authorised by the user past the §5.7 limit) + 1 handoff mid
  cycle 3, clean gate (`findings=0, verdict=approve`). checks=14. Suite floor → **639**.
  Ships `src/fce_web/graph.py`: the connection allowlist as a single authoritative Python
  definition — it previously existed only as prose in `docs/design-brief.md` §4 and as
  `isLegal()` in `bench.html:258` — plus the student-graph -> `RunConfig` translation.
  `DataSource` is synthesised at submit and rejected if a client sends one; `Observable`'s mode
  is resolved to the engine subtype. **F-005 and F-007 are released by this merge.**
  **The cost of raised-effort review, recorded because it was asked for:** across four cycles it
  caught a field-swap mistranslation that left all 14 tests green, a purity check a `CACHE = {}`
  would pass, two ordinary client payloads that 500'd, a false bit-for-bit claim in the contract
  record, and finally F12 — a documented 400 with no check able to fail. Three guards are now
  mutation-verified: `_shared_mult_cuts`, `_selection_exprs`, `_MULT_CUT_FIELDS`.
  **F7 remains backlogged** — the digest formula is transcribed a third time; exporting it from
  `runconfig.py` was outside this PR's file scope, as the reviewer itself said.
- **B-019** — engine output -> the `HISTOGRAM_SCHEMA` payload (**CONTRACT TASK**) — #34,
  `fff8ca3`, 2 cycles, clean gate (`findings=4, verdict=approve`; **all four folded in before
  merge**). checks=10. Suite floor → **621**.
  **Contract, verbatim in PR #34's body, which F-008 is dispatched read-only against:**
  `build_histogram_payload(hdir, plot_idx, mc_samples, meta, data_sample="data",
  lumi_unc=LUMI_UNC) -> dict`, plus `PayloadError`. `samples[].weightsSquared` is
  **unconditionally `None`** — no stat error bars; `systSources` is **derived** from which
  samples actually carried a template, not fixed; `systUp` is always present and may be `{}`,
  and it is the per-source keys that are absent rather than empty arrays.
  The bin-reading path is ported from the reference `plotter.py:51-63`, not invented.
  **C5 is the milestone fact: `run_analysis` on B-018's fixture through this function peaks X1
  within 3 GeV of the Z mass** — the first end-to-end run of the pipe in this repo.
  F5-F8 folded in: the length check now reuses `test_api_contract`'s
  `_check_sample_array_lengths_coherent`/`_check_data_length_matches_bins` (which also closed a
  latent `KeyError`), and `_check_edges` was deleted in favour of one inline guard.
  **B-021 is released by this merge, once B-020 lands.**
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
- Suite floor **639 passed**; flake8 0 across `src/ tests/ scripts/`. Confirmed on `main` at
  `1909046`, 2026-09-08. (605 after B-018; 615 after F-004; 621 after B-019; 639 after B-020.)
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