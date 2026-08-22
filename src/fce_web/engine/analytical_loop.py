"""Runs the physics analysis loop: turns raw ROOT events into a content-addressed
cache, fills histograms per selection branch, and writes the cutflow chart.

Vendored from the reference repo's ``engine/analytical_loop.py`` (kskovpen/fce),
353 lines, with every coupling to the reference's global run-state dict --
its ``ui`` package's ``state`` module, ``RUN_STATE`` (task B-009, defect #1
in ``.claude/shared/CLAUDE.md`` §2) -- replaced by an explicit ``RunContext``
(``fce_web.runs.RunContext``) passed down the call chain as a parameter. This
is a decoupling task, not a physics change: no numeric formula in this file
differs from the reference. See ``fce_web.runs`` for the full mapping from
the reference's ``ui`` package's ``state`` module -- five entry points -- to
``RunContext`` fields.

Two things the reference did that are not ported at all:

* ``progress_ctx`` (reference ``:258-267``) -- a dict sharing two
  ``threading.Lock``s with the desktop render thread, whose slot-pool
  machinery exists only to drive N stacked per-worker progress bars on
  screen. No physics meaning. What *does* have physics meaning -- counting
  how many (selection, sample) tasks are complete -- survives as
  ``_TaskTracker`` below, built fresh per call to ``run_physics_loop`` and
  never shared between runs.
* the hard-coded ``0·78`` (reference ``:174`` twice, ``:274``) and ``0·80``
  (reference ``:341``) progress scale factors -- UI layout constants baked
  into the engine, existing only to leave headroom on a Dear PyGui bar for
  the driver's own post-processing. The engine now reports ``0.0``-``1.0`` of
  its own work; scaling for a progress bar is the driver's job (B-011).

``run_physics_loop``'s ``samples`` and ``en`` parameters, present but unused
in the reference (``:205``), are dropped here (task B-009 criterion 5).
"""
import json
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import boost_histogram as bh
import uproot

from fce_web.engine.path_filter import (filter_raw_event_data, fill_histogram_from_cache,
                                        make_cache_acc, save_cache, preprocess_hep_expr)
from fce_web.engine.path_final import write_final_histograms
from fce_web.paths import get_fce_home
from fce_web.runs import RunContext, RunResult


