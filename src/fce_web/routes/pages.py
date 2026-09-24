"""Routes that render whole HTML pages from Jinja2 templates.

These endpoints return documents, not JSON: HTMX and the browser navigate to
them directly. JSON and HTML-fragment endpoints belong in sibling modules.

Templates are front-end owned (`.claude/shared/CLAUDE.md` §4) and are rendered
by name only -- this module never inspects or edits them. ``index.html`` reads
``title`` plus, as of B-034, ``student``, ``missions`` and ``current_mission``
(see ``docs/api.md``'s "Page context" section for their exact shapes) -- the
mission panel and palette gating F-020/F-021 build read from this context, not
from a separate fetch.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fce_web.routes.api import _COOKIE_NAME, _mission_progress, _read_cookie

#: Provisional placeholder heading for the landing page. User-facing copy is a
#: later task with the design brief behind it, so this stays plainly
#: descriptive rather than inventing a tagline or a mission name.
INDEX_TITLE = "FCE-site"


def _current_mission(missions_by_id, mission_entries) -> Optional[Dict[str, Any]]:
    """The mission the page should show: the first ``"open"`` one, else the
    last ``"done"`` one, else the first mission (nothing unlocked yet is
    unreachable in practice -- the first mission is always at least
    ``"open"`` -- but this stays total rather than assuming it)."""
    ordered = sorted(missions_by_id.values(), key=lambda m: m.order)
    by_state = {entry["id"]: entry["state"] for entry in mission_entries}
    for mission in ordered:
        if by_state.get(mission.id) == "open":
            return mission
    done = [m for m in ordered if by_state.get(m.id) == "done"]
    return done[-1] if done else (ordered[0] if ordered else None)


def _mission_context(mission) -> Optional[Dict[str, Any]]:
    if mission is None:
        return None
    return {
        "id": mission.id,
        "title": mission.title,
        "brief": mission.brief,
        "hints": mission.hints,
        "cards": mission.cards,
        "observableModes": mission.observable_modes,
    }


def build_router() -> APIRouter:
    """Return a fresh router serving the site's HTML pages.

    A factory, not a module-level router, so nothing mutable exists at import
    time and each application built by ``create_app()`` owns its own routes.
    """
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        """Render the landing page with the mission panel's data (B-034/C5).

        The ``Jinja2Templates`` instance is read off ``app.state`` rather than
        held in a module global: it is per-application, created in the factory.
        """
        templates: Jinja2Templates = request.app.state.templates
        env = request.app.state.jobs.env
        student, stale = _read_cookie(request, env)
        missions_by_id = request.app.state.missions
        entries = _mission_progress(missions_by_id, student, env)
        context = {
            "title": INDEX_TITLE,
            "student": {"classCode": student[0], "nickname": student[1]} if student else None,
            "missions": entries,
            "current_mission": _mission_context(_current_mission(missions_by_id, entries)),
        }
        rendered = templates.TemplateResponse(request, "index.html", context)
        if stale:
            rendered.delete_cookie(_COOKIE_NAME)
        return rendered

    return router
