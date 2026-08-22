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
import shutil
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

# Every non-``data`` sample's per-source variation keys the golden fixture
# must carry -- ``data`` is real pseudo-data, has no simulated systematics,
# and is excluded deliberately (criterion 9), not by omission.
_REQUIRED_VARIATION_KEYS = {"h_jec_up", "h_lep_up", "h_btag_up"}


def _assert_variation_coverage_per_sample(golden: dict) -> None:
    """Every non-``data`` sample in *golden* must carry every per-source
    variation key, checked **per sample** (criterion 9). An aggregated check
    across all samples (the pre-C9 shape) would be satisfied by a single
    sample carrying a key while every other sample's variations went
    uncompared -- weaker than criterion 1's claim that every per-source
    variation of every sample is compared.
    """
    for plot_idx, samples in golden.items():
        for sample, hists in samples.items():
            if sample == "data":
                continue
            missing = _REQUIRED_VARIATION_KEYS - set(hists)
            assert not missing, (
                f"sample={sample!r} (plot_idx={plot_idx!r}) is missing "
                f"systematic-variation keys: {sorted(missing)}"
            )


def test_every_bin_and_every_systematic_variation_matches_within_tolerance(isolated_run):
    golden = _load_golden()
    # Sanity: the golden fixture actually carries the per-source variations,
    # not only the nominal -- otherwise this test would certify nothing about
    # them (the B-009 c1 trap: a check whose run never reaches what it claims
    # to certify). Checked per sample (criterion 9), not aggregated.
    _assert_variation_coverage_per_sample(golden)

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


def _output_fingerprint(fce_home: str) -> Dict[str, Tuple[int, int]]:
    """``{relative_path: (size, mtime_ns)}`` for every file under
    ``<fce_home>/output`` -- used by criterion 8 to prove a probe run left
    ``reference_render``'s own output untouched.
    """
    out_dir = os.path.join(fce_home, "output")
    fingerprint: Dict[str, Tuple[int, int]] = {}
    if not os.path.isdir(out_dir):
        return fingerprint
    for name in sorted(os.listdir(out_dir)):
        full = os.path.join(out_dir, name)
        st = os.stat(full)
        fingerprint[name] = (st.st_size, st.st_mtime_ns)
    return fingerprint


def _copy_fce_home(src: str, dst: str) -> None:
    """Copy an FCE_HOME for the cache-crossing probe, preserving symlinks
    rather than dereferencing them.

    ``shutil.copytree``'s default (``symlinks=False``) walks *through* the
    ``<fce_home>/datasets/<detector>/<energy>`` symlink ``_link_dataset``
    creates and copies the real, shared ROOT tree behind it -- cycle-2
    review's M3, measured at ~336 MB of dataset per probe copy, on top of
    which every ``pytest tests/`` run retains pytest's last three tmp
    sessions. ``symlinks=True`` copies the symlink itself instead. See
    criterion 10.
    """
    shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True)


def _bytes_without_following_symlinks(path: str) -> int:
    """Total size in bytes of every entry under *path*, counting a symlink's
    own (tiny) size rather than descending into whatever it points to. Used
    by criterion 10 to bound the cache-crossing probe's footprint without
    the measurement itself dereferencing the thing it is checking was not
    dereferenced.
    """
    total = os.lstat(path).st_size
    with os.scandir(path) as entries:
        for entry in entries:
            total += os.lstat(entry.path).st_size
            if entry.is_dir(follow_symlinks=False):
                total += _bytes_without_following_symlinks(entry.path)
    return total


