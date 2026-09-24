# B-034 anchor

Worktree: .claude/worktrees/agent-a6d3b155cef1bbbbd, branch task/b-034-progress (not yet pushed).

## Decisions
- No app.py edit (out of scope, B-035 owns it). Added `JobRegistry.env` property (jobs.py)
  so api.py/pages.py can call `store.*` with the same env the app was built with
  (`request.app.state.jobs.env`), instead of app.state growing a second copy.
- Cookie: name `fce_student`, value `"{classCode}:{nickname}"` (both fields are colon-free
  by their own regex/alphabet), HttpOnly + SameSite=Lax.
- `Job` gains `student: Optional[Tuple[str,str]]` and `graph_json: Optional[str]`, set at
  submit() time (both cache-hit and fresh branches) — completion recording uses the
  *submitter's own* graph/identity, never a cache donor's.
- Unlock rule computed by iterating missions sorted by `.order`: state is "done" if in
  completed set, "open" if previous mission's state was "done" (first mission's "previous"
  defaults true), else "locked". Reused for /api/progress, POST /api/run gating, and GET /'s
  current-mission pick.
- `unlocked` in /result's objective = the mission whose order is job's mission.order+1, if
  any, computed only when objective.met and job.student is set; record_completion is called
  there too — relies on store's own INSERT OR IGNORE idempotency, no extra flag needed.
- N38 F2 fixed: `missions[job.mission_id]` direct index (mission always exists), dropped
  `if mission else None`. N38 F3 fixed: jobs.py:60-66 comment condensed to 2 lines.

## Done so far
- jobs.py: env property, Job.student/graph_json fields, comment trims. NOT yet wired
  submit()'s call sites to set student/graph_json — that's the immediate next step.

## Next steps
1. Finish jobs.py: submit() signature gains `student=None`, `graph_json` computed from
   `json.dumps(graph, sort_keys=True)`, passed into both Job(...) constructions.
2. routes/api.py: add `_COOKIE_NAME`, `_resolve_student`, `_progress_body` helpers; wire
   POST /api/join, GET /api/progress, gate POST /api/run, add `unlocked` to /result.
3. routes/pages.py: GET / context per C5 (current_mission, missions, student), using
   `_resolve_student`/progress helper — either import from api.py or duplicate minimally
   (ponytail: check which is less code before duplicating).
4. docs/api.md: document /api/join, /api/progress, updated /result objective.unlocked,
   and "Page context" heading for C5.
5. tests/test_progress.py: the one C7 check (join→run M-1→unlocked M-2→progress→rejoin→
   purge→cookie invalid; M-2-locked run→400).
6. Run full suite + flake8, PR.

No dead ends yet — straightforward wiring, just needs finishing.
