"""Tests for ``fce_web.engine.path_filter`` and ``fce_web.engine.path_final``.

11 tests are ported unchanged from the reference repo's
``tests/test_path_filter.py`` (kskovpen/fce, lines 18,28,38,49,58,66,71,78,88,99,107),
only the import path changed. The rest are new for task B-007: the ``cancel``
seam that replaces ``ui.state.RUN_STATE["stop"]``, the ``ui``-poisoned import
guard, and ``write_final_histograms``'s persistence of every ``outHist.h`` key.
"""
import ast
import inspect
import math
import re
import subprocess
import sys
import threading

import numpy as np
import pytest

from fce_web.engine.path_filter import (
    _delta_r, _P4Proxy, _ArrayProxy, _delta_r_vec,
    make_cache_acc, save_cache, _CACHE_KEYS,
)


class _Obj:
    pass


class _Hist:
    """Minimal stand-in for the reference's ``engine.analytical_loop.hist``.

    ``analytical_loop`` is not vendored until task B-009+, so this test module
    cannot import the real ``hist`` class -- it needs only the two things
    ``fill_histogram_from_cache`` and ``write_final_histograms`` actually touch:
    a ``.h`` dict of ``boost_histogram`` Histograms, and ``.create(bins, min_val,
    max_val)`` to seed the nominal one. Not part of production code; reused
    from ``tests.test_path_filter`` by ``tests/test_systematics.py`` for the
    same reason.
    """

    def __init__(self):
        self.h = {}

    def create(self, bins, min_val, max_val):
        import boost_histogram as bh
        ax = bh.axis.Regular(bins, min_val, max_val)
        self.h["h"] = bh.Histogram(ax)


# ---------------------------------------------------------------------------
# Ported unchanged from the reference (kskovpen/fce tests/test_path_filter.py)
# ---------------------------------------------------------------------------

def test_delta_r_zero_same_direction():
    a = _Obj()
    a.eta = 1.0
    a.phi = 0.5
    b = _Obj()
    b.eta = 1.0
    b.phi = 0.5
    assert _delta_r(a, b) == 0.0


def test_delta_r_known_value():
    a = _Obj()
    a.eta = 0.0
    a.phi = 0.0
    b = _Obj()
    b.eta = 1.0
    b.phi = 0.0
    assert abs(_delta_r(a, b) - 1.0) < 1e-10


def test_delta_r_phi_wrap():
    a = _Obj()
    a.eta = 0.0
    a.phi = math.pi - 0.1
    b = _Obj()
    b.eta = 0.0
    b.phi = -math.pi + 0.1
    dr = _delta_r(a, b)
    assert dr < 0.3


def test_p4proxy_mass():
    e = np.array([10.0])
    px = np.array([0.0])
    py = np.array([0.0])
    pz = np.array([0.0])
    p4 = _P4Proxy(e, px, py, pz)
    assert abs(float(p4.mass[0]) - 10.0) < 1e-8


def test_p4proxy_add():
    p4a = _P4Proxy(np.array([5.0]), np.array([3.0]), np.array([0.0]), np.array([0.0]))
    p4b = _P4Proxy(np.array([5.0]), np.array([3.0]), np.array([0.0]), np.array([0.0]))
    combined = p4a + p4b
    assert float(combined._e[0]) == 10.0
    assert float(combined._px[0]) == 6.0


def test_p4proxy_pt():
    p4 = _P4Proxy(np.array([10.0]), np.array([3.0]), np.array([4.0]), np.array([0.0]))
    assert abs(float(p4.pt[0]) - 5.0) < 1e-8


def test_array_proxy_missing_key_returns_sentinel():
    data = {"weight": np.array([1.0, 2.0])}
    proxy = _ArrayProxy("l1", data)
    vals = proxy.nonexistent
    assert all(v == -999.0 for v in vals)


def test_array_proxy_reads_key():
    data = {
        "weight": np.array([1.0, 2.0]),
        "l1_pt": np.array([30.0, 40.0]),
    }
    proxy = _ArrayProxy("l1", data)
    assert float(proxy.pt[0]) == 30.0
    assert float(proxy.pt[1]) == 40.0


def test_delta_r_vec_zero():
    a = _Obj()
    a.eta = np.array([1.0])
    a.phi = np.array([0.5])
    b = _Obj()
    b.eta = np.array([1.0])
    b.phi = np.array([0.5])
    dr = _delta_r_vec(a, b)
    assert abs(float(dr[0])) < 1e-10


def test_make_cache_acc_has_all_keys():
    acc = make_cache_acc()
    for key in _CACHE_KEYS:
        assert key in acc
        assert hasattr(acc[key], "__len__")  # pre-allocated numpy array
    assert acc["_n"] == 0


