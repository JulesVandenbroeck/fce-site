"""The headless driver: runs one complete analysis from Python alone.

Replaces the reference repo's (kskovpen/fce) ``run_engine.execute_analysis``
(``run_engine.py:18``, signature ``execute_analysis(cfg, _unused)``). That
function is already headless and free of ``dearpygui`` -- its only real
defect is that it returns ``None`` and writes its answers into the global
``ui.state.RUN_STATE`` dict through ``safe_set_state``, at 21 separate call
sites, instead of returning them. ``run_analysis`` here returns a
``RunResult`` (``fce_web.runs.RunResult``) instead, and takes an explicit
``RunContext`` the way ``fce_web.engine.analytical_loop.run_physics_loop``
already does (task B-009) rather than the reference's single shared global.

Per an explicit user ruling on vendor scope (task B-011 dispatch): **this
driver stops once the histogram ROOT files are written.** The reference's
``execute_analysis`` goes on to render a static image of every histogram
(``run_engine.py:55``) and, if any histogram in the config has a fit
target, run a statistical fit (``run_engine.py:87-99``). Neither is ported
here -- the modules that would do either are all vendored later, in
M5/M6.

Two things this module resolves that the reference resolved elsewhere:

* **Which samples to run.** The reference's ``execute_analysis`` reads a
  ``config/samples.json`` file listing every known sample name per energy
  (``run_engine.py:19-38``) to build ``active_samples`` -- a file that lives
  entirely in the reference repo's ``run_engine.py``/``ui`` layer, not in
  ``engine/``, and is not vendored anywhere in this project. Rather than
  vendor a second, independently-maintained list of sample names that can
  drift from what is actually on disk, this driver discovers active samples
  by listing ``<dataset dir>/*.root`` directly -- the same directory
  ``analytical_loop._find_data_file`` already reads from per-sample
  (``engine/analytical_loop.py:56-63``). A sample with no ROOT file present
  is a sample that cannot run either way, so the two approaches agree
  whenever both have data to say something about; this one also works
  correctly when the reference's static list is stale or wrong.
* **Progress scaling around the engine's own 0..1.** B-009 deleted the
  reference's hard-coded Dear PyGui layout scale constants from
  ``analytical_loop.py``: the engine now reports ``0.0``-``1.0`` of its own
  work, and "scaling for a progress bar is the driver's job now, not the
  engine's" (``engine/analytical_loop.py`` module docstring). This driver
  reserves the top ``1 - _ENGINE_PROGRESS_SHARE`` of the ``[0, 1]`` range for
  its own bookkeeping around the engine call (dataset discovery below it,
  the final completion report above it), and forwards every value the
  engine reports through ``_ENGINE_PROGRESS_SHARE`` on the way out. This is
  the *only* place any scale factor is applied, named here rather than
  buried, so an unexplained UI-layout scale constant like the ones B-009
  removed never reappears here.
"""
from __future__ import annotations

import os
from typing import List, Mapping, Optional

from fce_web.engine.analytical_loop import run_physics_loop
from fce_web.engine.runconfig import RunConfig
from fce_web.paths import get_fce_home
from fce_web.runs import RunContext, RunResult

# The fraction of the driver's overall [0, 1] progress range given to the
# engine's own [0, 1]. The remaining headroom is spent on the driver's own
# unconditional final completion report (see ``run_analysis``), which must
# land at exactly 1.0 regardless of what fraction of that headroom the
# engine's own last reported value used. Named and used in exactly one
# place -- the callback built in ``run_analysis`` -- so a reviewer or a
# later change can find every seam that touches a progress value by reading
# this module alone.
_ENGINE_PROGRESS_SHARE = 0.9


def _dataset_dir(config: RunConfig, env: Optional[Mapping[str, str]]) -> str:
    """The directory ``run_physics_loop``'s own ``_find_data_file`` would
    read *config*'s samples from (``engine/analytical_loop.py:56-63``):
    ``<fce home>/datasets/<detector>/<energy with spaces stripped>``.
    """
    hdir = get_fce_home(env)
    return os.path.join(str(hdir), "datasets", config.detector,
                        config.energy.replace(" ", ""))


