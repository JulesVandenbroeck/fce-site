"""Asserts that ``fce_web.engine`` never pulls in the desktop UI toolkit.

``.claude/backend/CLAUDE.md`` §3.1 states this outright: "``import fce_web.engine``
must pull in zero UI or ``dearpygui`` dependencies. A test should assert this."
``tests/test_skeleton.py`` checks *declared* requirements and ``pyproject.toml``
*text*; neither walks the actual import graph, so neither would catch a
genuinely lazy or indirect import of the desktop front end. This module
checks the import graph itself, via ``sys.modules`` after the import -- what
B-005's PR review did by hand, made permanent so B-007 onward (which import a
great deal more of the reference engine) inherit the guard rather than a
grep that decays.

Added in B-005 cycle 2 (suggested-major 2); file scope for this task was
extended to include this file.
"""
import re
import sys

import fce_web.engine  # noqa: F401  (imported for its effect on sys.modules)

#: Matches the module itself or any of its submodules -- 'ui' and 'ui.state'
#: both match; 'uproot' and 'requests.utils' do not, since the match is
#: anchored at the start and requires a following '.' or end of string, not a
#: bare substring search.
_FORBIDDEN = re.compile(r"^(dearpygui|ui)(\.|$)")


def _offending_modules(module_names):
    """Return the subset of module_names naming the desktop front end."""
    return sorted(name for name in module_names if _FORBIDDEN.match(name))


def test_importing_engine_pulls_in_no_dearpygui_or_ui_modules():
    """The real guard: nothing matching the desktop front end is loaded."""
    offenders = _offending_modules(sys.modules)
    assert not offenders, f"fce_web.engine pulled in front-end modules: {offenders}"


def test_offending_module_detection_flags_the_desktop_ui_toolkit():
    """Mutation check on the detector itself.

    A guard that can never fail is worse than none. This exercises
    ``_offending_modules`` directly against known-bad and known-safe names,
    independent of whatever happens to be in ``sys.modules`` when the suite
    runs, so a future accidental UI import is guaranteed to be caught rather
    than silently passing because nothing was ever imported to catch.
    """
    bad = {"dearpygui", "dearpygui.core", "ui", "ui.state", "ui.state.run"}
    safe = {"uproot", "uuid", "requests.utils", "fce_web.engine", "numpy", "buildui"}

    assert _offending_modules(bad | safe) == sorted(bad)