def test_save_cache_and_reload(tmp_path):
    from fce_web.engine.path_filter import _append_event, _P
    acc = make_cache_acc()
    null = _P()
    w_obj = _P(pt=0.0, eta=0.0, phi=0.0, e=0.0)
    # Signature: (acc, nlep, nel, nmu, njets, nphot, nbjets, l1, l2, j1, j2, ph1, ph2, met, w)
    # nbjets=1 is inserted after nphot (new column added for b-tagging systematics)
    _append_event(acc, 2, 1, 1, 0, 0, 1, null, null, null, null, null, null, w_obj, 1.5)

    cache_file = str(tmp_path / "test_cache.npz")
    save_cache(cache_file, acc)
    data = np.load(cache_file)
    assert abs(float(data["weight"][0]) - 1.5) < 1e-5
    assert int(data["nlep"][0]) == 2
    assert int(data["nbjets"][0]) == 1


# ---------------------------------------------------------------------------
# Criterion 1: no dependency on ui.state, checked from inside a poisoned process
# ---------------------------------------------------------------------------

def test_path_filter_imports_with_ui_poisoned():
    """Importing path_filter and path_final must succeed even if ``ui``/``ui.state``
    are broken -- proving neither module actually needs them at import time or when
    calling a basic function, not merely that the literal ``from ui.state import ...``
    line is gone.

    Run in a subprocess: poisoning ``sys.modules["ui"] = None`` leaks into the rest of
    the interpreter otherwise, corrupting every other test in this session.
    """
    code = (
        "import sys\n"
        "sys.modules['ui'] = None\n"
        "sys.modules['ui.state'] = None\n"
        "import fce_web.engine.path_filter as pf\n"
        "import fce_web.engine.path_final as pfin\n"
        "acc = pf.make_cache_acc()\n"
        "assert acc['_n'] == 0\n"
        "assert pfin.write_final_histograms is not None\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"subprocess with ui poisoned failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


# ---------------------------------------------------------------------------
# Criterion 7 (PR #12 cycle-2 suggested-major): the module docstring's claimed
# ``eval``/``compile`` line numbers must be this file's real ones, re-derived by
# parsing the file rather than hand-copied -- so a later edit that shifts lines
# breaks this test instead of silently rotting the docstring B-008 will navigate by.
# ---------------------------------------------------------------------------

def _actual_eval_compile_lines(source: str):
    """Return (sorted eval() call lines, sorted compile() call lines) found by ast."""
    tree = ast.parse(source)
    eval_lines, compile_lines = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "eval":
                eval_lines.append(node.lineno)
            elif node.func.id == "compile":
                compile_lines.append(node.lineno)
    return sorted(eval_lines), sorted(compile_lines)


def _claimed_eval_compile_lines(docstring: str):
    """Parse the "this file's lines ..." claim out of the module docstring."""
    eval_m = re.search(
        r"``eval\(\)`` calls \(this file's lines ([0-9, ]+)\)", docstring
    )
    compile_m = re.search(
        r"``compile\(\)`` call \(this file's line ([0-9]+)\)", docstring
    )
    assert eval_m and compile_m, (
        "module docstring no longer states this file's eval/compile line numbers "
        "in the expected format -- update this test's regex to match"
    )
    eval_lines = sorted(int(x) for x in eval_m.group(1).split(","))
    compile_lines = [int(compile_m.group(1))]
    return eval_lines, compile_lines


def test_docstring_eval_compile_line_numbers_match_this_file():
    """The docstring's claimed line numbers for every ``eval``/``compile`` call site
    must equal what ``ast`` actually finds in this file, right now.
    """
    import fce_web.engine.path_filter as pf

    source = inspect.getsource(pf)
    actual_eval, actual_compile = _actual_eval_compile_lines(source)
    claimed_eval, claimed_compile = _claimed_eval_compile_lines(pf.__doc__)

    assert claimed_eval == actual_eval, (
        f"docstring claims eval() at {claimed_eval}, ast finds {actual_eval}"
    )
    assert claimed_compile == actual_compile, (
        f"docstring claims compile() at {claimed_compile}, ast finds {actual_compile}"
    )


def test_docstring_eval_compile_line_check_catches_a_perturbed_number():
    """Mutation test (string substitution on the in-memory docstring, no tracked file
    touched): if one claimed line number is wrong, the comparison used by the test
    above must actually notice.
    """
    import fce_web.engine.path_filter as pf

    source = inspect.getsource(pf)
    actual_eval, actual_compile = _actual_eval_compile_lines(source)

    perturbed_docstring = pf.__doc__.replace(
        f"line {actual_compile[0]})", f"line {actual_compile[0] + 1})"
    )
    assert perturbed_docstring != pf.__doc__, (
        "perturbation did not change the docstring -- fix this test's substitution"
    )

    _claimed_eval, claimed_compile = _claimed_eval_compile_lines(perturbed_docstring)
    assert claimed_compile != actual_compile, (
        "perturbed docstring still matches ast output -- the check is not sensitive"
    )


# ---------------------------------------------------------------------------
# Criterion 3: cancellation
# ---------------------------------------------------------------------------

def _make_syst_cache(tmp_path, n, name="cancel_cache.npz"):
    """Build an n-event cache with fixed njets=2, weight=1.0, no b-jets."""
    from fce_web.engine.path_filter import make_cache_acc, save_cache, _append_event, _P

    acc = make_cache_acc()
    null = _P()
    met_obj = _P(pt=20.0, eta=0.0, phi=0.0, e=20.0)
    for _ in range(n):
        _append_event(acc, 1, 1, 0, 2, 0, 0, null, null, null, null, null, null, met_obj, 1.0)
    cache_file = str(tmp_path / name)
    save_cache(cache_file, acc)
    return cache_file


def test_fill_histogram_from_cache_cancel_mid_loop(tmp_path, monkeypatch):
    """Setting ``cancel`` partway through the event loop stops the fill early.

    n=350 -> _step = max(1, 350 // 100) = 3, so the loop polls ``cancel.is_set()``
    roughly 350 // 3 ~= 117 times, comfortably over the "at least 3 polls" floor --
    that is a fact about how often the *loop* checks ``cancel``, separate from when
    ``cancel`` actually gets set below.

    A real ``threading.Event`` is set by a callback (a monkeypatched wrapper around
    ``_obj_from_cache``, the per-event reconstruction called **six times per event**
    -- once each for l1, l2, j1, j2, ph1, ph2). ``fire_after = n // 3 = 116`` counts
    those *calls*, not events, so the callback actually fires at call 116, i.e. partway
    through event ~19 (116 // 6), not event ~117 -- still comfortably mid-cache (not
    before the first event and not after the last), which is all this test needs: the
    early return is provably mid-loop, not the entry guard exercised by
    ``filter_raw_event_data``.

    The observable is ``"int(njets)"``, not the simpler ``"njets"``: a plain ``njets``
    eval succeeds on the module's vectorized fast path (all of it, in one numpy call,
    with no cancellation check at all -- see the module docstring), so the per-event
    fallback loop this test targets would never run. ``int()`` of a multi-element numpy
    array raises ``TypeError``, which the vectorized try/except swallows and falls
    through to the per-event loop, where ``int()`` of a per-event Python scalar works.
    """
    pytest.importorskip("boost_histogram")
    from fce_web.engine import path_filter as pf

    n = 350
    cache_file = _make_syst_cache(tmp_path, n)

    cancel = threading.Event()
    original = pf._obj_from_cache
    calls = {"n": 0}
    fire_after = n // 3  # comfortably partway through, not the first or last event

    def _counting_obj_from_cache(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == fire_after:
            cancel.set()
        return original(*args, **kwargs)

    monkeypatch.setattr(pf, "_obj_from_cache", _counting_obj_from_cache)

    out_hist = _Hist()
    out_hist.create(bins=10, min_val=0, max_val=5)
    pf.fill_histogram_from_cache(cache_file, out_hist, "int(njets)", with_syst=False, cancel=cancel)

    filled = float(out_hist.h["h"].sum())
    assert cancel.is_set(), "the callback never fired -- test setup is broken"
    assert 0 < filled < n, (
        f"expected an early return with 0 < filled < {n}, got filled={filled}"
    )


def test_fill_histogram_from_cache_cancel_before_first_event_fills_nothing(tmp_path):
    """A ``cancel`` already set before the call returns with the histogram untouched."""
    pytest.importorskip("boost_histogram")
    from fce_web.engine.path_filter import fill_histogram_from_cache

    cache_file = _make_syst_cache(tmp_path, 100, name="precancelled.npz")
    cancel = threading.Event()
    cancel.set()

    out_hist = _Hist()
    out_hist.create(bins=10, min_val=0, max_val=5)
    fill_histogram_from_cache(cache_file, out_hist, "int(njets)", with_syst=False, cancel=cancel)

    assert float(out_hist.h["h"].sum()) == 0.0


def test_fill_histogram_from_cache_no_cancel_runs_to_completion(tmp_path):
    """``cancel=None`` (the default) never interrupts the loop."""
    pytest.importorskip("boost_histogram")
    from fce_web.engine.path_filter import fill_histogram_from_cache

    n = 350
    cache_file = _make_syst_cache(tmp_path, n, name="uncancelled.npz")

    out_hist = _Hist()
    out_hist.create(bins=10, min_val=0, max_val=5)
    fill_histogram_from_cache(cache_file, out_hist, "int(njets)", with_syst=False, cancel=None)

    assert float(out_hist.h["h"].sum()) == float(n)


def test_filter_raw_event_data_cancel_entry_guard_returns_immediately():
    """A ``cancel`` already set is checked as a single entry guard, before any event in
    the basket is touched -- separate from, and not a substitute for, the mid-loop case
    in ``fill_histogram_from_cache`` above.
    """
    from fce_web.engine.path_filter import filter_raw_event_data, make_cache_acc

    cancel = threading.Event()
    cancel.set()
    cache_acc = make_cache_acc()

    arrays = {
        "weight": [1.0, 1.0],
        "MET_pt": [0.0, 0.0],
        "electron_pt": [[30.0], [30.0]],
        "electron_eta": [[0.0], [0.0]],
        "electron_phi": [[0.0], [0.0]],
        "electron_e": [[30.0], [30.0]],
    }
    result = filter_raw_event_data(
        arrays, nev=2, cfg={}, outHist=None, observable_target=None,
        cache_acc=cache_acc, cancel=cancel,
    )

    assert result == ([], [], True)
    assert cache_acc["_n"] == 0


def test_filter_raw_event_data_no_cancel_processes_events():
    """``cancel=None`` lets the basket process normally -- the negative control for the
    entry-guard test above.
    """
    from fce_web.engine.path_filter import filter_raw_event_data, make_cache_acc

    cache_acc = make_cache_acc()
    arrays = {
        "weight": [1.0, 1.0],
        "MET_pt": [0.0, 0.0],
        "electron_pt": [[30.0], [30.0]],
        "electron_eta": [[0.0], [0.0]],
        "electron_phi": [[0.0], [0.0]],
        "electron_e": [[30.0], [30.0]],
    }
    result = filter_raw_event_data(
        arrays, nev=2, cfg={}, outHist=None, observable_target=None,
        cache_acc=cache_acc, cancel=None,
    )

    assert result == ([], [], False)
    assert cache_acc["_n"] == 2


# ---------------------------------------------------------------------------
# Criterion 4: write_final_histograms
# ---------------------------------------------------------------------------

def _build_filled_hist(tmp_path, with_syst, name):
    pytest.importorskip("boost_histogram")
    from fce_web.engine.path_filter import (
        make_cache_acc, save_cache, _append_event, _P, fill_histogram_from_cache,
    )

    acc = make_cache_acc()
    null = _P()
    met_obj = _P(pt=20.0, eta=0.0, phi=0.0, e=20.0)
    for _ in range(5):
        _append_event(acc, 1, 1, 0, 2, 0, 1, null, null, null, null, null, null, met_obj, 1.0)
    cache_file = str(tmp_path / name)
    save_cache(cache_file, acc)

    out_hist = _Hist()
    out_hist.create(bins=10, min_val=0, max_val=5)
    fill_histogram_from_cache(cache_file, out_hist, "njets", with_syst=with_syst)
    return out_hist


def test_write_final_histograms_persists_all_keys_for_mc(tmp_path):
    """MC sample (with_syst=True): every key -- 'h' plus the three SYST_SOURCES UP
    variations -- lands in both the output file and the h5-keyed cache file.
    """
    pytest.importorskip("uproot")
    import uproot
    from fce_web.engine.path_final import write_final_histograms

    hdir = tmp_path
    (hdir / "output").mkdir()
    out_hist = _build_filled_hist(tmp_path, with_syst=True, name="mc_cache.npz")

    write_final_histograms(str(hdir), "X1", "deadbeef", out_hist)

    for path in (hdir / "output" / "X1.root", hdir / "output" / "h5_deadbeef_X1.root"):
        with uproot.open(str(path)) as f:
            keys = {k.split(";")[0] for k in f.keys()}
        assert keys == {"h", "h_jec_up", "h_lep_up", "h_btag_up"}, f"{path}: {keys}"


def test_write_final_histograms_data_sample_only_nominal(tmp_path):
    """data sample (with_syst=False, mirroring analytical_loop's
    with_syst=(s != "data")): only 'h' is written, in both files.
    """
    pytest.importorskip("uproot")
    import uproot
    from fce_web.engine.path_final import write_final_histograms

    hdir = tmp_path
    (hdir / "output").mkdir()
    out_hist = _build_filled_hist(tmp_path, with_syst=False, name="data_cache.npz")

    write_final_histograms(str(hdir), "data", "deadbeef", out_hist)

    for path in (hdir / "output" / "data.root", hdir / "output" / "h5_deadbeef_data.root"):
        with uproot.open(str(path)) as f:
            keys = {k.split(";")[0] for k in f.keys()}
        assert keys == {"h"}, f"{path}: {keys}"
