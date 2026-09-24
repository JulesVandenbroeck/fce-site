"""JSON endpoints joining a student's graph to the physics engine (task B-021).

Documented in ``docs/api.md``: ``POST /api/run`` submits a graph and returns
a run id immediately, before the run finishes (it executes on a background
thread via ``fce_web.jobs.JobRegistry``); ``GET /api/run/{id}/result`` reads
that run's outcome back; ``GET /api/run/{id}/events`` (task B-022) streams
that same run's progress as Server-Sent Events, draining ``Job.events`` --
see ``docs/api.md``'s "Run progress event" section for the wire format.

**Identity and progress (task B-034).** ``POST /api/join`` and
``GET /api/progress`` are the join/progress half of the contract; the cookie
they set (``_COOKIE_NAME``) is what ``POST /api/run`` and ``GET /`` (see
``fce_web.routes.pages``, which imports ``_resolve_student``/``_progress_body``
from here rather than duplicating them) read back. Nothing here stores or
logs anything beyond class code, nickname, mission id, graph and timestamp
(``fce_web.store``) -- see ``.claude/backend/CLAUDE.md`` §5.
"""
from __future__ import annotations

import asyncio
import json
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncIterator, Dict, List, Mapping, Optional, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from fce_web import store
from fce_web.graph import Dataset, GraphError
from fce_web.jobs import Job, JobRegistry
from fce_web.missions import Mission, evaluate

#: Name of the HttpOnly cookie identifying a joined student. Its value is
#: ``"{classCode}:{nickname}"`` -- safe as a plain split, since neither a
#: class code (``store._CODE_ALPHABET``) nor a nickname
#: (``store._NICKNAME_RE``) can contain a colon.
_COOKIE_NAME = "fce_student"


class JoinRequest(BaseModel):
    """``POST /api/join``'s body -- see ``docs/api.md``."""

    classCode: str
    nickname: str


class RunRequest(BaseModel):
    """``POST /api/run``'s body -- see ``docs/api.md``. ``graph`` is handed
    to ``fce_web.graph.build_run_config`` unvalidated beyond "is an object";
    that function is the actual boundary validation."""

    missionId: str
    graph: Dict[str, Any]


def _read_cookie(
    request: Request, env: Optional[Mapping[str, str]]
) -> Tuple[Optional[Tuple[str, str]], bool]:
    """``(student, stale)`` -- *student* is ``(classCode, nickname)`` from the
    requester's cookie, or ``None`` if there is none, is malformed, or does not
    name a joined ``(classCode, nickname)`` pair (*stale* is ``True`` only in
    that last case -- a purged class or a nickname that never joined, e.g. a
    forged cookie -- so a caller holding its own response object -- e.g. a
    rendered template -- knows to clear the cookie, B-034/C1, C10)."""
    raw = request.cookies.get(_COOKIE_NAME)
    if not raw or ":" not in raw:
        return None, False
    code, nickname = raw.split(":", 1)
    if not store.student_exists(code, nickname, env=env):
        return None, True
    return (code, nickname), False


def _resolve_student(
    request: Request, response: Response, env: Optional[Mapping[str, str]]
) -> Optional[Tuple[str, str]]:
    """``_read_cookie``, clearing a stale cookie on *response* itself."""
    student, stale = _read_cookie(request, env)
    if stale:
        response.delete_cookie(_COOKIE_NAME)
    return student


def _mission_progress(
    missions_by_id: Dict[str, Mission], student: Optional[Tuple[str, str]], env: Optional[Mapping[str, str]]
) -> List[Dict[str, Any]]:
    """Every mission ordered by ``order``, each tagged with its unlock
    state: the first mission is always ``"open"`` (or ``"done"``); mission
    n+1 is ``"open"`` iff mission n is ``"done"`` (B-034/C3)."""
    done_ids = set(store.completed_missions(*student, env=env)) if student else set()
    missions = sorted(missions_by_id.values(), key=lambda m: m.order)
    entries = []
    previous_done = True
    for mission in missions:
        if mission.id in done_ids:
            state = "done"
        elif previous_done:
            state = "open"
        else:
            state = "locked"
        entries.append({"id": mission.id, "order": mission.order, "title": mission.title, "state": state})
        previous_done = state == "done"
    return entries


