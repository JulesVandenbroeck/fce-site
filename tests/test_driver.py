"""Tests for ``fce_web.engine.driver.run_analysis`` (task B-011).

``run_analysis`` is the headless replacement for the reference repo's
``run_engine.execute_analysis`` (kskovpen/fce, ``run_engine.py:18``): it
drives one complete analysis run from a ``RunConfig`` and a ``RunContext``
alone, with no ``ui`` import anywhere in the process, and returns a
``RunResult`` instead of writing answers into the reference's global
``ui.state.RUN_STATE`` dict through ``safe_set_state``.

Per an explicit user ruling on vendor scope (task B-011 dispatch), the
driver stops once the histogram ROOT files are written -- it never calls
``render_plots`` (reference ``run_engine.py:55``) or a fit. Plotting and
fitting are deferred to M5/M6.
"""
import inspect
import os
import subprocess
import sys
import threading
import time

import pytest

import fce_web.engine.driver as driver
from fce_web.engine.runconfig import RunConfig
from fce_web.runs import RunContext, RunResult

FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "content", "analyses", "zpeak-dilepton.json",
)


def _load_fixture_config() -> RunConfig:
    return RunConfig.from_file(FIXTURE)


def _make_dataset_dir(tmp_path, detector="IDEA", energy="91 GeV", samples=("X1",)):
    """Create an empty-but-present dataset directory: one zero-byte ``.root``
    file per name in *samples*. ``run_physics_loop`` never has to read it for
    these tests -- either it is stubbed out entirely, or (criterion 4's own
    test) discovery is the only thing exercised -- so a real ROOT file is
    unnecessary.
    """
    ddir = tmp_path / "datasets" / detector / energy.replace(" ", "")
    ddir.mkdir(parents=True, exist_ok=True)
    for s in samples:
        (ddir / f"{s}.root").touch()
    return ddir


def _env_for(tmp_path):
    return {"FCE_HOME": str(tmp_path)}


# ---------------------------------------------------------------------------
# Criterion 1: no ui coupling anywhere in the process, checked from inside a
# poisoned subprocess that actually drives the run far enough to fire a
# phase and a progress callback -- not merely importing the module.
# ---------------------------------------------------------------------------

def test_driver_source_has_no_ui_import():
    """Mirrors the acceptance criterion's own grep:
    ``grep -rnE '^\\s*(from|import)\\s+ui\\b' src/fce_web/``.
    """
    import re
    source = inspect.getsource(driver)
    pattern = re.compile(r"^\s*(from|import)\s+ui\b", re.MULTILINE)
    assert not pattern.search(source), "driver.py imports the ui package"


def _poisoned_subprocess_code(tmp_path, dataset_root):
    return f"""
import sys
sys.modules['ui'] = None
sys.modules['ui.state'] = None
import fce_web.engine.driver as driver
from fce_web.engine.runconfig import RunConfig
from fce_web.runs import RunContext

events = []
ctx = RunContext(
    n_workers=1,
    on_progress=lambda f: events.append(('progress', f)),
    on_phase=lambda p: events.append(('phase', p)),
)
config = RunConfig.from_file({FIXTURE!r})


def fake_run_physics_loop(cfg, active_samples, inner_ctx):
    from fce_web.runs import RunResult
    inner_ctx.on_phase("Reading events...")
    for f in (0.0, 0.5, 1.0):
        inner_ctx.on_progress(f)
    return RunResult(processed_any=True, cutflow_ready=False)


driver.run_physics_loop = fake_run_physics_loop
result = driver.run_analysis(config, ctx, env={{'FCE_HOME': {str(tmp_path)!r}}})
assert any(e[0] == 'progress' for e in events), events
assert any(e[0] == 'phase' for e in events), events
assert result.processed_any is True, result
"""


