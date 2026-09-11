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
``fce_web.app.create_app`` and reached through ``request.app.state.jobs``.
Two ``JobRegistry`` instances share nothing -- not a dict, not a lock, not a
cache.

**The progress queue, named for B-022.** Every ``Job`` carries ``events``, a
``queue.Queue[dict]`` fed by the run's ``RunContext`` callbacks. Full item
shapes and the exactly-one-sentinel contract are in ``docs/api.md``'s
"Run progress event" section -- this is the one place that contract is
written out; do not restate it here. ``submit()`` also records, by object
identity, which job each ``events`` queue was created for (``owner_of``) --
the SSE layer sources a frame's ``runId`` from that record rather than from
whichever ``Job`` it was handed to read, so a bug that ever points two jobs
at the same queue is still detectable instead of self-consistently wrong.

**The content-addressed cache, at the job-registry layer.** The engine
already caches on disk per histogram digest (``engine/analytical_loop.py``,
``.claude/shared/CLAUDE.md`` §2) -- a second run with the same cuts reads its
histogram straight off disk instead of re-processing events. That happens
regardless of anything here. What this registry adds is *visibility*: it
remembers, in memory, which finished job produced which ``RunConfig``
(recognised by ``RunConfig.to_dict()`` -- the same fields
``compute_h5``/``compute_h5_sel`` hash, so two graphs that resolve to an
identical config are the same digest even from different missions or node
ids). Submitting the same config again returns a *new* run id, already
``"done"``, with ``cache_hit=True`` -- the caller can say "recognised these
cuts" without inspecting a single ROOT file, and the reused payload's
``meta.mission`` is restamped to the new job's own mission
(``_retag_payload``), never the first submitter's.
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
from fce_web.payload import build_histogram_payload
from fce_web.runs import RunContext, RunResult

# V1 ships exactly one energy/detector pair (`.claude/shared/CLAUDE.md` §5).
# `content/missions/*.yaml` and the loader that would resolve a `missionId`
# to its own `Dataset` do not exist yet -- that is a later M3 task, not this
# one's file scope. `missionId` is still accepted and threaded through to
# the payload's `meta.mission`; only the dataset lookup is hardcoded.
# ponytail: replace with a mission lookup once missions.py exists.
_V1_DATASET = Dataset(energy="91 GeV", detector="IDEA")