def _progress_body(
    missions_by_id: Dict[str, Mission], student: Optional[Tuple[str, str]], env: Optional[Mapping[str, str]]
) -> Dict[str, Any]:
    """``GET /api/progress``'s response shape (B-034/C3), also returned by
    ``POST /api/join`` on success."""
    student_body = {"classCode": student[0], "nickname": student[1]} if student else None
    return {"student": student_body, "missions": _mission_progress(missions_by_id, student, env)}


def build_router() -> APIRouter:
    """Return a fresh router serving the JSON run endpoints.

    A factory, not a module-level router, so nothing mutable exists at
    import time and each application built by ``create_app()`` owns its own
    routes (matching ``fce_web.routes.pages.build_router``).
    """
    router = APIRouter(prefix="/api")

    @router.post("/join")
    async def join(request: Request, body: JoinRequest, response: Response) -> Dict[str, Any]:
        """Join a class under a nickname and set the identifying cookie
        (B-034/C1). ``400`` with a student-legible ``error`` for an unknown
        class or an invalid nickname; nothing is set or stored either way.
        """
        env = request.app.state.jobs.env
        try:
            store.join(body.classCode, body.nickname, env=env)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        response.set_cookie(_COOKIE_NAME, f"{body.classCode}:{body.nickname}", httponly=True, samesite="lax")
        return _progress_body(request.app.state.missions, (body.classCode, body.nickname), env)

    @router.get("/progress")
    async def get_progress(request: Request, response: Response) -> Dict[str, Any]:
        """The joined student (or ``null``) and every mission's unlock
        state (B-034/C3)."""
        env = request.app.state.jobs.env
        student = _resolve_student(request, response, env)
        return _progress_body(request.app.state.missions, student, env)

    @router.post("/run")
    async def submit_run(request: Request, body: RunRequest) -> Dict[str, Any]:
        """Validate and submit *body*'s graph. Returns before the run
        completes -- ``JobRegistry.submit`` starts it on a background
        thread and returns the job's id immediately. An invalid graph
        never starts a run at all.

        Does not clear a stale cookie itself (B-034 cycle 2, F2) -- a
        gating 400 here never carries a ``Set-Cookie``. ``GET /api/progress``
        and ``GET /`` are the endpoints documented to clear one
        (``docs/api.md``).
        """
        mission = request.app.state.missions.get(body.missionId)
        if mission is None:
            return JSONResponse(
                {"error": f"unknown mission: {body.missionId!r}", "nodeId": None}, status_code=400
            )
        env = request.app.state.jobs.env
        student, _stale = _read_cookie(request, env)
        state = next(m["state"] for m in _mission_progress(request.app.state.missions, student, env)
                     if m["id"] == mission.id)
        if state == "locked":
            return JSONResponse(
                {"error": f"{mission.title!r} isn't open yet -- finish the mission before it first.",
                 "nodeId": None},
                status_code=400,
            )
        registry: JobRegistry = request.app.state.jobs
        try:
            job = registry.submit(
                body.graph,
                mission.id,
                dataset=Dataset(**mission.dataset),
                allowed_cards=mission.cards,
                allowed_observable_modes=mission.observable_modes,
                student=student,
            )
        except GraphError as exc:
            return JSONResponse({"error": str(exc), "nodeId": exc.node_id}, status_code=400)
        return {"runId": job.id, "cacheHit": job.cache_hit}

    @router.get("/run/{run_id}/result")
    async def get_result(request: Request, run_id: str) -> Dict[str, Any]:
        """The histogram payload for a finished run, a "still running"
        status for one in flight, or 404 for an unknown id."""
        registry: JobRegistry = request.app.state.jobs
        job = registry.get(run_id)
        if job is None:
            return JSONResponse({"error": f"no such run: {run_id!r}"}, status_code=404)

        with job.lock:
            status, cache_hit, payload, error = job.status, job.cache_hit, job.payload, job.error

        if status == "running":
            return JSONResponse({"status": "running"}, status_code=202)
        if status == "done":
            # Evaluated per job, from this job's own mission id and payload
            # (both already correct on a cache hit -- `JobRegistry._retag_payload`)
            # -- never copied from whichever job originally computed the
            # cached result (B-032/C4). `job.mission_id` was validated against
            # `app.state.missions` at submit time, so the index is never missing.
            missions = request.app.state.missions
            mission = missions[job.mission_id]
            objective = {"missionId": job.mission_id, **evaluate(mission, payload), "unlocked": None}
            if objective["met"] and job.student:
                env = request.app.state.jobs.env
                store.record_completion(*job.student, job.mission_id, job.graph_json, env=env)
                # Same ordering `_mission_progress` uses (sorted by `.order`,
                # next-in-list) rather than a bare `order + 1` -- the two must
                # never be able to disagree on which mission unlocks next
                # (B-034 cycle 2, F5).
                ordered = sorted(missions.values(), key=lambda m: m.order)
                idx = ordered.index(mission)
                objective["unlocked"] = ordered[idx + 1].id if idx + 1 < len(ordered) else None
            body = {"status": "done", "cacheHit": cache_hit}
            body.update(payload)
            body["objective"] = objective
            return body
        # "error" or "cancelled" -- a legitimate run outcome, not a bad request.
        return {"status": status, "error": error, "objective": None}

    @router.get("/run/{run_id}/events")
    async def stream_events(request: Request, run_id: str) -> Response:
        """SSE progress for *run_id* -- ``text/event-stream``, terminated by
        a single ``done`` event. Never carries histogram data; that is
        ``GET /api/run/{id}/result``'s job. 404 (not an open stream) for an
        unknown id, checked before the response starts."""
        registry: JobRegistry = request.app.state.jobs
        job = registry.get(run_id)
        if job is None:
            return JSONResponse({"error": f"no such run: {run_id!r}"}, status_code=404)
        return StreamingResponse(_drain(request, job, registry), media_type="text/event-stream")

    return router


