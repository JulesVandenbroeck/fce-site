"""Resolves the writable FCE home directory (cache/output/datasets).

Vendored from the reference repo's ``paths.py`` (kskovpen/fce), with one
deliberate deviation (task B-005): the reference memoises its answer in a
module-level ``_fce_home`` global, which ``.claude/shared/CLAUDE.md`` §6
forbids ("No module-level mutable state. Ever."). Two concurrent students in
this webapp must not be able to see, or interfere with, each other's
resolved path through shared process state, so ``get_fce_home`` here is a
pure function: it takes an optional environment mapping and returns a fresh
answer on every call, with nothing cached between them.

``~/.fce`` is not always writable (read-only or quota-limited home
directories are common on shared clusters and containers), so this falls
back to a temp directory rather than crashing the app.

``configure_cache_env()`` from the reference is deliberately not vendored --
it exists solely to route around a desktop Mesa/GL shader-cache warning on
Dear PyGui launch, and this project has neither GL nor a desktop UI.
"""
import getpass
import os
import tempfile
from pathlib import Path
from typing import Mapping, Optional


def get_fce_home(env: Optional[Mapping[str, str]] = None) -> Path:
    """Return a writable FCE home directory.

    Resolution order, first candidate whose write-probe succeeds wins:
    ``$FCE_HOME``, then ``~/.fce``, then ``{tempdir}/fce-{user}``.

    Parameters
    ----------
    env : Mapping[str, str], optional
        Environment to read ``FCE_HOME`` from. Defaults to ``os.environ``.
        Passing an explicit mapping (rather than mutating process
        environment) is what lets callers, including tests, get an
        independent answer without touching global state.

    Raises
    ------
    OSError
        If no candidate directory is writable.
    """
    if env is None:
        env = os.environ

    candidates = []
    if env.get("FCE_HOME"):
        candidates.append(Path(env["FCE_HOME"]))
    candidates.append(Path(os.path.expanduser("~")) / ".fce")
    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    candidates.append(Path(tempfile.gettempdir()) / f"fce-{user}")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("")
            probe.unlink()
        except OSError:
            continue
        return candidate

    # Should be unreachable -- tempfile.gettempdir() is always writable in practice.
    raise OSError("No writable location found for FCE home directory.")