# ponytail: process-lifetime cap on how many finished jobs the registry
# remembers, not a real LRU -- a classroom session submits at most a few
# hundred runs. Evicts the oldest non-"running" job once over the cap
# (F8); upgrade to a real eviction policy if a long-lived server ever gets
# near it.
_MAX_JOBS = 500


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
    call and hang it off ``app.state`` -- never a module global.
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
        self._jobs: Dict[str, Job] = OrderedDict()
        self._cache: Dict[str, str] = {}  # config digest -> finished job id
        # `output/hist{plot_idx}_{sample}.root` is addressed by *plot_idx*
        # (0, 1, 2, ... assigned fresh per graph -- `fce_web.graph`'s own
        # `plot_idx` counter), not by run, and `run_physics_loop` always
        # resolves its output directory via `get_fce_home()` with no
        # argument (the real process environment, not this registry's
        # `_env` -- see `tests/test_fixture_dataset.py`'s note on that
        # inconsistency). Two jobs both producing a `plot_idx=0` histogram
        # would therefore write and read the same file concurrently and
        # corrupt each other's result unless serialized here.
        # ponytail: process-wide lock around the write+read of that shared
        # directory, not per-job isolation -- jobs stay independently
        # tracked (submitted, progressed, and cancelled independently) and
        # only their disk I/O queues up. Upgrade to a per-job output
        # directory if `run_physics_loop` ever accepts an explicit `hdir`.
        self._run_lock = threading.Lock()
        # id(events queue) -> the job id `submit()` created it for. Read by
        # `fce_web.routes.api._drain` via `owner_of` so a frame's `runId` on
        # the wire is sourced from who actually produced it, not from
        # whichever `Job` the reading stream happens to hold.
        self._queue_owner: Dict[int, str] = {}

    def submit(self, graph: dict, mission_id: str) -> Job:
        """Validate *graph* and start (or instantly resolve, on a cache
        hit) a run. Raises :class:`fce_web.graph.GraphError` for an invalid
        graph -- before any job is created or thread started.
        """
        config = build_run_config(graph, _V1_DATASET)
        digest = _config_digest(config)

        job_id = uuid.uuid4().hex
        events: "queue.Queue" = queue.Queue()
        ctx = _make_ctx(events)

        with self._lock:
            self._queue_owner[id(events)] = job_id
            cached_id = self._cache.get(digest)
            cached = self._jobs.get(cached_id) if cached_id else None
            if cached is not None:
                job = Job(
                    id=job_id, mission_id=mission_id, ctx=ctx,
                    events=events, status="done", cache_hit=True,
                    result=cached.result,
                    payload=_retag_payload(cached.payload, mission_id),
                )
                self._jobs[job.id] = job
                self._evict_over_cap()
                job.events.put({"type": "done", "status": "done"})
                return job

            job = Job(id=job_id, mission_id=mission_id, ctx=ctx, events=events)
            self._jobs[job.id] = job
            self._evict_over_cap()

        thread = threading.Thread(
            target=self._run, args=(job, config, digest), daemon=True,
        )
        thread.start()
        return job

    def get(self, run_id: str) -> Optional[Job]:
        """The job for *run_id*, or ``None`` if no such run exists in this
        registry -- a second app's registry never has it either."""
        with self._lock:
            return self._jobs.get(run_id)

    def owner_of(self, events: "queue.Queue") -> Optional[str]:
        """The job id whose ``submit()`` call created *events*, looked up by
        object identity -- independent of which ``Job`` a caller is holding.
        ``None`` only if *events* was never created by this registry."""
        with self._lock:
            return self._queue_owner.get(id(events))

    def _evict_over_cap(self) -> None:
        """Drop the oldest non-``"running"`` job once ``self._jobs`` exceeds
        ``_MAX_JOBS`` (F8). Caller holds ``self._lock``."""
        while len(self._jobs) > _MAX_JOBS:
            for old_id, old_job in self._jobs.items():
                if old_job.status != "running":
                    del self._jobs[old_id]
                    break
            else:
                break  # every job on record is still running; nothing to evict

    def _run(self, job: Job, config: RunConfig, digest: str) -> None:
        """Runs on a background thread, one per submitted job. The whole
        body -- the engine call and the payload build alike -- lives inside
        one ``try/except Exception``, so *any* failure (an engine bug, a
        bad histogram file, anything) still lands ``job`` in a terminal
        status and still puts the sentinel on ``job.events`` (see
        ``docs/api.md``'s "Run progress event" section for the queue's
        contract); nothing here may leave a job stuck at ``"running"`` with
        a caller blocked on the queue forever.
        """
        # Serialized: see the `_run_lock` note in `__init__`. A job waiting
        # its turn is still `"running"` and its cancellation still works --
        # `run_analysis` discovers the dataset directory first, then checks
        # `ctx.cancel.is_set()` before reading any events
        # (`engine/driver.py:run_analysis`), so a queued job cancelled
        # before its turn still returns a `cancelled=True` result soon
        # after it gets one, without processing a single event.
        status, error, payload, result = "error", None, None, None
        with self._run_lock:
            try:
                result = run_analysis(config, job.ctx, self._env)
                if result.cancelled:
                    status, error = "cancelled", result.reason
                elif not result.processed_any:
                    error = result.reason or "The run produced no output."
                else:
                    payload = self._build_payload(job, config, result)
                    status = "done"
            except Exception as exc:  # engine bug, not a student mistake -- still must not hang the HTTP layer
                error = str(exc)

            # `job.lock` wraps only this assignment, never the ROOT read
            # above -- a concurrent `GET .../result` acquiring `job.lock`
            # must not stall behind a run's disk I/O.
            with job.lock:
                job.result = result
                job.status = status
                job.error = error
                job.payload = payload

        if status == "done":
            with self._lock:
                self._cache[digest] = job.id
        job.events.put({"type": "done", "status": status})

    def _build_payload(self, job: Job, config: RunConfig, result: RunResult) -> dict:
        """Read the finished run's histogram files into the chart payload.
        Raises straight through on any failure (including
        ``fce_web.payload.PayloadError``) -- the caller's single
        ``try/except`` in ``_run`` handles it uniformly.
        """
        mc_samples = [s for s in result.active_samples if s != "data"]
        hist = config.histograms[0]
        meta = {
            "mission": job.mission_id,
            "detector": config.detector,
            "energy": config.energy,
            "xLabel": hist.x_label,
            "processNames": {name: name for name in mc_samples},
        }
        return build_histogram_payload(
            str(get_fce_home(self._env)), hist.plot_idx, mc_samples, meta,
        )
