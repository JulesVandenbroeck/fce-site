"""The job registry: joins a student graph to the physics engine over HTTP
(task B-021).

``fce_web.graph.build_run_config`` (B-020) turns a graph payload into a
``RunConfig``; ``fce_web.engine.driver.run_analysis`` (B-011) runs it;
``fce_web.payload.build_histogram_payload`` (B-019) reads the result back
into the chart contract. Nothing before this module joined the three --
this is that join, plus the bookkeeping an HTTP layer needs around a run
that takes seconds to minutes: an id, a background thread, and somewhere to
read progress and the finished result from.

**No module-level mutable state.** ``JobRegistry`` is a plain class with no
state outside ``__init__``; it is constructed once per app in
``fce_web.app.create_app`` and reached through ``request.app.state.jobs``
(``.claude/shared/CLAUDE.md`` §6, C4). Two ``JobRegistry`` instances share
nothing -- not a dict, not a lock, not a cache.

**The progress queue, named for B-022.** Every ``Job`` carries ``events``, a
``queue.Queue[dict]`` fed by the run's ``RunContext`` callbacks. Each item is
one of::

    {"type": "progress", "value": 0.42}
    {"type": "log", "message": "..."}
    {"type": "phase", "phase": "Reading events..."}
    {"type": "node", "status": "active"|"completed", "nids": [1, 2]}

and the queue is terminated by exactly one sentinel::

    {"type": "done", "status": "done"|"error"|"cancelled"}

after which nothing more is ever put on it. A cache-hit job (see below) skips
straight to the sentinel -- there is no run to report progress for. B-022's
SSE endpoint drains this queue with ``queue.Queue.get()`` in a loop until it
sees the sentinel.

**The content-addressed cache, at the job-registry layer.** The engine
already caches on disk per histogram digest
(``engine/analytical_loop.py``, ``.claude/shared/CLAUDE.md`` §2) -- a second
run with the same cuts reads its histogram straight off disk instead of
re-processing events. That happens regardless of anything here. What this
registry adds is *visibility*: it remembers, in memory, which finished job
produced which ``RunConfig`` (recognised by ``RunConfig.to_dict()`` --
the same fields ``compute_h5``/``compute_h5_sel`` hash, so two graphs that
resolve to an identical config are the same digest even from different
missions or node ids). Submitting the same config again returns a *new* run
id, already ``"done"``, with ``cache_hit=True`` -- the caller can say
"recognised these cuts" without inspecting a single ROOT file (C7).
"""
from __future__ import annotations

import json
import queue
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional

from fce_web.engine.driver import run_analysis
from fce_web.engine.runconfig import RunConfig
from fce_web.graph import Dataset, build_run_config
from fce_web.paths import get_fce_home
from fce_web.payload import PayloadError, build_histogram_payload
from fce_web.runs import RunContext, RunResult

# V1 ships exactly one energy/detector pair (`.claude/shared/CLAUDE.md` §5).
# `content/missions/*.yaml` and the loader that would resolve a `missionId`
# to its own `Dataset` do not exist yet -- that is a later M3 task, not this
# one's file scope. `missionId` is still accepted and threaded through to
# the payload's `meta.mission`; only the dataset lookup is hardcoded.
# ponytail: replace with a mission lookup once missions.py exists.
_V1_DATASET = Dataset(energy="91 GeV", detector="IDEA")


def _config_digest(config: RunConfig) -> str:
    """A cache key that changes iff any field of *config* does."""
    return json.dumps(config.to_dict(), sort_keys=True)


@dataclass
class Job:
    """One run's state, owned by exactly one ``JobRegistry``. Two ``Job``
    instances never share a ``RunContext``, an ``events`` queue, or a
    ``lock`` -- each is built fresh in ``JobRegistry.submit``, and *ctx* is
    always set at construction time (never patched on afterwards -- a
    ``get()`` caller must never observe a job with no context).
    """

    id: str
    mission_id: str
    ctx: RunContext
    events: "queue.Queue" = field(default_factory=queue.Queue)
    lock: threading.Lock = field(default_factory=threading.Lock)
    status: str = "running"  # "running" | "done" | "error" | "cancelled"
    cache_hit: bool = False
    result: Optional[RunResult] = None
    payload: Optional[dict] = None
    error: Optional[str] = None


def _make_ctx(events: "queue.Queue") -> RunContext:
    """A ``RunContext`` whose callbacks feed *events* -- nothing shared with
    any other job's context."""
    return RunContext(
        on_progress=lambda f: events.put({"type": "progress", "value": f}),
        on_log=lambda m: events.put({"type": "log", "message": m}),
        on_phase=lambda p: events.put({"type": "phase", "phase": p}),
        on_node=lambda status, nids: events.put(
            {"type": "node", "status": status, "nids": sorted(nids)}
        ),
    )


def _retag_payload(payload: Optional[dict], mission_id: str) -> Optional[dict]:
    """Shallow-copy *payload* and stamp ``meta.mission`` with *mission_id*.

    A cache hit reuses another job's ``payload`` by reference; without this,
    a student in mission B who submits mission A's exact cuts sees mission
    A's ``meta.mission`` in their own result.
    """
    if payload is None:
        return None
    payload = dict(payload)
    payload["meta"] = {**payload.get("meta", {}), "mission": mission_id}
    return payload


