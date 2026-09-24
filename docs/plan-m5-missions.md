# M5 — Missions and progression

Status: **design and plan approved by the user 2026-09-24.**
Predecessor: [`plan-m4-recipe-builder.md`](plan-m4-recipe-builder.md).

## Context

M4 made every node configurable, but the app still has no idea missions exist: the mission panel
hard-codes M-1 (`templates/shell.html:82`), `missionId` on `POST /api/run` is an unvalidated string
(`routes/api.py:31`), the dataset is hard-coded (`jobs.py:66`, `_V1_DATASET`), and there is no
`store.py`, `missions.py`, `sqlite3` or identity anywhere in `src/`. M5 makes the core loop's last
step real: *meet the objective → the page gets stamped → the next mission opens*, and it persists.

## User rulings (2026-09-24)

1. **Scope: machinery + M-1 only.** M-2 exists as an authored stub so unlocking is observable;
   M-2..M-4 objectives, cutflow purity and the pyhf fit are M6.
2. **PyYAML is added** as a dependency. Missions stay `content/missions/*.yaml`.
3. **M-1 is checked automatically from the run** — no student-typed number.
4. **Class codes come from a teacher CLI**; students can only join an existing code. Purge is CLI.
5. **The completing graph is stored** with the completion (feeds D-011 later).

## Design

