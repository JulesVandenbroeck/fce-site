"""Tests for ``fce_web.runs.RunContext`` and its use by
``fce_web.engine.analytical_loop`` (task B-009).

These check the property the reference's ``ui.state.RUN_STATE`` module-level
dict could never have: that two runs in flight, each with its own
``RunContext``, cannot see each other's progress, log lines, node status, or
cancellation.

Where a run needs to be driven without real ROOT datasets, tests monkeypatch
``fce_web.engine.analytical_loop._process_sample`` with a fast synthetic
stand-in that still calls into the same ``_TaskTracker``/``RunContext``
plumbing the real one does -- "drive a stubbed or injected loop body" per the
task, not a simulated interleaving of Python objects: the two-context test
below uses real ``threading.Thread`` objects.
"""
import inspect
import os
import subprocess
import sys
import threading
import time

import pytest

import fce_web.engine.analytical_loop as analytical_loop
import fce_web.runs as runs_module
from fce_web.runs import RunContext
from tests.test_app import _module_level_state


def _cfg(n_selections_h5: str = "deadbeef") -> dict:
    """A minimal analysis config: one selection, no histograms, that will
    never find real data files -- exercising the fast "Missing data" path
    without needing a dataset on disk.
    """
    return {
        "detector": "IDEA",
        "energy": "91 GeV",
        "selections": [{
            "h5_sel": n_selections_h5,
            "sel_exprs": [],
            "node_name": "test-selection",
            "nid": 1,
            "histograms": [],
        }],
    }


# ---------------------------------------------------------------------------
# Criterion 1: no ui coupling, checked from inside a poisoned process
# ---------------------------------------------------------------------------

