"""End-to-end tests for the FastAPI application factory and the index page.

Everything here runs the real application in-process through Starlette's
``TestClient``: no live server is started and no network is touched, so the
suite works on the offline classroom machines the app itself targets.

Three properties are load-bearing beyond "the page renders":

* ``create_app()`` is a *factory*. Nothing mutable exists at import time
  (``.claude/shared/CLAUDE.md`` §6) -- module-level mutable state is the defect
  inherited from the reference repo that this project exists to avoid, so it
  must not creep back in through a shared app, router, or template object.
* The template and static directories are resolved relative to the *package*,
  not the current working directory, so ``uvicorn fce_web.app:...`` works from
  anywhere.
* The static mount lives at ``/static``. ``templates/base.html`` hard-codes
  ``/static/js/app.js`` rather than using ``url_for``, so a mount anywhere else
  makes every page 404 its own script.
"""

import re
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient
from starlette.routing import Mount

import fce_web.app
import fce_web.routes.pages
from fce_web.app import create_app
from fce_web.routes.pages import INDEX_TITLE

PACKAGE_DIR = Path(fce_web.__file__).resolve().parent

#: Media types browsers and servers use for ES modules; either is acceptable,
#: the mapping depends on the host's mime database.
JAVASCRIPT_MEDIA_TYPES = frozenset({"text/javascript", "application/javascript"})

#: Types whose contents can be mutated in place after import.
MUTABLE_CONTAINERS = (list, dict, set, bytearray)

#: Per-app objects that must be built inside the factory, never at import time.
PER_APP_TYPES = (FastAPI, APIRouter, Jinja2Templates, StaticFiles)


@pytest.fixture(name="client")
def _client() -> Iterator[TestClient]:
    """Yield a ``TestClient`` driving a freshly built application."""
    with TestClient(create_app()) as client:
        yield client


def _module_level_state(module: ModuleType) -> dict[str, str]:
    """Return public module attributes that are mutable or per-app, by name."""
    return {
        name: type(value).__name__
        for name, value in vars(module).items()
        if not name.startswith("__")
        and isinstance(value, MUTABLE_CONTAINERS + PER_APP_TYPES)
    }


def _static_mount(app: FastAPI) -> Mount:
    """Return the single ``Mount`` route named ``static``."""
    mounts = [
        route for route in app.routes
        if isinstance(route, Mount) and route.name == "static"
    ]
    assert len(mounts) == 1, f"expected exactly one static mount, got {mounts}"
    return mounts[0]


def test_create_app_returns_a_fastapi_instance() -> None:
    """The factory hands back a configured application, not a coroutine or None."""
    assert isinstance(create_app(), FastAPI)


def test_create_app_builds_a_new_application_each_call() -> None:
    """Two calls share no application object, so no request state can leak."""
    first, second = create_app(), create_app()
    assert first is not second


def test_no_module_level_mutable_state_in_the_app_module() -> None:
    """``fce_web.app`` holds no mutable or per-app object at import time."""
    assert _module_level_state(fce_web.app) == {}


def test_no_module_level_mutable_state_in_the_pages_module() -> None:
    """``fce_web.routes.pages`` holds no shared router at import time."""
    assert _module_level_state(fce_web.routes.pages) == {}


def test_index_responds_ok_as_html(client: TestClient) -> None:
    """``GET /`` renders a page rather than JSON or a redirect."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_index_renders_the_page_heading(client: TestClient) -> None:
    """The rendered body carries the ``<h1>`` fed by the ``title`` variable."""
    body = client.get("/").text
    assert re.search(rf"<h1[^>]*>\s*{re.escape(INDEX_TITLE)}\s*</h1>", body), body


def test_index_renders_the_document_title(client: TestClient) -> None:
    """``base.html`` reads the same ``title`` for the browser tab."""
    body = client.get("/").text
    assert f"<title>{INDEX_TITLE}</title>" in body


def test_index_references_the_static_entry_script(client: TestClient) -> None:
    """The page points at the literal script path ``base.html`` hard-codes."""
    assert "/static/js/app.js" in client.get("/").text


def test_static_files_are_mounted_at_slash_static() -> None:
    """The mount is named ``static`` and reachable under the expected prefix."""
    app = create_app()
    assert _static_mount(app).path == "/static"
    assert app.url_path_for("static", path="js/app.js") == "/static/js/app.js"


def test_static_mount_serves_the_package_static_directory() -> None:
    """Static files come from ``src/fce_web/static/``, resolved off the package."""
    served = Path(_static_mount(create_app()).app.directory).resolve()
    assert served == PACKAGE_DIR / "static"


def test_static_entry_script_is_served_as_javascript(client: TestClient) -> None:
    """``GET /static/js/app.js`` returns the module the page shell loads."""
    response = client.get("/static/js/app.js")
    assert response.status_code == 200
    media_type = response.headers["content-type"].split(";")[0].strip()
    assert media_type in JAVASCRIPT_MEDIA_TYPES, response.headers["content-type"]


def test_app_works_from_an_unrelated_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Templates and static files resolve off the package, not off ``cwd``."""
    monkeypatch.chdir(tmp_path)
    with TestClient(create_app()) as client:
        assert client.get("/").status_code == 200
        assert client.get("/static/js/app.js").status_code == 200


def test_index_title_is_a_plain_string() -> None:
    """The provisional placeholder title is a non-empty ``str``."""
    assert isinstance(INDEX_TITLE, str)
    assert INDEX_TITLE.strip()
