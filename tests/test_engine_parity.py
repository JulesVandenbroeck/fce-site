"""The M2 checkpoint: proves ``fce_web.engine.driver.run_analysis`` reproduces
the reference repo's (``kskovpen/fce``) own histogram output bin-for-bin.

Method (user ruling, 2026-08-20): ``scripts/render_reference.py`` drives the
*reference checkout's own* ``run_physics_loop`` in a subprocess and dumps its
histogram bin edges/contents -- nominal and every ``h_{src}_up`` systematic
variation -- to JSON, committed here as
``tests/fixtures/golden/zpeak-dilepton.json``. This module compares a fresh
run of *our* engine against that committed fixture. **The golden file is
never regenerated inside a test** -- doing so would let the expectation
self-adjust to whatever our engine currently returns, which is exactly the
trap B-011 cycle 1's reviewer found (a check computed from the thing it
checks cannot be moved by a mutation).

Two ROOT files this module reads are written by the *same* vendored
function on both sides (``fce_web.engine.path_final.write_final_histograms``
/ the reference's own, byte-identical ``engine/path_final.py``), so reading
them back the same way on both sides is I/O plumbing, not a physics
computation -- it does not violate the "separate hands" rule, which is about
not sharing the *engine* code being verified, not about not sharing a ROOT
reader.
"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import time
from typing import Dict, Iterator, List, Tuple

import pytest

from fce_web.engine.driver import run_analysis
from fce_web.engine.runconfig import RunConfig
from fce_web.runs import RunContext

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "content", "analyses", "zpeak-dilepton.json")
GOLDEN_PATH = os.path.join(REPO_ROOT, "tests", "fixtures", "golden", "zpeak-dilepton.json")
RENDER_SCRIPT = os.path.join(REPO_ROOT, "scripts", "render_reference.py")

# Both overridable so criterion 5's two skip cases can be driven independently
# without touching the real reference checkout or the real dataset directory.
_REFERENCE_ROOT_ENV = "FCE_PARITY_REFERENCE_ROOT"
_DATASETS_DIR_ENV = "FCE_PARITY_DATASETS_DIR"
_DEFAULT_REFERENCE_ROOT = os.path.expanduser("~/Documents/Phd/teaching/fce-project/fce")
_DEFAULT_DATASETS_DIR = os.path.expanduser("~/.fce/datasets")

# Tolerance is absolute, in bin-content units (weighted event counts, which
# range up to ~2.8e3 for this fixture -- see PR body for the observed
# worst-case). Both sides fill histograms through the identical, unchanged,
# single-threaded per-sample vectorized code path (path_filter.py, vendored
# unchanged in B-007), so no cross-thread summation reordering happens
# within one sample's fill and bit-identical output is the expected common
# case, not the tolerance's target. 1e-6 exists only for double-precision
# (uproot writes TH1D, not TH1F -- see write_final_histograms) round-off
# that is not physically meaningful, e.g. differing BLAS/awkward reduction
# order between two separate processes. It was fixed at this value before
# any comparison was run, not widened after seeing a failure: the observed
# worst-case deviation across every sample/key/bin in this fixture was 0.0.
TOLERANCE = 1e-6


def _reference_root() -> str:
    return os.environ.get(_REFERENCE_ROOT_ENV, _DEFAULT_REFERENCE_ROOT)


def _datasets_dir() -> str:
    return os.environ.get(_DATASETS_DIR_ENV, _DEFAULT_DATASETS_DIR)


def _skip_reason_if_unavailable() -> str:
    """None if both the reference checkout and the datasets are present;
    otherwise a reason naming which is missing and where it was looked for.
    """
    reference_root = _reference_root()
    if not os.path.isdir(os.path.join(reference_root, "engine")):
        return (
            f"reference checkout not found: expected an 'engine/' subdirectory "
            f"under {reference_root!r} (set ${_REFERENCE_ROOT_ENV} to override)"
        )
    datasets_dir = _datasets_dir()
    dataset_leaf = os.path.join(datasets_dir, "IDEA", "91GeV")
    if not os.path.isdir(dataset_leaf):
        return (
            f"datasets not found: expected {dataset_leaf!r} to exist "
            f"(set ${_DATASETS_DIR_ENV} to override {datasets_dir!r})"
        )
    return ""


@pytest.fixture(scope="module")
def _require_reference_and_datasets() -> None:
    reason = _skip_reason_if_unavailable()
    if reason:
        pytest.skip(reason)


@contextlib.contextmanager
def _fce_home_env(path: str) -> Iterator[None]:
    """Set the *real* ``FCE_HOME`` process environment variable for the
    duration of the block, restoring whatever was there before.

    Needed because ``engine/analytical_loop.py:241`` (both ours and the
    reference's) calls ``get_fce_home()`` with **no** ``env`` argument, so it
    always resolves against ``os.environ`` regardless of what a caller passes
    through ``run_analysis(..., env=...)``. See criterion 4 in the PR body.
    """
    previous = os.environ.get("FCE_HOME")
    os.environ["FCE_HOME"] = path
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("FCE_HOME", None)
        else:
            os.environ["FCE_HOME"] = previous


def _link_dataset(fce_home: str, detector: str, energy: str) -> str:
    """Symlink ``<fce_home>/datasets/<detector>/<energy>`` to the real,
    shared dataset directory, without copying the multi-hundred-MB files.
    """
    energy_dir = energy.replace(" ", "")
    src = os.path.join(_datasets_dir(), detector, energy_dir)
    dest_parent = os.path.join(fce_home, "datasets", detector)
    os.makedirs(dest_parent, exist_ok=True)
    dest = os.path.join(dest_parent, energy_dir)
    if not os.path.exists(dest):
        os.symlink(src, dest)
    return dest


def _run_our_engine(fce_home: str) -> None:
    """Run our engine end to end against *fce_home*, an isolated FCE_HOME
    with only the real datasets symlinked in. Raises if the run did not
    actually process data, so a broken run cannot silently pass as "compared
    zero histograms".
    """
    config = RunConfig.from_file(CONFIG_PATH)
    _link_dataset(fce_home, config.detector, config.energy)
    ctx = RunContext(n_workers=4)
    with _fce_home_env(fce_home):
        result = run_analysis(config, ctx, env={"FCE_HOME": fce_home})
    assert result.processed_any, (
        f"our engine did not process any data against {fce_home!r}: {result}"
    )


def _read_our_output(fce_home: str, plot_idx: str, sample: str) -> Dict[str, dict]:
    """Read back ``<fce_home>/output/hist{plot_idx}_{sample}.root`` the same
    way ``scripts/render_reference.py`` reads the reference's own output --
    plain uproot/``to_numpy()``, no engine code involved.
    """
    import uproot

    path = os.path.join(fce_home, "output", f"hist{plot_idx}_{sample}.root")
    with uproot.open(path) as f:
        keys = sorted({k.split(";")[0] for k in f.keys()})
        out = {}
        for key in keys:
            counts, edges = f[key].to_numpy()
            out[key] = {
                "edges": [float(x) for x in edges],
                "counts": [float(x) for x in counts],
            }
        return out


def _load_golden() -> dict:
    with open(GOLDEN_PATH) as f:
        return json.load(f)


def _compare(golden: dict, fce_home: str, tolerance: float) -> Tuple[float, List[str]]:
    """Compare every sample/key/bin in *golden* against a fresh read of
    *fce_home*'s output. Returns ``(worst_abs_deviation, failure_messages)``.
    Each failure message names the histogram key, the sample and the bin
    index -- criterion 3 requires the failing bin to be identifiable, not
    just "a bin differs".
    """
    worst = 0.0
    failures: List[str] = []
    for plot_idx, samples in golden.items():
        for sample, hists in samples.items():
            actual = _read_our_output(fce_home, plot_idx, sample)
            for key, expected in hists.items():
                assert key in actual, f"missing key {key!r} for sample {sample!r} in our output"
                exp_edges = expected["edges"]
                act_edges = actual[key]["edges"]
                assert act_edges == pytest.approx(exp_edges), (
                    f"bin edges differ for sample={sample!r} key={key!r}: "
                    f"golden={exp_edges} ours={act_edges}"
                )
                exp_counts = expected["counts"]
                act_counts = actual[key]["counts"]
                assert len(exp_counts) == len(act_counts), (
                    f"bin count differs for sample={sample!r} key={key!r}"
                )
                for i, (e, a) in enumerate(zip(exp_counts, act_counts)):
                    dev = abs(e - a)
                    if dev > worst:
                        worst = dev
                    if dev > tolerance:
                        failures.append(
                            f"sample={sample!r} key={key!r} bin={i} "
                            f"golden={e!r} ours={a!r} |deviation|={dev!r} > tolerance={tolerance!r}"
                        )
    return worst, failures


# ---------------------------------------------------------------------------
# Fixtures that actually drive the two engines. Module-scoped: both cost
# real wall-clock time (see PR body) and produce output every test in this
# module reads from, never mutated between tests.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def reference_render(tmp_path_factory, _require_reference_and_datasets):
    """Render the reference in a genuine subprocess into its own isolated
    FCE_HOME. Returns ``(subprocess.CompletedProcess, ref_home)``.
    """
    ref_home = str(tmp_path_factory.mktemp("ref_home"))
    out_path = str(tmp_path_factory.mktemp("ref_out") / "golden.json")
    env = dict(os.environ)
    env["FCE_HOME"] = ref_home  # explicit, not merely inherited
    result = subprocess.run(
        [
            sys.executable, RENDER_SCRIPT,
            "--reference-root", _reference_root(),
            "--datasets-dir", _datasets_dir(),
            "--fce-home", ref_home,
            "--config", CONFIG_PATH,
            "--out", out_path,
        ],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, (
        f"render_reference.py failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    return result, ref_home


@pytest.fixture(scope="module")
def isolated_run(tmp_path_factory, _require_reference_and_datasets):
    """Run our own engine into its own isolated FCE_HOME -- distinct from
    ``reference_render``'s -- and return that home's path.
    """
    our_home = str(tmp_path_factory.mktemp("our_home"))
    _run_our_engine(our_home)
    return our_home


# ---------------------------------------------------------------------------
# Criterion 1
# ---------------------------------------------------------------------------

def test_render_reference_leaves_no_ui_module_in_the_test_process(reference_render):
    result, _ref_home = reference_render
    assert result.returncode == 0
    assert "ui" not in sys.modules, "ui leaked into the test process"
    assert "ui.state" not in sys.modules, "ui.state leaked into the test process"


# ---------------------------------------------------------------------------
# Criterion 2
# ---------------------------------------------------------------------------

def test_every_bin_and_every_systematic_variation_matches_within_tolerance(isolated_run):
    golden = _load_golden()
    # Sanity: the golden fixture actually carries the per-source variations,
    # not only the nominal -- otherwise this test would certify nothing about
    # them (the B-009 c1 trap: a check whose run never reaches what it claims
    # to certify).
    all_keys = {k for samples in golden.values() for h in samples.values() for k in h}
    assert {"h_jec_up", "h_lep_up", "h_btag_up"} <= all_keys, (
        f"golden fixture is missing systematic-variation keys: {all_keys}"
    )

    worst, failures = _compare(golden, isolated_run, TOLERANCE)
    print(f"\nparity: worst observed |deviation| across all bins = {worst!r}")
    assert not failures, "\n".join(failures)


# ---------------------------------------------------------------------------
# Criterion 3 -- mutation transcripts as real, permanent tests: a bin
# perturbed beyond tolerance fails naming that bin; one perturbed just under
# tolerance still passes. Both mutate an in-memory copy of the loaded golden
# dict -- nothing tracked is ever touched.
# ---------------------------------------------------------------------------

def _perturbed_golden(delta: float) -> dict:
    golden = _load_golden()
    # tests/fixtures/golden/zpeak-dilepton.json:0/X1/h -- the nominal
    # di-lepton mass histogram for the signal sample, bin 12.
    golden["0"]["X1"]["h"]["counts"][12] += delta
    return golden


def test_perturbing_one_bin_beyond_tolerance_fails_naming_that_bin(isolated_run):
    golden = _perturbed_golden(TOLERANCE * 100)
    worst, failures = _compare(golden, isolated_run, TOLERANCE)
    assert failures, "expected the perturbed bin to be reported as a failure"
    assert len(failures) == 1, failures
    assert "sample='X1'" in failures[0] and "key='h'" in failures[0] and "bin=12" in failures[0], (
        f"failure message does not name the perturbed bin: {failures[0]}"
    )


def test_perturbing_one_bin_just_under_tolerance_still_passes(isolated_run):
    golden = _perturbed_golden(TOLERANCE * 0.5)
    worst, failures = _compare(golden, isolated_run, TOLERANCE)
    assert not failures, failures


# ---------------------------------------------------------------------------
# Criterion 4 -- the circularity guard.
# ---------------------------------------------------------------------------

def test_reference_and_our_run_use_distinct_fce_homes(reference_render, isolated_run):
    _result, ref_home = reference_render
    assert ref_home != isolated_run, (
        "the parity proof's two runs must not share an FCE_HOME -- "
        "see criterion 4"
    )


def test_pointing_both_runs_at_the_same_fce_home_lets_the_second_reuse_the_firsts_cache(
    reference_render,
):
    """Mutation for criterion 4: point our engine at the SAME FCE_HOME the
    reference just rendered into, instead of an isolated one. Because both
    sides compute the identical content-addressed ``h5``/``h5_sel`` digests
    for this fixture (same config), our engine's own ``analytical_loop``
    finds the reference's cache files already on disk
    (``sel_{h5_sel}_{s}.npz`` and ``h5_{h5}_{s}.root``) and copies them
    straight through instead of computing anything -- exactly the danger
    this criterion exists to rule out. Demonstrated by wall-clock: a fresh,
    isolated run of this fixture takes ~30s (see PR body); a run pointed at
    an already-populated home finishes in a small fraction of that, which is
    only explainable by a cache hit, not a genuine independent computation.
    """
    _result, ref_home = reference_render
    t0 = time.time()
    _run_our_engine(ref_home)
    elapsed = time.time() - t0
    # Loose bound (independent of the exact machine): a fresh run in this
    # fixture takes tens of seconds (see PR body); reusing every cache entry
    # finishes in a small fraction of that. 10s is generous headroom above
    # the handful of seconds a pure cache-hit copy actually took when this
    # was measured, while still being far below a genuine fresh run.
    assert elapsed < 10.0, (
        f"expected a same-FCE_HOME run to reuse the reference's cache and finish "
        f"fast; it took {elapsed:.1f}s instead, which would undermine the "
        f"conclusion that the two runs are proven independent -- see criterion 4"
    )


# ---------------------------------------------------------------------------
# Criterion 5 -- named skip reasons. Exercised directly here (not just by
# running the suite with a redirected env var from the shell) so the
# reasoning is captured in the suite itself.
# ---------------------------------------------------------------------------

def test_skip_reason_names_a_missing_reference_checkout(monkeypatch, tmp_path):
    monkeypatch.setenv(_REFERENCE_ROOT_ENV, str(tmp_path / "does-not-exist"))
    reason = _skip_reason_if_unavailable()
    assert "reference checkout not found" in reason
    assert str(tmp_path / "does-not-exist") in reason


def test_skip_reason_names_a_missing_datasets_dir(monkeypatch, tmp_path):
    monkeypatch.setenv(_DATASETS_DIR_ENV, str(tmp_path / "no-datasets-here"))
    reason = _skip_reason_if_unavailable()
    assert "datasets not found" in reason
    assert str(tmp_path / "no-datasets-here") in reason
