"""JSON endpoints joining a student's graph to the physics engine (task B-021).

Documented in ``docs/api.md``: ``POST /api/run`` submits a graph and returns
a run id immediately, before the run finishes (it executes on a background
thread via ``fce_web.jobs.JobRegistry``); ``GET /api/run/{id}/result`` reads
that run's outcome back. ``GET /api/run/{id}/events`` (SSE progress) is
B-022's -- this router does not define it.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fce_web.graph import GraphError
from fce_web.jobs import JobRegistry


class RunRequest(BaseModel):
    """``POST /api/run``'s body -- see ``docs/api.md``. ``graph`` is handed
    to ``fce_web.graph.build_run_config`` unvalidated beyond "is an object";
    that function is the actual boundary validation (C2)."""

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
        thread and returns the job's id immediately (C1). An invalid graph
        never starts a run at all (C2).
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
        status for one in flight, or 404 for an unknown id (C5)."""
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

    return router