class JobRegistry:
    """Owns every ``Job`` for one app. Construct one per ``create_app()``
    call and hang it off ``app.state`` -- never a module global (C4).
    """

    def __init__(self, env: Optional[Mapping[str, str]] = None) -> None:
        """*env* is the same optional environment mapping
        ``fce_web.paths.get_fce_home``/``fce_web.engine.driver.run_analysis``
        accept -- the seam a test uses to point dataset discovery and
        histogram output at a tmp ``FCE_HOME`` instead of the real one.
        ``None`` (the default, used by the real app) means "the real
        process environment".
        """
        self._env = env
        self._lock = threading.Lock()
        self._jobs: Dict[str, Job] = {}
        self._cache: Dict[str, str] = {}  # config digest -> finished job id
        # `output/hist{plot_idx}_{sample}.root` is addressed by *plot_idx*
        # (0, 1, 2, ... assigned fresh per graph -- `fce_web.graph`'s own
        # `plot_idx` counter), not by run, and `run_physics_loop` always
        # resolves its output directory via `get_fce_home()` with no
        # argument (the real process environment, not this registry's
        # `_env` -- see `tests/test_fixture_dataset.py`'s note on that
        # inconsistency). Two jobs both producing a `plot_idx=0` histogram
        # would therefore write and read the same file concurrently and
        # corrupt each other's result (C3) unless serialized here.
        # ponytail: process-wide lock around the write+read of that shared
        # directory, not per-job isolation -- jobs stay independently
        # tracked (submitted, progressed, and cancelled independently) and
        # only their disk I/O queues up. Upgrade to a per-job output
        # directory if `run_physics_loop` ever accepts an explicit `hdir`.
        self._run_lock = threading.Lock()

    def submit(self, graph: dict, mission_id: str) -> Job:
        """Validate *graph* and start (or instantly resolve, on a cache
        hit) a run. Raises :class:`fce_web.graph.GraphError` for an invalid
        graph -- before any job is created or thread started (C2).
        """
        config = build_run_config(graph, _V1_DATASET)
        digest = _config_digest(config)

        with self._lock:
            cached_id = self._cache.get(digest)
            cached = self._jobs.get(cached_id) if cached_id else None
            if cached is not None:
                job = Job(
                    id=uuid.uuid4().hex, mission_id=mission_id, status="done",
                    cache_hit=True, result=cached.result, payload=cached.payload,
                )
                self._jobs[job.id] = job
                job.events.put({"type": "done", "status": "done"})
                return job

            job = Job(id=uuid.uuid4().hex, mission_id=mission_id)
            self._jobs[job.id] = job

        job.ctx = _make_ctx(job)
        thread = threading.Thread(
            target=self._run, args=(job, config, digest), daemon=True,
        )
        thread.start()
        return job

    def get(self, run_id: str) -> Optional[Job]:
        """The job for *run_id*, or ``None`` if no such run exists in this
        registry -- a second app's registry never has it either (C4)."""
        with self._lock:
            return self._jobs.get(run_id)

    def _run(self, job: Job, config: RunConfig, digest: str) -> None:
        """Runs on a background thread, one per submitted job (C1). Never
        raises back into the thread pool -- an engine exception becomes an
        ``"error"`` status, not a crashed thread nobody observes.
        """
        # Serialized: see the `_run_lock` note in `__init__`. A job waiting
        # its turn is still `"running"` and its cancellation still works --
        # `run_analysis` checks `ctx.cancel.is_set()` before touching the
        # dataset, so a queued job cancelled before its turn returns
        # immediately once it gets one.
        with self._run_lock:
            try:
                result = run_analysis(config, job.ctx, self._env)
            except Exception as exc:  # engine bug, not a student mistake -- still must not hang the HTTP layer
                with job.lock:
                    job.status = "error"
                    job.error = str(exc)
                job.events.put({"type": "done", "status": "error"})
                return

            with job.lock:
                job.result = result
                if result.cancelled:
                    job.status = "cancelled"
                    job.error = result.reason
                elif not result.processed_any:
                    job.status = "error"
                    job.error = result.reason or "The run produced no output."
                else:
                    self._finish(job, config)

        if job.status == "done":
            with self._lock:
                self._cache[digest] = job.id
        job.events.put({"type": "done", "status": job.status})

    def _finish(self, job: Job, config: RunConfig) -> None:
        """Reads the finished run's histogram files into the chart payload.
        Caller holds ``job.lock``.
        """
        mc_samples = _mc_samples(config, self._env)
        hist = config.histograms[0]
        meta = {
            "mission": job.mission_id,
            "detector": config.detector,
            "energy": config.energy,
            "xLabel": hist.x_label,
            "processNames": {name: name for name in mc_samples},
        }
        try:
            job.payload = build_histogram_payload(
                str(get_fce_home(self._env)), hist.plot_idx, mc_samples, meta,
            )
        except PayloadError as exc:
            job.status = "error"
            job.error = str(exc)
        else:
            job.status = "done"


def _mc_samples(config: RunConfig, env: Optional[Mapping[str, str]]) -> List[str]:
    """The simulated (non-``data``) sample names ``run_analysis`` just
    processed -- the same discovery it uses internally
    (``fce_web.engine.driver._discover_active_samples``), so the payload is
    built from exactly the samples the run actually wrote, not a guess.
    """
    dataset_dir = _dataset_dir(config, env)
    return [s for s in _discover_active_samples(dataset_dir) if s != "data"]