async def _drain(request: Request, job: Job, registry: JobRegistry) -> AsyncIterator[str]:
    """Yield ``job.events`` as SSE frames until the terminal sentinel.

    ``job.events`` is a single, destructive queue shared by every stream on
    this job, so a second client -- or the same one reconnecting after the
    sentinel was already read -- would otherwise block forever on a queue
    nothing will ever fill again; checking ``job.status`` under ``job.lock``
    before touching the queue gets it one synthesised ``done`` frame
    instead. Each blocking read runs off the event loop in a one-worker
    ``ThreadPoolExecutor`` scoped to this single stream (joined on exit, so
    a disconnecting client leaves no thread behind) rather than
    ``asyncio.to_thread``'s shared, process-wide default executor. A frame's
    ``runId`` is sourced from ``registry.owner_of(job.events)`` -- who
    actually created that queue -- not from ``job.id``, so a bug that ever
    points two jobs at the same queue still tags the wrong id instead of
    quietly reporting the reading stream's own.
    """
    with job.lock:
        status = job.status
    if status != "running":
        yield f"data: {json.dumps({'type': 'done', 'status': status, 'runId': job.id})}\n\n"
        return

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        while True:
            if await request.is_disconnected():
                return
            try:
                item = await loop.run_in_executor(pool, job.events.get, True, 0.5)
            except queue.Empty:
                continue
            item = {**item, "runId": registry.owner_of(job.events) or job.id}
            yield f"data: {json.dumps(item)}\n\n"
            if item["type"] == "done":
                return
