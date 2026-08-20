"""Tests for ``fce_web.paths``.

Ported from the reference repo's ``tests/test_paths.py`` (kskovpen/fce), with
two deliberate deviations (task B-005, decided not open questions):

1. The reference caches its answer in a module-level ``_fce_home`` global,
   which forces its own tests to reach in and reset ``paths._fce_home = None``
   between cases. ``.claude/shared/CLAUDE.md`` §6 forbids module-level mutable
   state outright, so ``get_fce_home`` here takes an optional ``env`` mapping
   and is pure -- nothing to reset. ``test_get_fce_home_is_not_memoised_across_calls``
   is the test the reference could not write: two calls in the same process
   with two different environments get two different, correct answers.

2. ``configure_cache_env()`` is not ported (it exists only to route around a
   desktop Mesa/GL shader-cache warning; this project has no GL and no
   desktop), so ``test_configure_cache_env_sets_writable_path`` is dropped
   with it.
"""
import os

from fce_web.paths import get_fce_home


def test_get_fce_home_returns_writable_dir(tmp_path):
    result = get_fce_home(env={"FCE_HOME": str(tmp_path)})
    assert os.path.isdir(result)
    probe = result / "probe.txt"
    probe.write_text("ok")
    probe.unlink()


def test_get_fce_home_returns_a_path_object(tmp_path):
    result = get_fce_home(env={"FCE_HOME": str(tmp_path)})
    assert isinstance(result, type(tmp_path))


def test_get_fce_home_same_env_returns_same_path(tmp_path):
    """Adapted from the reference's ``test_get_fce_home_cached``.

    The reference asserted this by relying on its module-level cache; here
    it falls out of the function being pure -- same input, same output, no
    global involved.
    """
    first = get_fce_home(env={"FCE_HOME": str(tmp_path)})
    second = get_fce_home(env={"FCE_HOME": str(tmp_path)})
    assert first == second


def test_get_fce_home_is_not_memoised_across_calls(tmp_path):
    """The point of deviation 1: no module global to leak between calls.

    Two calls in the same process, each with its own FCE_HOME, must return
    two different paths -- something the reference's cached-global
    implementation cannot do without manual resets between calls.
    """
    first_home = tmp_path / "first"
    second_home = tmp_path / "second"

    first = get_fce_home(env={"FCE_HOME": str(first_home)})
    second = get_fce_home(env={"FCE_HOME": str(second_home)})

    assert first != second
    assert first == first_home
    assert second == second_home