def _discover_active_samples(dataset_dir: str) -> List[str]:
    """Return the sample names with a ``.root`` file directly under
    *dataset_dir*, sorted for a deterministic run order. Empty if the
    directory does not exist or contains no ROOT files -- both are the
    caller's cue to report a named "missing dataset" skip rather than start
    a run with nothing to process.
    """
    if not os.path.isdir(dataset_dir):
        return []
    return sorted(
        entry[:-len(".root")]
        for entry in os.listdir(dataset_dir)
        if entry.endswith(".root")
    )


def run_analysis(
    config: RunConfig,
    ctx: RunContext,
    env: Optional[Mapping[str, str]] = None,
) -> RunResult:
    """Run *config* end to end -- selection, caching, histogram filling --
    and return a ``RunResult``. No plotting, no fit (see module docstring).

    Reports progress, log lines and phase labels through *ctx* exactly as
    ``run_physics_loop`` does, plus the two phases this driver owns around
    the engine call: locating the dataset, and the driver's own completion
    report.

    *env* is the same optional environment mapping ``fce_web.paths.
    get_fce_home`` accepts -- the seam a test uses to point at a dataset
    directory that does not exist, without touching the real
    ``~/.fce/datasets`` this machine has. ``None`` (the default) means "use
    the real process environment", the same default ``get_fce_home`` itself
    has.
    """
    ctx.on_phase("Locating datasets...")
    dataset_dir = _dataset_dir(config, env)
    active_samples = _discover_active_samples(dataset_dir)

    if not active_samples:
        reason = (
            f"No data found for {config.detector} at {config.energy}. "
            f"Expected .root files in {dataset_dir}, but that folder is "
            f"empty or does not exist."
        )
        ctx.on_log(reason)
        ctx.on_phase("")
        return RunResult(
            processed_any=False, cutflow_ready=False,
            cancelled=False, reason=reason,
        )

    if ctx.cancel.is_set():
        reason = "Run cancelled before any data was read."
        return RunResult(
            processed_any=False, cutflow_ready=False,
            cancelled=True, reason=reason,
        )

    ctx.on_phase("Reading events...")

    # A fresh RunContext for the engine call: same cancel Event (so setting
    # it on the caller's ctx still reaches the engine -- see B-009's
    # criterion 7(a), which this driver must not break), same n_workers,
    # log/phase/node callbacks forwarded unchanged, and a progress callback
    # that scales every engine-space value into this driver's overall
    # range before handing it to the caller's own ctx.on_progress. This is
    # seam 1 of the two the driver touches a progress value at.
    inner_ctx = RunContext(
        n_workers=ctx.n_workers,
        cancel=ctx.cancel,
        on_progress=lambda f: ctx.on_progress(f * _ENGINE_PROGRESS_SHARE),
        on_log=ctx.on_log,
        on_phase=ctx.on_phase,
        on_node=ctx.on_node,
    )

    result = run_physics_loop(config.to_dict(), active_samples, inner_ctx)

    if ctx.cancel.is_set():
        ctx.on_phase("Cancelled")
        return RunResult(
            processed_any=result.processed_any,
            cutflow_ready=result.cutflow_ready,
            cancelled=True,
            reason="Run cancelled by request.",
        )

    if result.processed_any:
        # Seam 2: the driver's own unconditional final completion report.
        # The engine's own last reported value already scaled into
        # [0, _ENGINE_PROGRESS_SHARE] above; this always lands on exactly
        # 1.0 regardless of that value, so a caller watching progress sees
        # the run finish at 100% every time, not at 90%.
        ctx.on_progress(1.0)
        ctx.on_phase("Done")

    return RunResult(
        processed_any=result.processed_any,
        cutflow_ready=result.cutflow_ready,
        cancelled=False,
        reason=None,
    )