def test_run_analysis_imports_and_runs_with_ui_poisoned(tmp_path):
    """Importing AND driving ``run_analysis`` far enough to fire at least one
    ``on_phase`` and one ``on_progress`` must succeed even with ``ui``/
    ``ui.state`` poisoned in ``sys.modules``. Modelled on
    ``tests/test_path_filter.py:165`` and
    ``tests/test_run_context.py::test_analytical_loop_imports_and_runs_with_ui_poisoned``;
    run in a subprocess for the same reason those give: poisoning
    ``sys.modules["ui"]`` leaks into the rest of the interpreter otherwise.

    ``run_physics_loop`` itself is monkeypatched at module level (inside the
    subprocess, so nothing leaks back) to a fast stand-in that still reports
    real progress and phase values through the real ``ctx``, so the
    assertions exercise the driver's own wiring rather than a real dataset
    read.
    """
    _make_dataset_dir(tmp_path)
    code = _poisoned_subprocess_code(tmp_path, tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"subprocess with ui poisoned failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_ui_poison_mutation_is_caught_by_the_subprocess_test(tmp_path, monkeypatch):
    """Mutation transcript for criterion 1: importing ``ui.state`` at the top
    of ``driver.py`` must make the poisoned-subprocess test above fail.
    Reproduced here without touching the tracked file -- a scratch copy of
    the module source with the poison import spliced in, executed the same
    way the real test executes ``driver.py``.
    """
    _make_dataset_dir(tmp_path)
    source = inspect.getsource(driver)
    poisoned_source = "import ui.state\n" + source

    scratch_dir = tmp_path / "poisoned_driver_pkg"
    (scratch_dir / "fce_web" / "engine").mkdir(parents=True)
    (scratch_dir / "fce_web" / "__init__.py").write_text("")
    (scratch_dir / "fce_web" / "engine" / "__init__.py").write_text("")
    (scratch_dir / "fce_web" / "engine" / "driver.py").write_text(poisoned_source)

    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(scratch_dir)!r})\n"
        "sys.modules['ui'] = None\n"
        "sys.modules['ui.state'] = None\n"
        "import fce_web.engine.driver\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True,
    )
    assert result.returncode != 0, (
        "importing a driver.py with 'import ui.state' spliced in should fail "
        f"under ui-poisoning, but it succeeded:\nstdout={result.stdout}"
    )
    assert "ui" in result.stderr, result.stderr


# ---------------------------------------------------------------------------
# Criterion 2: progress fires monotonically 0..1, driver-owned scaling, exact
# sequence for a stubbed multi-step run.
# ---------------------------------------------------------------------------

def _stub_engine_progress_trace(trace):
    """A stand-in for ``run_physics_loop`` that reports a fixed sequence of
    engine-space progress values and one phase change through the
    ``RunContext`` it is handed -- modelling a real multi-sample run's shape
    (``tests/test_run_context.py``'s own stub reports ``[0.0, 1/3, 2/3, 1.0,
    1.0]``) closely enough that the driver's forwarding/scaling code
    actually executes on every value, not just the endpoints.
    """
    def fake_run_physics_loop(cfg, active_samples, inner_ctx):
        inner_ctx.on_phase("Reading events...")
        for f in trace:
            inner_ctx.on_progress(f)
        return RunResult(processed_any=True, cutflow_ready=False)
    return fake_run_physics_loop


def test_progress_sequence_is_exact_for_a_stubbed_multi_step_run(tmp_path, monkeypatch):
    _make_dataset_dir(tmp_path)
    monkeypatch.setattr(
        driver, "run_physics_loop",
        _stub_engine_progress_trace([0.0, 1 / 3, 2 / 3, 1.0, 1.0]),
    )
    recorded = []
    ctx = RunContext(n_workers=1, on_progress=lambda f: recorded.append(f))
    config = _load_fixture_config()

    result = driver.run_analysis(config, ctx, env=_env_for(tmp_path))

    assert result.processed_any is True
    assert result.cancelled is False
    # Hard-coded, not derived from ``driver._ENGINE_PROGRESS_SHARE`` -- a
    # check computed from the value it is meant to pin cannot catch that
    # value changing (cycle 1 review, Required). Every engine-space value
    # scaled by the *current* 0.9 share, then one final driver-owned 1.0
    # completion report appended.
    expected = [0.0, 0.3, 0.6, 0.9, 0.9, 1.0]
    assert recorded == pytest.approx(expected), recorded


