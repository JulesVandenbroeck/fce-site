"""``RunContext``: per-run state passed explicitly through the physics engine.

Task B-009 replaces the reference repo's (kskovpen/fce) global run-state dict
-- its ``ui`` package's ``state`` module, ``RUN_STATE``, a single
module-level dict guarded by one ``threading.RLock``, read and written from
``engine/analytical_loop.py`` in ~25 places -- with an object
created fresh for every analysis run and threaded down the call chain as a
parameter. That module-level dict is defect #1 named in
``.claude/shared/CLAUDE.md`` §2: fine for one desktop user, but on a shared
classroom server two students running analyses at once would silently
corrupt each other's progress and cancellation, because both were reading
and writing the same dict.

``RunContext`` fixes that by construction: nothing here lives at module
scope. Each run gets its own ``RunContext``, so two runs never share a
``threading.Event`` or a callback closure, and there is nothing for a second
run to corrupt.

The reference's ``ui`` package's ``state`` module -- five entry points --
collapse into this object's fields, grouped by what they actually did rather
than ported one call site at a time:

* ``get_run_state("stop")`` / the driver-owned "running" flag it wrote back
  (reference ``:76,118,119,126,127,139,145,182,319,322``) -- ``cancel``, a
  plain ``threading.Event``. The "running" acknowledgement writes are not
  ported at all: the caller that set ``cancel`` already knows the run is
  stopping.
* ``status_msg`` / ``current_phase`` (reference ``:92,115,151,192,304,328``)
  -- ``on_log`` and ``on_phase``. The reference's ``status_msg`` was a
  single-slot mailbox, read and blanked by the desktop poller
  (its ``ui`` package's ``components.py:385-387``); under N concurrent workers that silently
  drops messages. A callback has no such slot to overwrite.
* ``progress`` (reference ``:172-175,270,274,341``) -- ``on_progress``, fed a
  plain ``float`` in ``[0.0, 1.0]``. The reference's hard-coded ``0·78`` /
  ``0·80`` scale factors, which existed only to leave room on a Dear PyGui
  bar for the driver's own bookkeeping, are gone; scaling for a progress bar
  is the driver's job now, not the engine's.
* ``add_active_node`` / ``add_completed_node`` / ``mark_nodes_completed``
  (reference ``:300,303,339``) -- one ``on_node(status, nids)`` callback.
  ``engine/analytical_loop.py`` is their only caller anywhere in the
  reference, so there is no second consumer that needs a three-function
  surface preserved.
* ``n_workers`` (reference ``:225``) -- a plain field, ``RunContext.n_workers``.

Not ported at all: ``progress_ctx`` (reference ``:258-267``), a dict shared
with the desktop render thread purely to drive N stacked per-worker progress
bars on screen. It has no physics meaning. ``cutflow_ready`` (reference
``:348-350``) is not a field here either -- see ``RunResult`` below.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, FrozenSet, Iterable, Optional


def _noop_progress(fraction: float) -> None:
    """Default ``on_progress``: discard the value."""
    return None


def _noop_log(message: str) -> None:
    """Default ``on_log``: discard the message."""
    return None


def _noop_phase(phase: str) -> None:
    """Default ``on_phase``: discard the phase label."""
    return None


def _noop_node(status: str, nids: FrozenSet[int]) -> None:
    """Default ``on_node``: discard the node update."""
    return None


@dataclass
class RunContext:
    """Everything one analysis run needs to report itself and be cancelled.

    Built fresh per run -- never shared, never stored at module scope. Two
    ``RunContext`` instances are independent: setting ``cancel`` on one has
    no effect on the other, and each one's callbacks only ever see values
    from the run that owns it.

    Callbacks default to no-ops so a ``RunContext`` can be constructed with
    no arguments (e.g. in a test that only cares about cancellation), but a
    real caller supplies sinks that write to its own job registry entry or
    SSE stream.
    """

    # Default matches the reference's ``ui.state.RUN_STATE["n_workers"]`` seed
    # value (``ui/state.py:18``, "number of parallel sample workers
    # (user-configurable)"), which the reference exposes through a slider
    # capped at ``[1, 8]`` (``fce.py:598``). 4 is that slider's starting
    # position, not a number invented for this webapp -- a caller that wants
    # something else (task B-011's driver, eventually a per-mission or
    # per-server setting) passes it explicitly; nothing here reads it from
    # config on its own.
    n_workers: int = 4
    cancel: threading.Event = field(default_factory=threading.Event)
    on_progress: Callable[[float], None] = _noop_progress
    on_log: Callable[[str], None] = _noop_log
    on_phase: Callable[[str], None] = _noop_phase
    on_node: Callable[[str, FrozenSet[int]], None] = _noop_node

    def node(self, status: str, nids: Iterable[int]) -> None:
        """Report a node status change, normalising *nids* to a frozenset.

        *status* is ``"active"`` or ``"completed"``, matching the reference's
        ``add_active_node``/``add_completed_node``/``mark_nodes_completed``
        collapsed into one callback (see module docstring).
        """
        self.on_node(status, frozenset(nids))


@dataclass(frozen=True)
class RunResult:
    """What one call to ``run_physics_loop`` -- or, above it, one call to
    ``fce_web.engine.driver.run_analysis`` -- produced.

    Replaces the reference's ``RUN_STATE["cutflow_ready"]`` side effect
    (``:348-350``) with an explicit return value.

    ``cancelled`` and ``reason`` are B-011 additions, both defaulted so
    every existing ``RunResult(processed_any=..., cutflow_ready=...)`` call
    site in ``engine/analytical_loop.py`` (task B-009) keeps working
    unchanged. A cancelled run is not the same as a clean finish: it must
    report ``cancelled=True`` distinguishably, while still carrying
    ``processed_any``/``cutflow_ready`` for whatever partial output existed
    before the stop. ``reason`` is set on the two paths that end a run
    without producing a normal result -- cancellation, and a driver-level
    skip such as a missing dataset directory -- and is always a plain
    sentence a caller can show a student, never a bare ``False``/``None``
    or an internal label.
    """

    processed_any: bool
    cutflow_ready: bool
    cancelled: bool = False
    reason: Optional[str] = None