def test_pointing_both_runs_at_the_same_fce_home_lets_the_second_reuse_the_firsts_cache(
    reference_render, tmp_path_factory,
):
    """Mutation for criterion 4: point our engine at the SAME FCE_HOME the
    reference just rendered into, instead of an isolated one. Because both
    sides compute the identical content-addressed ``h5``/``h5_sel`` digests
    for this fixture (same config), our engine's own ``analytical_loop``
    finds the reference's cache files already on disk
    (``sel_{h5_sel}_{s}.npz`` and ``h5_{h5}_{s}.root``) and copies them
    straight through instead of computing anything -- exactly the danger
    this criterion exists to rule out. Demonstrated by wall-clock: a fresh,
    isolated run of this fixture takes ~78s (measured -- see PR body), which
    is also the number the 10s bound below is set against; a run pointed at
    an already-populated home finishes in a small fraction of that, which is
    only explainable by a cache hit, not a genuine independent computation.

    Criterion 8: probes a **copy** of ``reference_render``'s FCE_HOME, not
    that fixture's own directory. ``reference_render`` is module-scoped and
    its docstring promises its output is never mutated between tests; probing
    it directly would let ``_run_our_engine`` overwrite
    ``output/hist0_*.root`` in place, corrupting the very files the
    criterion-7 tests read from that same fixture later in the module.
    """
    _result, ref_home = reference_render
    before = _output_fingerprint(ref_home)

    probe_home = str(tmp_path_factory.mktemp("cache_probe_home"))
    _copy_fce_home(ref_home, probe_home)

    t0 = time.time()
    _run_our_engine(probe_home)
    elapsed = time.time() - t0

    after = _output_fingerprint(ref_home)
    assert before == after, (
        "the cache-crossing probe must not mutate reference_render's own "
        "output -- see criterion 8"
    )

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
# Criterion 10 -- the cache-crossing probe's copy must not dereference the
# dataset symlink (cycle-2 review, M3: ``shutil.copytree``'s default,
# ``symlinks=False``, does exactly that). Measured 2026-08-22, with the fix
# (``symlinks=True``, see ``_copy_fce_home``) in place: ``probe_home`` is
# ~24.6 MB. The cap below is set at 60 MB -- comfortable headroom over that,
# and well under the ~376 MB a dereferencing copy produces, so the mutation
# gate that follows actually distinguishes the two rather than passing
# either way.
# ---------------------------------------------------------------------------

_PROBE_FOOTPRINT_CAP_BYTES = 60 * 1024 * 1024


def test_cache_probe_preserves_the_dataset_symlink_and_bounds_its_footprint(
    reference_render, tmp_path_factory,
):
    """Criterion 10, the real (fixed) path: the probe copy keeps the dataset
    entry a symlink, and the copy's total footprint -- measured without
    following symlinks, so the measurement cannot itself launder a
    dereferenced copy back under the cap -- stays under
    ``_PROBE_FOOTPRINT_CAP_BYTES``.
    """
    _result, ref_home = reference_render
    probe_home = str(tmp_path_factory.mktemp("cache_probe_symlink_home"))
    _copy_fce_home(ref_home, probe_home)

    dataset_link = os.path.join(probe_home, "datasets", "IDEA", "91GeV")
    assert os.path.islink(dataset_link), (
        f"expected {dataset_link!r} to still be a symlink after the probe "
        f"copy -- see criterion 10"
    )

    footprint = _bytes_without_following_symlinks(probe_home)
    print(f"\nprobe_home footprint (not following symlinks) = {footprint / 1e6:.1f} MB")
    assert footprint < _PROBE_FOOTPRINT_CAP_BYTES, (
        f"probe_home footprint {footprint / 1e6:.1f} MB exceeds the "
        f"{_PROBE_FOOTPRINT_CAP_BYTES / 1e6:.0f} MB cap -- the dataset symlink "
        f"may have been dereferenced (see criterion 10)"
    )


