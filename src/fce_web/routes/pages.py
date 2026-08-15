"""Routes that render whole HTML pages from Jinja2 templates.

These endpoints return documents, not JSON: HTMX and the browser navigate to
them directly. JSON and HTML-fragment endpoints belong in sibling modules.

Templates are front-end owned (`.claude/shared/CLAUDE.md` §4) and are rendered
by name only -- this module never inspects or edits them. ``index.html`` reads
exactly one variable, ``title``; adding more context would silently do nothing
and would drift from what the template promises.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

#: Provisional placeholder heading for the landing page. User-facing copy is a
#: later task with the design brief behind it, so this stays plainly
#: descriptive rather than inventing a tagline or a mission name.
INDEX_TITLE = "FCE-site"


def build_router() -> APIRouter:
    """Return a fresh router serving the site's HTML pages.

    A factory, not a module-level router, so nothing mutable exists at import
    time and each application built by ``create_app()`` owns its own routes.
    """
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        """Render the landing page.

        The ``Jinja2Templates`` instance is read off ``app.state`` rather than
        held in a module global: it is per-application, created in the factory.
        """
        templates: Jinja2Templates = request.app.state.templates
        return templates.TemplateResponse(request, "index.html", {"title": INDEX_TITLE})

    return router
