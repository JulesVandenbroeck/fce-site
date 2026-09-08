# B-021 backend cycle 2 -- handoff (90% usage stop)

Branch `task/b-021-run-api`, PR #35. Committed d5dc659 (jobs.py **does not
import** as committed -- mid-edit, see below). Working dir otherwise clean.

## Plan (from cycle-1 review, PR #35 comment 5584607751) -- fix F1-F11
F11 is ruled by orchestrator: leave `.claude/handoff/b-021-backend.anchor.md`
alone, mark `F11 ruled by the orchestrator`, do not touch it further.

## Done so far (in jobs.py, committed but broken)
- F6: `Job.ctx` is now non-Optional (required field, reordered before
  defaulted fields); `_make_ctx(events: queue.Queue) -> RunContext` (was
  `_make_ctx(job)`), so ctx can be built before the Job exists.
- F10: stripped `_config_digest`'s docstring to one line. `(Cn)` annotations
  elsewhere in jobs.py **not yet stripped** -- still need a pass over
  `jobs.py:15, 47, 74-83 (mostly done), 90, 107, 121, 143, 183, 188`.
- Added `_retag_payload(payload, mission_id)` helper for F2 (shallow-copies
  payload dict + `meta`, restamps `meta["mission"]`) -- **not yet wired into
  `submit()`**.
- Removed `from fce_web.engine.driver import _dataset_dir,
  _discover_active_samples` -- **but `_mc_samples()` (jobs.py ~257-264) still
  calls both names and is still called from `_finish` (jobs.py ~237). This
  is why the module does not import.** Must finish F9 (see below) or
  temporarily restore the import to get back to green, then redo F9 properly.

## Not started
- **F9** (permitted to touch `engine/driver.py` + `runs.py`): add
  `active_samples: Tuple[str, ...] = ()` field to `RunResult` (`runs.py`,
  import `Tuple`); in `driver.py`, pass `active_samples=tuple(active_samples)`
  at all 4 `RunResult(...)` call sites (variable already in scope at all 4).
  Then in `jobs.py`, replace `_mc_samples(config, self._env)` with
  `[s for s in result.active_samples if s != "data"]` inside `_finish`
  (renamed `_build_payload` per F7 below), delete `_mc_samples()` entirely,
  drop the now-unused `Optional`... check `Mapping`/`List` imports after.
- **F1 + F7** (the two structural fixes to `_run`/`_finish`): restructure so
  the *whole* body (run_analysis + payload build) is in one try/except that
  always sets a terminal status and always puts exactly one sentinel in a
  `finally`, AND `job.lock` is only held for the final field-assignment, not
  across the ROOT-file read. Full replacement code for `_run` and a renamed
  `_build_payload` (returns `(payload, error)`, no longer touches `job.lock`
  itself) is drafted in this session's transcript -- reconstruct from the
  requirements, do not guess: **run_analysis + `_build_payload` both stay
  inside `self._run_lock`** (C3's disk-collision fix, do not lose it);
  `job.lock` moves to wrap *only* the `job.status/error/payload = ...`
  assignment after the `with self._run_lock:` block exits.
- **F2 wiring**: in `submit()`'s cache-hit branch, pass
  `payload=_retag_payload(cached.payload, mission_id)` instead of
  `payload=cached.payload`.
- **F6 wiring in `submit()`**: build `events = queue.Queue()`, `ctx =
  _make_ctx(events)` *before* the `with self._lock:` block, pass both into
  every `Job(...)` construction (cache-hit and fresh), so `job.ctx` is never
  `None` and is set before insertion into `self._jobs`. Delete the
  `job.ctx = _make_ctx(job)` line currently at jobs.py:184 (post-insertion).
- **F8**: bound `self._jobs` (make it an `OrderedDict`, add `_MAX_JOBS =
  500` module constant with a `ponytail:` comment, evict oldest
  non-`"running"` job on insert once over cap). Not started at all.
- **F3** (C1 reopened): rewrite `test_jobs.py:67-75` and
  `test_api_run.py:60-65` to actually observe `submit()` returning before
  the run finishes -- block `run_analysis` on a `threading.Event` the test
  controls (monkeypatch), assert `job.status == "running"` immediately after
  `submit()` returns, then release the event and let it finish.
- **F5** (C6 reopened): new test -- submit two jobs so the second is queued
  behind `_run_lock`, call `job_b.ctx.cancel.set()` while job A still holds
  the lock, assert job B reaches `status == "cancelled"` with the sentinel
  on its queue.
- **F4 / C10** (new criterion, total checks -> 10): one test draining a
  completed job's `events` queue asserting >=1 `{"type": "progress"}` item
  and exactly one terminal `{"type": "done", ...}` as the *last* item; and a
  cache-hit job's queue holding only the sentinel (one item).
- **F1 verification** (required by the dispatch): monkeypatch
  `fce_web.jobs.build_histogram_payload` to raise `RuntimeError` (not
  `PayloadError`), submit a job, wait, assert it reaches a terminal
  `status` and the sentinel is on the queue within a few seconds. Paste
  this transcript in the final report.
- Still need: `flake8 src/ tests/ scripts/` clean, `pytest tests/ -q` full
  green (>= 649 + new), PR #35 body appended (never rewritten) with the new
  C10 criterion + updated F<n> fixed/overruled list for all 11, via
  `gh pr edit 35 --body-file <path>`.

## Dead ends / notes
- Do not move `run_analysis`/payload-build fully outside `self._run_lock` --
  that lock is what fixes C3's real cross-job ROOT-file corruption (see
  jobs.py module docstring). F7 only wants `job.lock` narrowed, not
  `_run_lock`.
- `Job` dataclass field order: non-default fields (`id`, `mission_id`,
  `ctx`) must precede defaulted ones (`events`, `lock`, `status`, ...) --
  already fixed in the committed state.

## Immediate next step for whoever resumes
1. Finish F9 in `runs.py` + `driver.py`, then finish wiring `_mc_samples`
   removal in `jobs.py` so the module imports again.
2. Run `python -c "import fce_web.jobs"` to confirm green before touching
   anything else.
3. Work the remaining list top to bottom; re-run `pytest tests/test_jobs.py
   tests/test_api_run.py -q` after each fix.