def test_cache_probe_footprint_check_would_catch_a_dereferencing_copy(tmp_path):
    """Mutation gate for criterion 10, self-contained: build a small
    synthetic FCE_HOME whose ``datasets/IDEA/91GeV`` entry is a symlink to a
    directory holding one file sized just over the footprint cap, then show
    ``_copy_fce_home`` (the fix, ``symlinks=True``) stays under the cap while
    ``shutil.copytree`` with its *default* (``symlinks=False`` -- cycle-2's
    M3, the pre-fix behavior) exceeds it. Deliberately independent of
    ``reference_render`` and the real, shared dataset tree: gating this with
    the real ~336 MB dataset would itself perform, on every suite run, the
    same dereferencing copy criterion 10 exists to rule out.
    """
    real_home = tmp_path / "real_home"
    shared_dataset = tmp_path / "shared_dataset"
    shared_dataset.mkdir()
    big_file = shared_dataset / "big.root"
    oversized = _PROBE_FOOTPRINT_CAP_BYTES + 1024 * 1024
    with open(big_file, "wb") as f:
        f.seek(oversized - 1)
        f.write(b"\0")
    dataset_link = real_home / "datasets" / "IDEA" / "91GeV"
    dataset_link.parent.mkdir(parents=True)
    os.symlink(str(shared_dataset), str(dataset_link))

    preserved_home = tmp_path / "preserved_home"
    _copy_fce_home(str(real_home), str(preserved_home))
    assert os.path.islink(preserved_home / "datasets" / "IDEA" / "91GeV")
    preserved_footprint = _bytes_without_following_symlinks(str(preserved_home))
    assert preserved_footprint < _PROBE_FOOTPRINT_CAP_BYTES, (
        f"the symlink-preserving copy measured {preserved_footprint / 1e6:.1f} "
        f"MB, at or above the {_PROBE_FOOTPRINT_CAP_BYTES / 1e6:.0f} MB cap -- "
        f"the synthetic fixture itself is miscalibrated"
    )

    dereferenced_home = tmp_path / "dereferenced_home"
    shutil.copytree(str(real_home), str(dereferenced_home), dirs_exist_ok=True, symlinks=False)
    assert not os.path.islink(dereferenced_home / "datasets" / "IDEA" / "91GeV")
    dereferenced_footprint = _bytes_without_following_symlinks(str(dereferenced_home))
    assert dereferenced_footprint >= _PROBE_FOOTPRINT_CAP_BYTES, (
        f"expected the pre-fix, dereferencing copy to exceed the "
        f"{_PROBE_FOOTPRINT_CAP_BYTES / 1e6:.0f} MB cap (the mutation "
        f"criterion 10 must catch); got {dereferenced_footprint / 1e6:.1f} MB "
        f"instead"
    )


# ---------------------------------------------------------------------------
# Criterion 5 -- named skip reasons. Exercised directly here (not just by
# running the suite with a redirected env var from the shell) so the
# reasoning is captured in the suite itself.
# ---------------------------------------------------------------------------

def test_skip_reason_names_a_missing_reference_checkout(monkeypatch, tmp_path):
    monkeypatch.setenv(_REFERENCE_ROOT_ENV, str(tmp_path / "does-not-exist"))
    # R2 (cycle 2): the datasets branch must not leak in from whatever the
    # *real* environment or machine happens to have -- give it a datasets
    # dir that unambiguously exists, so this test is reachable regardless of
    # any outer $FCE_PARITY_DATASETS_DIR and regardless of whether the real
    # reference checkout or dataset tree exist on the machine running it.
    datasets_dir = tmp_path / "datasets"
    os.makedirs(datasets_dir / "IDEA" / "91GeV")
    monkeypatch.setenv(_DATASETS_DIR_ENV, str(datasets_dir))
    reason = _skip_reason_if_unavailable()
    assert "reference checkout not found" in reason
    assert str(tmp_path / "does-not-exist") in reason


def test_skip_reason_names_a_missing_datasets_dir(monkeypatch, tmp_path):
    # R2 (cycle 2): mirror image of the test above. Before this fix,
    # `_skip_reason_if_unavailable` checks the reference checkout first and
    # returns early, so on a machine without the real reference checkout
    # (e.g. any CI box, or a dev machine that never cloned kskovpen/fce) this
    # test observed "reference checkout not found" instead of "datasets not
    # found" and failed -- the datasets branch was not independently
    # reachable. Give it a reference checkout that unambiguously exists.
    reference_root = tmp_path / "reference"
    os.makedirs(reference_root / "engine")
    monkeypatch.setenv(_REFERENCE_ROOT_ENV, str(reference_root))
    monkeypatch.setenv(_DATASETS_DIR_ENV, str(tmp_path / "no-datasets-here"))
    reason = _skip_reason_if_unavailable()
    assert "datasets not found" in reason
    assert str(tmp_path / "no-datasets-here") in reason


