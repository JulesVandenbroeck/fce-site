# B-021 anchor — job registry, POST /api/run, GET /api/run/{id}/result

Status: implementation complete, suite green (649 passed, 0 flake8), about to
commit + open PR. If interrupted before the PR exists, resume from here.

## Decisions
- `_V1_DATASET = Dataset("91 GeV", "IDEA")` hardcoded in jobs.py -- missions.py
  doesn't exist yet; missionId is still threaded through to payload meta.
- Cache-hit keyed on `json.dumps(config.to_dict(), sort_keys=True)`, an
  in-memory dict on JobRegistry (not the engine's disk cache).
- Progress queue: `Job.events: queue.Queue[dict]`, shapes documented in
  jobs.py docstring and docs/api.md -- named explicitly for B-022.
- Real defect found in testing (C3): `output/hist{plot_idx}_{sample}.root` is
  addressed by plot_idx only, shared across all jobs via the real process
  env (`get_fce_home()` with no arg, inside analytical_loop.py, out of file
  scope). Two concurrent jobs with the same plot_idx corrupted each other.
  Fixed with `JobRegistry._run_lock` serializing the run_analysis+payload-read
  section only -- jobs stay independently submitted/tracked/cancellable,
  only disk I/O queues. ponytail comment in jobs.py names the upgrade path.

## Dead ends
- None significant.

## Next step
Commit, push, `gh pr create`, report done. Branch: task/b-021-run-api.

## Verification already run
pytest tests/ -q -> 649 passed. flake8 src/ tests/ scripts/ -> clean.