def test_progress_ends_at_exactly_one(tmp_path, monkeypatch):
    _make_dataset_dir(tmp_path)
    monkeypatch.setattr(
        driver, "run_physics_loop",
        _stub_engine_progress_trace([0.0, 1.0, 1.0]),
    )
    recorded = []
    ctx = RunContext(n_workers=1, on_progress=lambda f: recorded.append(f))
    result = driver.run_analysis(_load_fixture_config(), ctx, env=_env_for(tmp_path))
    assert result.processed_any is True
    assert recorded[-1] == 1.0, recorded


def test_no_ui_layout_scale_constants_reused_in_driver():
    """The driver must not reintroduce the reference's ``0.78``/``0.80``
    Dear PyGui layout constants (already banned from the engine by B-009).
    """
    import re
    source = inspect.getsource(driver)
    assert not re.search(r"0\.78|0\.80", source), (
        "found a 0.78/0.80 UI progress-bar scale constant in driver.py"
    )


# ---------------------------------------------------------------------------
# Criterion 3: cancellation mid-run returns a RunResult marked cancelled,
# carrying whatever partial output existed.
# ---------------------------------------------------------------------------

def _slow_stub_run_physics_loop(steps=6, step_seconds=0.05):
    """A stand-in for ``run_physics_loop`` that does real, checkable, waitable
    work: it reports partial progress across *steps* steps, checking
    ``ctx.cancel`` between each one via ``Event.wait`` (so a set from another
    thread interrupts it immediately rather than after a fixed sleep), and
    returns a ``RunResult`` whose ``processed_any`` reflects whatever
    fraction of steps actually completed before the stop -- so the returned
    result carries genuine partial output, not a canned value.
    """
    def fake_run_physics_loop(cfg, active_samples, inner_ctx):
        inner_ctx.on_phase("Reading events...")
        completed = 0
        for i in range(steps):
            if inner_ctx.cancel.wait(timeout=step_seconds):
                break
            completed += 1
            inner_ctx.on_progress(completed / steps)
        return RunResult(processed_any=(completed > 0), cutflow_ready=False)
    return fake_run_physics_loop


def test_cancelling_mid_run_returns_a_cancelled_result_with_partial_output(tmp_path, monkeypatch):
    _make_dataset_dir(tmp_path)
    monkeypatch.setattr(driver, "run_physics_loop", _slow_stub_run_physics_loop())

    ctx = RunContext(n_workers=1)
    result_holder = {}

    def run():
        result_holder["result"] = driver.run_analysis(
            _load_fixture_config(), ctx, env=_env_for(tmp_path),
        )

    thread = threading.Thread(target=run)
    thread.start()
    time.sleep(0.12)  # let 1-2 steps complete before cancelling
    ctx.cancel.set()
    thread.join(timeout=5)
    assert not thread.is_alive(), "run did not finish after cancellation"

    result = result_holder["result"]
    assert result.cancelled is True, result
    assert result.processed_any is True, (
        f"cancelled run reported no partial output: {result}"
    )
    # A cancelled run must be distinguishable from a clean finish -- the
    # clean-finish path also has processed_any True, so cancelled itself is
    # the property that must differ.
    assert result != RunResult(processed_any=True, cutflow_ready=False), result


# ---------------------------------------------------------------------------
# Criterion 4: a missing dataset directory is a clean skip with a named
# reason, not a crash and not a silent success.
# ---------------------------------------------------------------------------