# ---------------------------------------------------------------------------
# Criterion 7 -- the golden fixture itself must be checked against a fresh
# *reference* render inside the suite, not merely trusted. Before this,
# nothing in the module compared reference_render's own output to the
# committed golden: criterion 2 only compares OUR engine to golden, so a
# golden regenerated from our own engine would leave every existing
# assertion green and the parity proof would compare a number against
# itself -- one step short of circular. The module docstring already claims
# parity "against the reference repo's own histogram output"; this makes the
# suite check what the docstring claims.
#
# `_compare` and `_read_our_output` are pure I/O over whatever FCE_HOME they
# are pointed at (uproot `to_numpy()`, no engine code involved -- see their
# docstrings), so reusing them against `reference_render`'s `ref_home`
# instead of `isolated_run`'s home is exactly "diff a fresh output against
# golden", just aimed at the other side of the proof.
# ---------------------------------------------------------------------------

def test_reference_render_matches_the_committed_golden(reference_render):
    """The reference's OWN fresh output, diffed against the committed golden
    fixture bin-for-bin. This is the comparison that closes the parity
    proof: criterion 2 already proves ours == golden; this proves
    reference == golden; together they establish ours == reference without
    either side of the engine ever computing the other's expectation.
    """
    _result, ref_home = reference_render
    golden = _load_golden()
    worst, failures = _compare(golden, ref_home, TOLERANCE)
    print(f"\nreference-vs-golden: worst observed |deviation| across all bins = {worst!r}")
    assert not failures, "\n".join(failures)


def test_perturbing_one_bin_of_golden_fails_the_reference_comparison_naming_that_bin(
    reference_render,
):
    """Mutation gate for criterion 7, run against `reference_render`
    specifically (not `isolated_run`, which criterion 3's mutation tests
    already cover) -- proves the assertion above actually reaches the
    reference-vs-golden comparison, and is not merely re-exercising the
    ours-vs-golden path under a new name. Same in-memory perturbation
    technique as criterion 3: nothing tracked is ever touched.
    """
    _result, ref_home = reference_render
    golden = _perturbed_golden(TOLERANCE * 100)
    worst, failures = _compare(golden, ref_home, TOLERANCE)
    assert failures, "expected the perturbed bin to be reported as a failure"
    assert len(failures) == 1, failures
    assert "sample='X1'" in failures[0] and "key='h'" in failures[0] and "bin=12" in failures[0], (
        f"failure message does not name the perturbed bin: {failures[0]}"
    )


# ---------------------------------------------------------------------------
# Criterion 9 -- variation-key coverage is checked per sample, not
# aggregated. Mutation gate: remove one variation key from one non-``data``
# sample in an in-memory copy of the golden and show the guard fails naming
# that sample and that key; restore; show green. Nothing tracked is touched.
# ---------------------------------------------------------------------------

def test_variation_coverage_passes_on_the_real_golden():
    golden = _load_golden()
    _assert_variation_coverage_per_sample(golden)  # must not raise


def test_removing_a_variation_key_from_one_sample_fails_naming_that_sample():
    golden = _load_golden()
    # X2, deliberately distinct from criterion 3/7's X1, so the two mutation
    # gates cannot be confused with each other in a failure report.
    sample_to_break = "X2"
    plot_idx = "0"
    assert sample_to_break in golden[plot_idx], (
        f"fixture assumption broken: {sample_to_break!r} not in golden[{plot_idx!r}]"
    )
    del golden[plot_idx][sample_to_break]["h_jec_up"]

    with pytest.raises(AssertionError) as excinfo:
        _assert_variation_coverage_per_sample(golden)
    message = str(excinfo.value)
    assert sample_to_break in message, message
    assert "h_jec_up" in message, message


def test_removing_a_variation_key_from_data_is_not_flagged():
    """``data`` is nominal-only, legitimately -- confirm it is excluded
    deliberately (it has no variation keys to begin with in the real
    fixture) rather than by an accident of iteration order.
    """
    golden = _load_golden()
    assert set(golden["0"]["data"]) == {"h"}, golden["0"]["data"].keys()
    _assert_variation_coverage_per_sample(golden)  # must not raise
