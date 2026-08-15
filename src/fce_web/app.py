"""The FastAPI application factory.

``create_app()`` builds and returns a fully wired application. Everything
mutable -- the app, its templates, its routers, its static mount -- is created
inside the call, so importing this module has no side effects and two
applications in one process never share state
(``.claude/shared/CLAUDE.md`` §6).

Paths are resolved from this file's location, not from the current working
directory, so the server behaves identically whether it is started from the
repo root or from a teacher's home directory.

Resolving off the package is not by itself enough to make an *installed*
copy work: ``pyproject.toml`` currently ships no ``package-data``, so a wheel
carries the Python modules and neither ``templates/`` nor ``static/``, and
the static mount below raises on a non-editable install. Running from a
source checkout, editable or not, is unaffected. Fixing that is a packaging
task of its own -- it is recorded in ``.claude/tasks/backlog.md`` -- so do
not read this module as a claim that ``pip install fce-web`` yields a
runnable server yet.

Nothing here reaches the network, and nothing it serves asks a browser to.
That is a requirement, not a coincidence: see ``docs_url`` below.

Run it with::

    uvicorn --factory fce_web.app:create_app
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fce_web import __version__
from fce_web.routes import pages

#: Directory of the installed package; the anchor for every asset path below.
PACKAGE_DIR = Path(__file__).resolve().parent

#: Jinja2 templates. Front-end owned -- rendered by name, never edited here.
TEMPLATES_DIR = PACKAGE_DIR / "templates"

#: Served assets. Mounted at ``/static`` because ``templates/base.html``
#: references ``/static/js/app.js`` as a literal path rather than via
#: ``url_for``; any other prefix makes every page 404 its own script.
STATIC_DIR = PACKAGE_DIR / "static"

#: URL prefix of the static mount. Must match the literal paths in the
#: templates.
STATIC_URL_PATH = "/static"

#: Route name of the static mount, so ``url_path_for("static", ...)`` resolves.
STATIC_MOUNT_NAME = "static"

#: Path of the generated OpenAPI schema. Kept on -- unlike the pages that
#: render it, the schema is produced by this process and references nothing
#: outside it, and it is how the endpoint contract in ``docs/api.md`` gets
#: checked against the routes that actually exist.
OPENAPI_URL = "/openapi.json"


def create_app() -> FastAPI:
    """Build and return the FCE-site application.

    Every call yields an independent application: a new router, a new template
    environment, and a new static-files app. Nothing is cached at module level.
    """
    app = FastAPI(
        title="FCE-site",
        description=(
            "Browser-based learning game teaching particle-physics data "
            "analysis on simulated FCC-ee data"
        ),
        version=__version__,
        openapi_url=OPENAPI_URL,
        # FastAPI's interactive docs are off, not styled or vendored. The HTML
        # it generates for /docs pulls Swagger UI from cdn.jsdelivr.net, /redoc
        # pulls ReDoc from the same CDN plus Montserrat and Roboto from Google
        # Fonts, and both fetch a favicon from fastapi.tiangolo.com. A CDN
        # link, a remote script and an external font: the three things
        # `.claude/shared/CLAUDE.md` §3 forbids outright, in an app whose whole
        # point is to run in a classroom with no internet, where those requests
        # would hang rather than fail fast.
        docs_url=None,
        redoc_url=None,
    )

    # Per-application, so nothing is shared between instances. Routes reach it
    # through ``request.app.state`` instead of importing a global.
    app.state.templates = Jinja2Templates(directory=TEMPLATES_DIR)

    app.mount(
        STATIC_URL_PATH,
        StaticFiles(directory=STATIC_DIR),
        name=STATIC_MOUNT_NAME,
    )
    app.include_router(pages.build_router())

    return app