def test_missing_dataset_directory_is_a_named_clean_skip(tmp_path):
    """*tmp_path* is empty -- no ``datasets/`` subtree at all -- so
    ``get_fce_home``'s ``env`` parameter (``fce_web.paths.get_fce_home``)
    is the seam that lets this test reach the missing-dataset path without
    touching the real ``~/.fce/datasets`` this machine actually has.
    """
    logs = []
    ctx = RunContext(on_log=lambda m: logs.append(m))
    config = _load_fixture_config()

    result = driver.run_analysis(config, ctx, env=_env_for(tmp_path))

    assert result.processed_any is False
    assert result.cancelled is False
    assert result.reason is not None, "no reason recorded for the missing dataset"
    expected_dir = str(tmp_path / "datasets" / "IDEA" / "91GeV")
    assert expected_dir in result.reason, (
        f"reason does not name the missing dataset path {expected_dir!r}: {result.reason!r}"
    )
    assert any(expected_dir in m for m in logs), (
        f"no log line named the missing dataset path {expected_dir!r}: {logs!r}"
    )


@pytest.mark.skipif(
    not os.path.isdir(os.path.expanduser("~/.fce/datasets/IDEA/91GeV")),
    reason="real datasets not present at ~/.fce/datasets/IDEA/91GeV on this machine",
)
def test_real_datasets_are_discovered_when_present():
    """Runs discovery only (not a full physics run) against the real
    dataset directory this machine has, so the "datasets present" path is
    exercised at least once without needing a stub.
    """
    config = _load_fixture_config()
    dataset_dir = driver._dataset_dir(config, env=None)
    active_samples = driver._discover_active_samples(dataset_dir)
    assert active_samples, "expected at least one sample under ~/.fce/datasets/IDEA/91GeV"
    assert "data" in active_samples or any(s.startswith("X") for s in active_samples)


@pytest.mark.skipif(
    not os.path.isdir(os.path.expanduser("~/.fce/datasets/IDEA/91GeV")),
    reason="real datasets not present at ~/.fce/datasets/IDEA/91GeV on this machine",
)
def test_real_end_to_end_run_exercises_the_real_run_physics_loop():
    """Criterion 7: the one test in this file that never stubs
    ``run_physics_loop``. Every other test above monkeypatches it, so the
    genuine integration seam -- ``config.to_dict()`` ->
    ``run_physics_loop(cfg, active_samples, ctx)``, real ``RunConfig``
    handed to the real ``analytical_loop`` -- is never actually executed by
    the rest of this suite. A signature or dict-shape drift between the two
    would land as a green suite and a broken driver, which is the exact net
    B-012's parity proof is built on top of.

    Runs the real fixture (``content/analyses/zpeak-dilepton.json``) against
    the real ``~/.fce/datasets/IDEA/91GeV`` dataset with no stub anywhere in
    the call chain. Not narrowed to one sample: the content-addressed disk
    cache (``.claude/shared/CLAUDE.md`` §2, "do not break this") means a
    warm cache makes a full run of every sample fast in practice -- see the
    wall-clock time in the PR body -- and narrowing would only remove
    coverage of the multi-sample path.
    """
    events = []
    phases = []
    ctx = RunContext(
        n_workers=4,
        on_progress=lambda f: events.append(f),
        on_phase=lambda p: phases.append(p),
    )
    config = _load_fixture_config()

    result = driver.run_analysis(config, ctx, env=None)

    assert result.processed_any is True, result
    assert result.cancelled is False, result
    assert result.reason is None, result
    assert "Reading events..." in phases, phases
    assert "Done" in phases, phases
    assert events, "no progress reported"
    assert events[-1] == 1.0, events
    assert all(0.0 <= f <= 1.0 for f in events), events


# ---------------------------------------------------------------------------
# Criterion 5: no plotting, no fit, and the driver's own signature is clean.
# ---------------------------------------------------------------------------

def test_driver_source_has_no_plotting_or_fitting():
    """Mirrors the acceptance criterion's own grep:
    ``grep -nE 'render_plots|plotter|fitter|pyhf|matplotlib|mplhep'
    src/fce_web/engine/driver.py``.
    """
    import re
    source = inspect.getsource(driver)
    assert not re.search(r"render_plots|plotter|fitter|pyhf|matplotlib|mplhep", source), (
        "driver.py references plotting or fitting, which B-011 explicitly defers"
    )


def test_run_analysis_signature():
    sig = inspect.signature(driver.run_analysis)
    assert list(sig.parameters)[:2] == ["config", "ctx"], sig


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