**Mission file** (`content/missions/m-1.yaml`, validated at startup; a bad file fails `create_app`
with the file and field named):
`id, order, title, brief, dataset {energy, detector}, cards [kinds], observable_modes [modes],
objective {type, ...}, hints [str], success str`.
Objective types in M5: `peak_position {sample: data, target: 91.19, tolerance: 3.0}` and `none`
(cannot complete — M-2's stub). Tolerance 3.0 GeV is a proposal and yours to change in the YAML.

**M-1 check** (pure function, `missions.evaluate(mission, payload) -> {met, value, message}`): over
every Histogram in the payload, take the `data` sample's modal bin; met iff its centre is within
`tolerance` of `target`. Default 50 bins / 0-150 GeV gives a 3 GeV bin at 90-93 → met. Miss copy
names the value found ("your peak is at 82.5 GeV") — a margin note, never an error.
*Ceiling:* a diphoton-mass plot (X5) also peaks at 91 GeV and would pass; accepted for M5.

**Gating is enforced both sides.** The browser shows locked kinds/modes inert and labelled "opens in
M-n" (brief §4); the server rejects a run whose graph uses a kind or mode the mission does not offer
(400 naming the node — B-026's contract).

**Identity.** `POST /api/join {classCode, nickname}` → validates class exists and nickname
(2-20 chars, `[A-Za-z0-9_-]`) → sets an HttpOnly, SameSite=Lax cookie. No signing: the brief has no
accounts, so class code + nickname *is* the identity. No IP stored or logged — which includes
uvicorn's access log (see Q2).

**Store** (`store.py`, stdlib `sqlite3`, file at `get_fce_home(env)/fce.sqlite3`, one connection per
call): `classes(code)`, `students(class_code, nickname)`, `completions(class_code, nickname,
mission_id, graph_json, completed_at)`. Teacher CLI: `python -m fce_web.store create-class` /
`purge <code>` (no `pyproject` script entry, so it does not collide with B-031's edit).

**Progress flow.** `POST /api/run` reads the cookie into the job. When the job finishes, the
objective is evaluated **per job, never from cache** (B-021's cache-hit `meta.mission` defect is the
precedent), attached to `/result` as `objective {missionId, met, value, message, unlocked}`, and a
met objective by a joined student writes a completion. `GET /` renders the mission panel and palette
gating from `missions` + progress (backend supplies the template context; frontend owns the markup).
Unlock rule: mission n+1 opens when n is completed.

## Tasks

| ID | Role | Outcome | Depends on |
|---|---|---|---|
| **B-031** | backend | PyYAML dep; `missions.py` loader + startup validation; `m-1.yaml`, `m-2.yaml` stub; `evaluate()` with one check on the fixture payload | — |
| **B-033** | backend | `store.py` schema + nickname validation + CLI create/purge; `docs/teacher.md` for the purge | — |
| **B-032** | backend | run wiring: `missionId` validated, dataset from mission (delete `_V1_DATASET`), locked kinds/modes → 400, `objective` on `/result` per job | B-031 |
| **B-034** | backend | **CONTRACT**: `/api/join`, cookie, completion recording, `GET /api/progress`, page template context; `docs/api.md` sections | B-032, B-033 |
| **F-020** | frontend | join form (class code + nickname, "not your real name"), shown when not joined | B-034 |
| **F-021** | frontend | mission panel + pager from server data; locked kinds/modes inert with "opens in M-n" | B-034 |
| **F-022** | frontend | objective outcome after a run: margin note on miss, completion + unlock on met; panel updates without reload | F-021 |
| **D-027** | design | style join form, locked items, objective note; a minimal completion mark (the full stamp/logbook is D-011, M6) | F-020, F-022 |

**Waves.** 1: B-031 ∥ B-033 (disjoint files, `isolation: "worktree"`). 2: B-032. 3: B-034. 4: F-020 ∥
F-021 (join is its own template; worktrees). 5: F-022. 6: D-027. Then the **M5 checkpoint**.
Reviewer at raised effort on B-032 (objective = a number students see) and B-034 (contract +
privacy). D-011 stays blocked into M6.

## Open questions — scout before the dispatch that needs them

- **Q1 (B-032).** How `graph.py` rejects with a node id today, and where Observable `mode` is read.
- **Q2 (B-034).** How the server is launched (`__main__`, script, uvicorn args) and whether the access
  log is on — if so, B-034 turns it off; that is the "no IP logging" criterion.
- **Q3 (F-021).** Which `graph.js`/`shell.html` hooks render the palette and Observable modes.

## Verification (the M5 checkpoint)

`python -m fce_web.store create-class` → code; start the server with the fixture `FCE_HOME`; join with
that code and a nickname; M-1 panel shows only M-1's cards; build the default chain, Run → objective
met, M-2 opens; reload and switch browser → progress still there; `purge <code>` → rows gone, join
fails. Full suite ≥ floor 739 plus each task's one check; flake8 0; `verify.py --all` red set still
exactly `{board-lane-fill}`.

## First moves after approval

1. Commit this as `docs/plan-m5-missions.md`; add B-031..B-034, F-020..F-022, D-027 to the task lists.
2. Dispatch B-031 ∥ B-033 with worktree isolation.

## Answers (scout, 2026-09-24)

- **Q1.** `GraphError(ValueError)` carries `node_id` (`graph.py:49,67`); `api.py:54-55` turns it into
  `400 {"error","nodeId"}`. Mode read in `_resolved_kind()` (`graph.py:123`); `_OBS_MODES` at `:92`;
  kinds checked against `PALETTE_KINDS` in `_parse_nodes()` (`:90`, `:132-155`). Gating hooks there.
- **Q1b.** `Job.mission_id` at `jobs.py:90`; `_V1_DATASET` defined `:66`, used once `:171`
  (`submit`). Payload built `:255` via `_build_payload` (`:274-291`). **Cache hit returns early at
  `:182-192`** through `_retag_payload(cached.payload, mission_id)` (`:187`) — so the objective must
  be evaluated on that path too, not only after `_build_payload`.
- **Q2.** Launched only as `uvicorn --factory fce_web.app:create_app` (docstring, `app.py:27`); no
  `__main__`, no `[project.scripts]`, no `access_log` setting. **Uvicorn's default access log prints
  the client IP**, so B-034 must ship a launcher (`python -m fce_web`) with `access_log=False` and
  document it. Nothing in `src/` logs `request.client`.
