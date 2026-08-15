"""Tests for the ``fce_web`` package skeleton and its packaging metadata.

These guard the properties every later back-end task depends on: the package
imports, reports a version that matches the installed distribution, sits in a
src-layout, and declares exactly the fixed stack from
``.claude/shared/CLAUDE.md`` §3 -- with the desktop UI toolkit (``dearpygui``)
absent, since the reference repo's UI is deliberately not vendored.

The dependency assertions read the *installed* metadata rather than parsing
``pyproject.toml``, so they fail if the declaration and the installed
distribution ever drift apart.
"""

import re
from importlib import metadata
from pathlib import Path

import fce_web

DIST_NAME = "fce-web"

#: Runtime stack fixed by ``.claude/shared/CLAUDE.md`` §3.
RUNTIME_STACK = frozenset({
    "fastapi",
    "uvicorn",
    "jinja2",
    "uproot",
    "boost-histogram",
    "vector",
    "pyhf",
    "numpy",
    "scipy",
    "matplotlib",
    "mplhep",
})

#: Tooling that must stay out of the runtime install.
DEV_TOOLS = frozenset({"pytest", "flake8", "playwright"})

REPO_ROOT = Path(__file__).resolve().parents[1]


def _requirement_name(requirement: str) -> str:
    """Return the normalised distribution name from a ``Requires-Dist`` string."""
    name = re.split(r"[\s\[<>=!~;(]", requirement, maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


def _declared_requirements() -> list[str]:
    """Return every ``Requires-Dist`` entry of the installed distribution."""
    return list(metadata.requires(DIST_NAME) or [])


def _runtime_requirement_names() -> set[str]:
    """Return names of requirements installed unconditionally (no extra marker)."""
    return {
        _requirement_name(req)
        for req in _declared_requirements()
        if "extra ==" not in req
    }


def _extra_requirement_names(extra: str) -> set[str]:
    """Return names of requirements gated behind ``extra``."""
    return {
        _requirement_name(req)
        for req in _declared_requirements()
        if f'extra == "{extra}"' in req or f"extra == '{extra}'" in req
    }


def test_package_exposes_a_dotted_version() -> None:
    """``fce_web.__version__`` is a three-part numeric version string."""
    assert isinstance(fce_web.__version__, str)
    assert re.fullmatch(r"\d+\.\d+\.\d+", fce_web.__version__), fce_web.__version__


def test_installed_version_matches_dunder_version() -> None:
    """The distribution version and ``__version__`` never drift apart."""
    assert metadata.version(DIST_NAME) == fce_web.__version__


def test_package_uses_src_layout() -> None:
    """The importable package lives at ``src/fce_web/``, not at the repo root."""
    package_dir = Path(fce_web.__file__).resolve().parent
    assert package_dir.name == "fce_web"
    assert package_dir.parent.name == "src"


def test_distribution_requires_python_3_10_or_newer() -> None:
    """Python >= 3.10 is a hard constraint from the developer's environment."""
    assert metadata.metadata(DIST_NAME)["Requires-Python"] == ">=3.10"


def test_runtime_requirements_cover_the_fixed_stack() -> None:
    """Every layer of the fixed stack is installed by a plain ``pip install``."""
    missing = RUNTIME_STACK - _runtime_requirement_names()
    assert not missing, f"missing runtime dependencies: {sorted(missing)}"


def test_dev_tools_are_optional_not_runtime() -> None:
    """Test and lint tooling ships in the ``dev`` extra, not the runtime set."""
    assert DEV_TOOLS.isdisjoint(_runtime_requirement_names())
    missing = DEV_TOOLS - _extra_requirement_names("dev")
    assert not missing, f"missing dev dependencies: {sorted(missing)}"


def test_dearpygui_is_never_a_dependency() -> None:
    """The desktop UI toolkit is not vendored, so it must not be depended on."""
    offenders = [req for req in _declared_requirements() if "dearpygui" in req.lower()]
    assert not offenders, f"dearpygui declared in: {offenders}"


def test_dearpygui_appears_nowhere_in_pyproject() -> None:
    """Guard the declaration itself, not just the built metadata."""
    pyproject = REPO_ROOT / "pyproject.toml"
    assert pyproject.is_file(), f"missing {pyproject}"
    assert "dearpygui" not in pyproject.read_text(encoding="utf-8").lower()