def _load_event_counts(hdir: str) -> dict:
    """Read the persistent event-count cache at *hdir*/event_counts.json, if any."""
    path = os.path.join(hdir, "event_counts.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _find_data_file(cfg: dict, s: str, hdir: str) -> Optional[str]:
    """Return the path to the ROOT file for sample *s*, or None if not found."""
    for base in (os.getcwd(), hdir):
        path = os.path.join(base, "datasets", cfg["detector"],
                            cfg["energy"].replace(" ", ""), f"{s}.root")
        if os.path.exists(path):
            return path
    return None


class hist:
    def __init__(self):
        self.h = {}

    def create(self, bins, min_val, max_val):
        ax = bh.axis.Regular(bins, min_val, max_val)
        self.h["h"] = bh.Histogram(ax)


class _TaskTracker:
    """Thread-safe count of completed (selection, sample) pairs for one run.

    Replaces the reference's ``progress_ctx["tasks_done"]``/``["tasks_total"]``
    counting, minus the worker-slot pool that lived alongside it (see module
    docstring). One instance is built per ``run_physics_loop`` call and is
    never shared across runs, so two concurrent runs never see each other's
    counts.
    """

    def __init__(self, total: int, done: int = 0):
        self._lock = threading.Lock()
        self.total = total
        self._done = done

    def increment(self) -> float:
        """Record one completed task under lock; return overall progress in [0, 1]."""
        with self._lock:
            self._done += 1
            return self._fraction_locked()

    def fraction(self) -> float:
        """Return the current overall progress in [0, 1]."""
        with self._lock:
            return self._fraction_locked()

    def _fraction_locked(self) -> float:
        if self.total <= 0:
            return 1.0
        return min(1.0, self._done / self.total)


def _report_progress(ctx: RunContext, fraction: float) -> None:
    """Forward *fraction* to ``ctx.on_progress`` unchanged.

    A single named seam for every progress report in this module, so a test
    can monkeypatch exactly one function to verify nothing downstream
    reintroduces a UI scale factor.
    """
    ctx.on_progress(fraction)


def _process_sample(sel_cfg, s, idx, active_samples, cfg,
                    compiled_sel_exprs, ctx: RunContext,
                    tracker: _TaskTracker, hdir: str) -> bool:
    """Process one sample for one selection branch: build cache then fill histograms."""
    n_samp = len(active_samples)
    h5_sel = sel_cfg["h5_sel"]
    histograms = sel_cfg["histograms"]

    branch_cfg = dict(cfg)
    branch_cfg["sel_exprs"] = sel_cfg["sel_exprs"]
    branch_cfg["compiled_sel_exprs"] = compiled_sel_exprs  # OPT-2
    branch_cfg["h5_sel"] = h5_sel

    if ctx.cancel.is_set():
        return False

    sel_cache = os.path.join(hdir, "cache", f"sel_{h5_sel}_{s}.npz")

    # ── Ensure selection cache exists ────────────────────────────────────────
    # Always read from ROOT with ALL combined expressions ([expr_A, expr_B, ...]).
    # Chained selections have the full expression list compiled into sel_exprs by
    # compile_graph_topology, so there is no need to derive from a parent cache.
    # This ensures every worker reads its own ROOT file independently and all N
    # workers run in true parallel for every selection branch.
    if not os.path.exists(sel_cache):
        data_file = _find_data_file(cfg, s, hdir)
        if data_file is None:
            ctx.on_log(f"Missing data: {s}")
            return False

        cache_acc = make_cache_acc()
        try:
            with uproot.open(data_file) as f_root:
                tr = f_root["ntuple"]
                v_keys = [k for k in tr.keys()
                          if "pt" in k or "eta" in k or "phi" in k
                          or "e" in k or "weight" in k or "btag" in k
                          or "d0signif" in k or "z0signif" in k or "charge" in k]

                ctx.on_log("Processing...")

                for arrays in tr.iterate(v_keys, step_size="15 MB", library="np"):
                    if ctx.cancel.is_set():
                        break
                    nev = len(arrays["weight"])
                    _, _, stop_req = filter_raw_event_data(
                        arrays, nev, branch_cfg, None, "",
                        cache_acc=cache_acc, cancel=ctx.cancel,
                    )
                    if stop_req or ctx.cancel.is_set():
                        break
                    del arrays
                    # OPT-5: CPython reference-counting frees arrays immediately;
                    # explicit gc.collect() between baskets is unnecessary overhead.

            if ctx.cancel.is_set():
                return False

            save_cache(sel_cache, cache_acc)

        except Exception as err:
            ctx.on_log(f"Error reading {s}: {err}")
            return False

        # Advance overall progress by one completed (selection, sample) task.
        if os.path.exists(sel_cache):
            fraction = tracker.increment()
            _report_progress(ctx, fraction)

    if not os.path.exists(sel_cache):
        return False

    # ── Fill each histogram in this branch from the selection cache ──────────
    for hcfg in histograms:
        if ctx.cancel.is_set():
            return False

        plot_idx = hcfg.get("plot_idx", 0)
        hist_cache = os.path.join(hdir, "output", f"h5_{hcfg['h5']}_{s}.root")
        out_path = os.path.join(hdir, "output", f"hist{plot_idx}_{s}.root")

        if os.path.exists(hist_cache):
            shutil.copy(hist_cache, out_path)
            ctx.on_log(f"[{idx+1}/{n_samp}] hist{plot_idx} (cache)")
            continue

        outHist = hist()
        outHist.create(int(hcfg["bins"]), float(hcfg["min"]), float(hcfg["max"]))
        fill_histogram_from_cache(sel_cache, outHist, hcfg["observable"],
                                  with_syst=(s != "data"))
        write_final_histograms(hdir, s, hcfg["h5"], outHist, out_path)

    return True


def run_physics_loop(cfg: dict, active_samples: List[str], ctx: RunContext) -> RunResult:
    """Run every selection branch of *cfg* against *active_samples*.

    Reports progress, log lines, phase labels and node status through *ctx*
    (see ``fce_web.runs.RunContext``) instead of a shared global, and
    returns a ``RunResult`` instead of writing ``cutflow_ready`` back to
    global state. Cancellation is ``ctx.cancel``: setting it on this run's
    context stops only this run.
    """
    selections = cfg.get("selections")

    if not selections:
        # Fallback: build a single selection from flat cfg fields
        selections = [{
            "h5_sel":    cfg.get("h5_sel", cfg["h5"]),
            "sel_exprs": cfg.get("sel_exprs", []),
            "node_name": "",
            "histograms": cfg.get("histograms", [{
                "observable": cfg["observable"],
                "bins": cfg["bins"], "min": cfg["min"], "max": cfg["max"],
                "target": cfg["target"], "h5": cfg["h5"], "plot_idx": 0,
            }]),
        }]

    hdir = str(get_fce_home())
    os.makedirs(os.path.join(hdir, "cache"),  exist_ok=True)
    os.makedirs(os.path.join(hdir, "output"), exist_ok=True)

    # ── Number of parallel workers (RunContext-configurable) ──────────────────
    n_workers = max(1, min(ctx.n_workers, len(active_samples))) if active_samples else 1

    # ── Pre-compute event totals for header cache / cutflow denominators ─────
    event_counts = _load_event_counts(hdir)
    ec_prefix = f"{cfg['detector']}_{cfg['energy'].replace(' ', '')}_"

    header_cache: dict = {}
    for s in active_samples:
        cnt = event_counts.get(ec_prefix + s, 0)
        if cnt == 0:
            data_file = _find_data_file(cfg, s, hdir)
            if data_file:
                try:
                    with uproot.open(data_file) as f:
                        header_cache[s] = f["ntuple"].num_entries
                except Exception:
                    header_cache[s] = 0
        else:
            header_cache[s] = cnt

    # ── Task-completion progress: count (sel, sample) pairs ──────────────────
    tasks_total = len(selections) * len(active_samples)
    tasks_pre_cached = sum(
        1
        for sel_cfg in selections
        for s in active_samples
        if os.path.exists(os.path.join(hdir, "cache", f"sel_{sel_cfg['h5_sel']}_{s}.npz"))
    )

    tracker = _TaskTracker(total=tasks_total, done=tasks_pre_cached)

    # Report initial progress to reflect pre-cached work.
    if tasks_total > 0:
        _report_progress(ctx, tracker.fraction())

    processed_any = False

    for sel_cfg in selections:
        sel_nid = sel_cfg.get("nid")
        sel_name = sel_cfg.get("node_name", "")

        # OPT-2: compile selection expressions once per selection branch,
        # shared across all sample workers (code objects are read-only).
        compiled_sel_exprs = [
            compile(preprocess_hep_expr(e), '<sel>', 'eval')
            for e in sel_cfg.get("sel_exprs", []) if e and e.strip()
        ]

        h5_sel = sel_cfg["h5_sel"]
        all_cached = all(
            os.path.exists(os.path.join(
                hdir, "cache", f"sel_{h5_sel}_{s}.npz"))
            for s in active_samples
        )

        if sel_nid is not None:
            prefix_nids = set(sel_cfg.get("prefix_nids", [sel_nid]))
            if all_cached:
                ctx.node("completed", prefix_nids)
            else:
                ctx.node("active", prefix_nids)
                ctx.on_phase(
                    f"Processing: {sel_name}" if sel_name else "Filtering events...")

        # OPT-3: process samples for this selection branch in parallel.
        # Each sample writes to a unique cache path — no cross-sample data races.
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(
                    _process_sample,
                    sel_cfg, s, idx, active_samples, cfg,
                    compiled_sel_exprs, ctx, tracker, hdir,
                ): s
                for idx, s in enumerate(active_samples)
            }
            for fut in as_completed(futures):
                if ctx.cancel.is_set():
                    for f in futures:
                        f.cancel()
                    return RunResult(processed_any=processed_any, cutflow_ready=False)
                try:
                    if fut.result():
                        processed_any = True
                except Exception as e:
                    ctx.on_log(f"Sample error: {e}")

        # Mark this selection and all its observable/histogram nodes as done
        if sel_nid is not None:
            prefix_nids = set(sel_cfg.get("prefix_nids", [sel_nid]))
            nids_to_complete = set(prefix_nids)
            for hcfg in sel_cfg.get("histograms", []):
                if hcfg.get("obs_nid") is not None:
                    nids_to_complete.add(hcfg["obs_nid"])
                if hcfg.get("hist_nid") is not None:
                    nids_to_complete.add(hcfg["hist_nid"])
            ctx.node("completed", nids_to_complete)

    # ── Cut-flow chart ────────────────────────────────────────────────────────
    cutflow_ready = False
    try:
        from fce_web.engine.cutflow_plotter import generate_cutflow_plot
        png_path = generate_cutflow_plot(
            cfg, active_samples, header_cache, selections)
        cutflow_ready = bool(png_path)
    except Exception:
        cutflow_ready = False

    _report_progress(ctx, 1.0)

    return RunResult(processed_any=processed_any, cutflow_ready=cutflow_ready)