def test_analytical_loop_imports_and_runs_with_ui_poisoned(tmp_path):
    """Importing and *running* ``analytical_loop`` must succeed even if
    ``ui``/``ui.state`` are broken -- proving the module needs neither at
    import time nor when actually driving a run, not merely that the literal
    ``from ui.state import ...`` line is gone.

    Modelled on ``tests/test_path_filter.py:165``
    (``test_path_filter_imports_with_ui_poisoned``); run in a subprocess for
    the same reason that test's docstring gives: poisoning
    ``sys.modules["ui"] = None`` leaks into the rest of the interpreter
    otherwise, corrupting every other test in this session.

    ``FCE_HOME`` is pointed at a throwaway directory so the run creates no
    files outside the test's own tmp_path.
    """
    code = (
        "import sys\n"
        "sys.modules['ui'] = None\n"
        "sys.modules['ui.state'] = None\n"
        "import fce_web.engine.analytical_loop as al\n"
        "from fce_web.runs import RunContext\n"
        "events = []\n"
        "ctx = RunContext(\n"
        "    n_workers=1,\n"
        "    on_progress=lambda f: events.append(('progress', f)),\n"
        "    on_node=lambda status, nids: events.append(('node', status, nids)),\n"
        ")\n"
        "cfg = {\n"
        "    'detector': 'IDEA', 'energy': '91 GeV',\n"
        "    'selections': [{'h5_sel': 'deadbeef', 'sel_exprs': [],\n"
        "                    'node_name': 'n', 'nid': 1, 'histograms': []}],\n"
        "}\n"
        "result = al.run_physics_loop(cfg, ['X1'], ctx)\n"
        "assert any(e[0] == 'progress' for e in events), events\n"
        "assert any(e[0] == 'node' for e in events), events\n"
        "assert result.processed_any is False\n"
    )
    env = dict(os.environ)
    env["FCE_HOME"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, (
        f"subprocess with ui poisoned failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


# ---------------------------------------------------------------------------
# Criterion 2: two concurrent runs keep separate progress and cancellation
# ---------------------------------------------------------------------------

def _stub_process_sample(sel_cfg, s, idx, active_samples, cfg,
                         compiled_sel_exprs, ctx, tracker, hdir):
    """Fast stand-in for the real ``_process_sample``: no ROOT file is
    touched. Simulates a small amount of work via ``ctx.cancel.wait`` so
    cancellation set from another thread wakes this one immediately rather
    than after a fixed sleep, then records one completed task exactly as the
    real function does.
    """
    cancelled = ctx.cancel.wait(timeout=0.05)
    if cancelled:
        return False
    fraction = tracker.increment()
    ctx.on_progress(fraction)
    return True


def _build_context_factory(progress_by_name):
    """The correct factory: a fresh ``RunContext`` per caller, tagging its
    own progress values with its own name.
    """
    def build_context(name, n_workers):
        return RunContext(
            n_workers=n_workers,
            on_progress=lambda f, n=name: progress_by_name[n].append(f),
        )
    return build_context


def _crossed_context_factory(progress_by_name):
    """Broken factory used only for the mutation transcript in the PR body
    (never collected as a permanent test -- a test that must always fail
    would break CI): hands back the SAME ``RunContext`` no matter which
    caller asks, modelling exactly the defect this criterion exists to
    catch -- two runs sharing one context, so cancelling one cancels both
    and their progress is indistinguishable.
    """
    shared = RunContext(
        n_workers=4,
        on_progress=lambda f: progress_by_name["A"].append(f),
    )

    def build_context(name, n_workers):
        return shared
    return build_context


def _run_two_contexts(monkeypatch, tmp_path, build_context_factory):
    """Drive two real analysis runs concurrently on real ``threading.Thread``
    objects, using *build_context_factory* to build each run's ``RunContext``.
    Cancels the "A" run shortly after both start; "B" is left to finish.
    Returns (progress_by_name, results).
    """
    monkeypatch.setattr(analytical_loop, "_process_sample", _stub_process_sample)
    monkeypatch.setenv("FCE_HOME", str(tmp_path))

    progress_by_name: dict = {"A": [], "B": []}
    build_context = build_context_factory(progress_by_name)

    # Built up front, before either thread starts, so the test can reach
    # ctx_a.cancel while A's run is genuinely in flight rather than after
    # it has already finished.
    ctx_a = build_context("A", 4)
    ctx_b = build_context("B", 4)

    results: dict = {}

    def run(name, ctx, n_active_samples):
        cfg = _cfg(n_selections_h5=f"h5-{name}")
        active_samples = [f"S{i}" for i in range(n_active_samples)]
        results[name] = analytical_loop.run_physics_loop(cfg, active_samples, ctx)

    # A has more samples than B so it is still running when B finishes,
    # giving the cancellation something to interrupt.
    thread_a = threading.Thread(target=run, args=("A", ctx_a, 8))
    thread_b = threading.Thread(target=run, args=("B", ctx_b, 2))
    thread_a.start()
    thread_b.start()

    # Cancel A shortly after it starts -- well before its 8 stubbed samples
    # (4 at a time, ~0.05s each per _stub_process_sample) could finish, and
    # B (2 samples) finishes on its own before this matters to it.
    time.sleep(0.01)
    ctx_a.cancel.set()

    thread_a.join(timeout=5)
    thread_b.join(timeout=5)
    assert not thread_a.is_alive() and not thread_b.is_alive(), "a run thread did not finish"

    return progress_by_name, results


def test_two_run_contexts_keep_progress_and_cancellation_separate(monkeypatch, tmp_path):
    progress_by_name, results = _run_two_contexts(monkeypatch, tmp_path, _build_context_factory)

    # (a) each context's recorded progress sequence contains only its own values
    assert len(progress_by_name["B"]) > 0, (
        f"context B recorded no progress values of its own "
        f"(A recorded {progress_by_name['A']}, B recorded {progress_by_name['B']}) "
        f"-- context B observed context A's callbacks instead of its own"
    )

    # (b) cancelling A stops A (no final 1.0) and leaves B running to completion (final 1.0)
    assert 1.0 in progress_by_name["B"], (
        f"context B never reported completion (recorded {progress_by_name['B']}); "
        f"expected B to run to completion unaffected by A's cancellation"
    )
    assert 1.0 not in progress_by_name["A"], (
        f"context A reported completion (recorded {progress_by_name['A']}) despite being "
        f"cancelled -- context A observed context B's completion instead of stopping on its own"
    )


# ---------------------------------------------------------------------------
# Criterion 3: neither new module holds module-level mutable state
# ---------------------------------------------------------------------------

def test_no_module_level_mutable_state_in_runs_and_analytical_loop():
    """``fce_web.runs`` and ``fce_web.engine.analytical_loop`` hold nothing
    mutable at import time -- the property that replaces the reference's
    ``ui.state.RUN_STATE`` global. See ``tests/test_app.py``'s identically
    named helper, reused here rather than duplicated because ``tests/`` is a
    package (``tests/__init__.py``).
    """
    assert _module_level_state(runs_module) == {}
    assert _module_level_state(analytical_loop) == {}


# ---------------------------------------------------------------------------
# Criterion 4: no UI layout constants; progress observes the whole path, not
# just its endpoints -- a real 3-task run must report 1/3, 2/3, 1.0, not
# merely "somewhere in range, non-decreasing, ends at 1.0".
# ---------------------------------------------------------------------------

class _FakeTree:
    """Stand-in for the ``uproot`` tree object: enough surface for
    ``_process_sample`` to build an empty cache from it (``nev=0``, so the
    real ``filter_raw_event_data`` per-event loop never executes and no
    other branch keys are needed) -- while running the REAL
    ``_process_sample``, not a stub, so the real call site at
    ``analytical_loop.py:188-189`` executes for real.
    """

    def keys(self):
        return ["weight", "MET_pt"]

    def iterate(self, v_keys, step_size, library):
        import numpy as np
        yield {
            "weight": np.array([], dtype=np.float32),
            "MET_pt": np.array([], dtype=np.float32),
        }


class _FakeRootFile:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def __getitem__(self, key):
        return _FakeTree()


def _install_fake_uproot_source(monkeypatch):
    """Make every sample look like a real, but empty, ROOT file -- so
    ``_process_sample`` runs its real cache-building path (creating a real
    ``sel_cache`` file via the real ``save_cache``) without touching a real
    dataset on disk.
    """
    monkeypatch.setattr(analytical_loop, "_find_data_file",
                        lambda cfg, s, hdir: "fake.root")
    monkeypatch.setattr(analytical_loop.uproot, "open",
                        lambda path: _FakeRootFile())


def test_progress_values_are_bounded_monotonic_and_reach_one(tmp_path, monkeypatch):
    """Drives the real ``_process_sample`` (via ``_install_fake_uproot_source``,
    not a stub of ``_process_sample`` itself) over 3 samples in 1 selection,
    so all three progress seams -- the initial report, the real per-task
    ``tracker.increment()``/``_report_progress`` call at
    ``analytical_loop.py:188-189``, and the final report -- fire for real.
    """
    monkeypatch.setenv("FCE_HOME", str(tmp_path))
    _install_fake_uproot_source(monkeypatch)
    recorded = []
    ctx = RunContext(n_workers=1, on_progress=lambda f: recorded.append(f))
    cfg = _cfg()
    result = analytical_loop.run_physics_loop(cfg, ["X1", "X2", "X3"], ctx)

    assert result.processed_any is True, "the fake data source was not exercised"
    assert recorded, "no progress values were ever reported"
    assert all(0.0 <= f <= 1.0 for f in recorded), recorded
    assert recorded == sorted(recorded), f"progress went backwards: {recorded}"

    # The exact intermediate values, not just "in range and monotonic and
    # ends at 1.0" -- 1/3 after the first sample, 2/3 after the second, then
    # 1.0 twice (the third sample's own completion, and the run's final
    # unconditional report). A uniform down-scale anywhere on the path
    # (``_TaskTracker.increment``, the mid-run call site, or
    # ``_report_progress`` itself) changes these exact numbers even though
    # it would still look "in range, monotonic, ends at 1.0".
    assert recorded == [0.0, 1 / 3, 2 / 3, 1.0, 1.0], recorded


def test_no_ui_layout_scale_constants_in_source():
    """Mirrors the acceptance criterion's own grep:
    ``grep -nE '0\\.78|0\\.80' src/fce_web/engine/analytical_loop.py``.
    """
    import re
    source = inspect.getsource(analytical_loop)
    assert not re.search(r"0\.78|0\.80", source), (
        "found a 0.78/0.80 UI progress-bar scale constant in analytical_loop.py"
    )


# ---------------------------------------------------------------------------
# Criterion 5: the dead samples/en parameters are gone
# ---------------------------------------------------------------------------

def test_run_physics_loop_has_no_dead_parameters():
    sig = inspect.signature(analytical_loop.run_physics_loop)
    assert list(sig.parameters) == ["cfg", "active_samples", "ctx"], sig


# ---------------------------------------------------------------------------
# grep-equivalent sanity check that the module never imports ui -- mirrors
# the acceptance criterion's own check:
# grep -rnE '(^|[^A-Za-z_.])ui\.|from ui|import ui' src/fce_web/
# ---------------------------------------------------------------------------

def test_analytical_loop_source_has_no_ui_import():
    import re
    source = inspect.getsource(analytical_loop)
    pattern = re.compile(r"(^|[^A-Za-z_.])ui\.|from ui|import ui")
    matches = [line for line in source.splitlines() if pattern.search(line)]
    assert not matches, matches


# ---------------------------------------------------------------------------
# Criterion 6: cutflow_ready is False because cutflow_plotter is deferred,
# not because plotting genuinely failed -- and a log line says which.
# ---------------------------------------------------------------------------

def test_cutflow_ready_is_false_because_plotter_is_deferred_not_because_it_failed(
    tmp_path, monkeypatch,
):
    """``fce_web.engine.cutflow_plotter`` does not exist in this vendor tree --
    deferred to M5/M6 by an explicit user ruling on vendor scope, not an
    accidental gap. ``cutflow_ready`` is unconditionally False today because
    of that deferral, and a log line names the reason, so a student's
    genuinely failed cutflow plot is not indistinguishable from a feature
    that has not been built yet.
    """
    monkeypatch.setenv("FCE_HOME", str(tmp_path))
    logs = []
    ctx = RunContext(on_log=lambda m: logs.append(m))
    cfg = _cfg()

    result = analytical_loop.run_physics_loop(cfg, [], ctx)

    assert result.cutflow_ready is False
    assert any("cutflow_plotter" in m and "deferred" in m for m in logs), logs


# ---------------------------------------------------------------------------
# Criterion 7(a): ctx.cancel reaches fill_histogram_from_cache -- B-007 added
# the parameter, and this is its only engine caller.
# ---------------------------------------------------------------------------

def test_fill_histogram_from_cache_receives_run_context_cancel(tmp_path, monkeypatch):
    monkeypatch.setenv("FCE_HOME", str(tmp_path))
    h5_sel = "deadbeef"
    sample = "X1"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Pre-existing selection cache: _process_sample skips straight to the
    # histogram-fill branch, so no ROOT data or fake source is needed.
    (cache_dir / f"sel_{h5_sel}_{sample}.npz").touch()

    calls = []

    def fake_fill(cache_file, out_hist, observable, with_syst=True, cancel=None):
        calls.append(cancel)

    monkeypatch.setattr(analytical_loop, "fill_histogram_from_cache", fake_fill)

    ctx = RunContext(n_workers=1)
    cfg = {
        "detector": "IDEA", "energy": "91 GeV",
        "selections": [{
            "h5_sel": h5_sel, "sel_exprs": [], "node_name": "n", "nid": 1,
            "histograms": [{
                "observable": "l1.pt", "bins": 10, "min": 0, "max": 100,
                "target": "target", "h5": "aaaa", "plot_idx": 0,
            }],
        }],
    }

    analytical_loop.run_physics_loop(cfg, [sample], ctx)

    assert calls == [ctx.cancel], (
        f"fill_histogram_from_cache was called with cancel={calls!r}, "
        f"expected exactly [ctx.cancel] -- the run's own context.cancel must "
        f"reach its only engine caller"
    )


# ---------------------------------------------------------------------------
# Criterion 7(b): a run that processed nothing must not report 100% --
# "100%" for a dead run reads as success in B-011's SSE stream.
# ---------------------------------------------------------------------------

def test_final_progress_report_is_not_sent_when_nothing_was_processed(tmp_path, monkeypatch):
    monkeypatch.setenv("FCE_HOME", str(tmp_path))
    recorded = []
    ctx = RunContext(on_progress=lambda f: recorded.append(f))
    cfg = _cfg()

    result = analytical_loop.run_physics_loop(cfg, ["X1"], ctx)

    assert result.processed_any is False  # no real data files exist for X1
    assert 1.0 not in recorded, (
        f"a run that processed nothing reported 100% progress: {recorded}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
