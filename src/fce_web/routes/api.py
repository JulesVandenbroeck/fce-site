"""JSON endpoints joining a student's graph to the physics engine (task B-021).

Documented in ``docs/api.md``: ``POST /api/run`` submits a graph and returns
a run id immediately, before the run finishes (it executes on a background
thread via ``fce_web.jobs.JobRegistry``); ``GET /api/run/{id}/result`` reads
that run's outcome back; ``GET /api/run/{id}/events`` (task B-022) streams
that same run's progress as Server-Sent Events, draining ``Job.events`` --
see ``docs/api.md``'s "Run progress event" section for the wire format.
"""
from __future__ import annotations

import asyncio
import json
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Any, AsyncIterator, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from fce_web.graph import GraphError
from fce_web.jobs import Job, JobRegistry


class RunRequest(BaseModel):
    """``POST /api/run``'s body -- see ``docs/api.md``. ``graph`` is handed
    to ``fce_web.graph.build_run_config`` unvalidated beyond "is an object";
    that function is the actual boundary validation."""

    missionId: str
    graph: Dict[str, Any]


def build_router() -> APIRouter:
    """Return a fresh router serving the JSON run endpoints.

    A factory, not a module-level router, so nothing mutable exists at
    import time and each application built by ``create_app()`` owns its own
    routes (matching ``fce_web.routes.pages.build_router``).
    """
    router = APIRouter(prefix="/api")

    @router.post("/run")
    async def submit_run(request: Request, body: RunRequest) -> Dict[str, Any]:
        """Validate and submit *body*'s graph. Returns before the run
        completes -- ``JobRegistry.submit`` starts it on a background
        thread and returns the job's id immediately. An invalid graph
        never starts a run at all.
        """
        registry: JobRegistry = request.app.state.jobs
        try:
            job = registry.submit(body.graph, body.missionId)
        except GraphError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
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
            body = {"status": "done", "cacheHit": cache_hit}
            body.update(payload)
            return body
        # "error" or "cancelled" -- a legitimate run outcome, not a bad request.
        return {"status": status, "error": error}

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
