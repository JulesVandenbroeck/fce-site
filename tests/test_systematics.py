"""Tests for ``fce_web.engine.systematics`` and its use in ``fce_web.engine.path_filter``.

Ported from the reference repo's ``tests/test_systematics.py`` (kskovpen/fce).

B-005 dropped ``test_fill_histogram_syst_keys_created`` because it needs
``engine.path_filter`` and ``engine.analytical_loop.hist``, neither of which existed yet
in this repo. ``path_filter`` was vendored by B-007 (this task); ``analytical_loop`` is
still not vendored (later task), so the test is ported using ``tests.test_path_filter._Hist``,
a minimal local stand-in documented there, in place of the real ``hist`` class.

B-005 also flagged that its five ``test_nbjets_*`` tests exercised a *local*
reimplementation of b-jet counting (``_count_bjets`` below, as it stood before B-007)
rather than any production code. B-007 discharges that carry-forward too: the local
reimplementation is removed, and the same five tests now call
``fce_web.engine.path_filter.filter_raw_event_data`` -- the actual per-event basket
filter -- and read the ``nbjets`` column it wrote into a real cache accumulator, so a
break in production b-jet counting fails these tests, not a break in a test-only copy.

Expected numbers are computed from the module's own published constants
(``JEC_PER_JET``, ``LEP_PER_EL``, ``LEP_PER_MU``, ``BTAG_PER_BJET``), not typed
in by hand, so a change to the constants and a change to the formula would
each be caught independently.
"""
import numpy as np
import pytest

from fce_web.engine.systematics import (
    LUMI_UNC,
    JEC_PER_JET,
    LEP_PER_EL,
    LEP_PER_MU,
    BTAG_PER_BJET,
    BTAG_WP,
    SYST_SOURCES,
    event_syst_factor,
)


# ---------------------------------------------------------------------------
# event_syst_factor -- scalar inputs
# ---------------------------------------------------------------------------

def test_jec_factor_scalar():
    """JEC UP = 1 + JEC_PER_JET * njets."""
    factor = event_syst_factor("jec", njets=2, nel=1, nmu=0, nbjets=0)
    assert abs(factor - (1.0 + JEC_PER_JET * 2)) < 1e-10


def test_jec_factor_zero_jets():
    factor = event_syst_factor("jec", njets=0, nel=0, nmu=0, nbjets=0)
    assert factor == 1.0


def test_lep_factor_electrons_only():
    """LEP UP = 1 + LEP_PER_EL * nel + LEP_PER_MU * nmu."""
    factor = event_syst_factor("lep", njets=0, nel=3, nmu=0, nbjets=0)
    assert abs(factor - (1.0 + LEP_PER_EL * 3)) < 1e-10


def test_lep_factor_muons_only():
    factor = event_syst_factor("lep", njets=0, nel=0, nmu=2, nbjets=0)
    assert abs(factor - (1.0 + LEP_PER_MU * 2)) < 1e-10


def test_lep_factor_mixed():
    factor = event_syst_factor("lep", njets=0, nel=1, nmu=1, nbjets=0)
    expected = 1.0 + LEP_PER_EL * 1 + LEP_PER_MU * 1
    assert abs(factor - expected) < 1e-10


def test_btag_factor_scalar():
    """BTAG UP = 1 + BTAG_PER_BJET * nbjets."""
    factor = event_syst_factor("btag", njets=4, nel=0, nmu=0, nbjets=2)
    assert abs(factor - (1.0 + BTAG_PER_BJET * 2)) < 1e-10


def test_btag_factor_zero_bjets():
    factor = event_syst_factor("btag", njets=3, nel=0, nmu=0, nbjets=0)
    assert factor == 1.0


def test_unknown_source_raises():
    with pytest.raises(ValueError):
        event_syst_factor("xyz", njets=1, nel=1, nmu=0, nbjets=0)


# ---------------------------------------------------------------------------
# event_syst_factor -- numpy array inputs (vectorisation)
# ---------------------------------------------------------------------------

def test_jec_factor_array():
    njets = np.array([0, 1, 2, 4])
    factor = event_syst_factor("jec", njets=njets, nel=0, nmu=0, nbjets=0)
    expected = 1.0 + JEC_PER_JET * njets
    np.testing.assert_allclose(factor, expected)


def test_lep_factor_array():
    nel = np.array([0, 1, 2])
    nmu = np.array([1, 0, 1])
    factor = event_syst_factor("lep", njets=0, nel=nel, nmu=nmu, nbjets=0)
    expected = 1.0 + LEP_PER_EL * nel + LEP_PER_MU * nmu
    np.testing.assert_allclose(factor, expected)


def test_btag_factor_array():
    nbjets = np.array([0, 1, 3])
    factor = event_syst_factor("btag", njets=0, nel=0, nmu=0, nbjets=nbjets)
    expected = 1.0 + BTAG_PER_BJET * nbjets
    np.testing.assert_allclose(factor, expected)


def test_factors_always_geq_one_for_nonneg_inputs():
    """For any non-negative object counts all UP factors should be >= 1."""
    for src in SYST_SOURCES:
        f = event_syst_factor(src, njets=3, nel=2, nmu=1, nbjets=1)
        assert f >= 1.0, f"Factor for {src} is {f} < 1"


# ---------------------------------------------------------------------------
# Constant sanity checks
# ---------------------------------------------------------------------------

def test_constants_have_expected_values():
    assert abs(LUMI_UNC - 0.025) < 1e-10
    assert abs(JEC_PER_JET - 0.015) < 1e-10
    assert abs(LEP_PER_EL - 0.01) < 1e-10
    assert abs(LEP_PER_MU - 0.005) < 1e-10
    assert abs(BTAG_PER_BJET - 0.02) < 1e-10
    assert abs(BTAG_WP - 0.7) < 1e-10


def test_syst_sources_tuple():
    assert set(SYST_SOURCES) == {"jec", "lep", "btag"}


# ---------------------------------------------------------------------------
# nbjets counting semantics -- exercised through production code
# The rule: nbjets = count of jets with btag score > BTAG_WP (=0.7).
# These call fce_web.engine.path_filter.filter_raw_event_data (the real per-event
# basket filter) and read the nbjets column it writes into a cache accumulator, so a
# break in production b-jet counting -- not a test-only reimplementation -- fails
# these tests. See the module docstring for why this replaced a local _count_bjets.
# ---------------------------------------------------------------------------

def _run_nbjets_via_filter(btags):
    """Run one single-jet-collection event through filter_raw_event_data and return
    the nbjets value it wrote to the cache accumulator.
    """
    from fce_web.engine.path_filter import filter_raw_event_data, make_cache_acc

    n = len(btags)
    arrays = {
        "weight": [1.0],
        "MET_pt": [0.0],
        "jet_pt": [[30.0] * n],
        "jet_eta": [[0.0] * n],
        "jet_phi": [[0.0] * n],
        "jet_e": [[30.0] * n],
        "jet_btag": [list(btags)],
    }
    cache_acc = make_cache_acc()
    filter_raw_event_data(
        arrays, nev=1, cfg={}, outHist=None, observable_target=None,
        cache_acc=cache_acc,
    )
    assert cache_acc["_n"] == 1, "the event should have passed (no cuts configured)"
    return int(cache_acc["nbjets"][0])


def test_nbjets_counting_all_below_wp():
    assert _run_nbjets_via_filter([0.1, 0.5, 0.69]) == 0


def test_nbjets_counting_all_above_wp():
    assert _run_nbjets_via_filter([0.8, 0.9, 1.0]) == 3


def test_nbjets_counting_mixed():
    assert _run_nbjets_via_filter([0.65, 0.71, 0.80, 0.60]) == 2


def test_nbjets_counting_exactly_at_wp_not_tagged():
    # Threshold is strictly greater-than (> 0.7), so 0.7 itself is NOT b-tagged.
    assert _run_nbjets_via_filter([0.7]) == 0


def test_nbjets_empty_jet_list():
    assert _run_nbjets_via_filter([]) == 0


# ---------------------------------------------------------------------------
# fill_histogram_from_cache: variation template creation
# Ported from the reference (kskovpen/fce tests/test_systematics.py:158), dropped by
# B-005 for lack of engine.path_filter -- now vendored by this task (B-007).
# Requires boost_histogram -- skipped when absent.
# ---------------------------------------------------------------------------

def test_fill_histogram_syst_keys_created(tmp_path):
    """fill_histogram_from_cache with with_syst=True must create h_jec_up,
    h_lep_up, h_btag_up on outHist.h; with_syst=False must not.

    The integral of each UP histogram must be >= the nominal integral because
    all systematic factors are >= 1 for non-negative event multiplicities.
    """
    pytest.importorskip("boost_histogram")

    from fce_web.engine.path_filter import (
        make_cache_acc, save_cache, _append_event, _P,
        fill_histogram_from_cache,
    )
    from tests.test_path_filter import _Hist

    acc = make_cache_acc()
    null = _P()
    met_obj = _P(pt=20.0, eta=0.0, phi=0.0, e=20.0)

    # 5 events: 2 jets, 1 electron, 0 muons, 1 b-jet, weight=1.0
    for _ in range(5):
        _append_event(acc, 1, 1, 0, 2, 0, 1,
                      null, null, null, null, null, null, met_obj, 1.0)

    cache_file = str(tmp_path / "syst_test.npz")
    save_cache(cache_file, acc)

    # --- with_syst=True ---
    h_with = _Hist()
    h_with.create(bins=10, min_val=0, max_val=5)
    fill_histogram_from_cache(cache_file, h_with, "njets", with_syst=True)

    for src in ("jec", "lep", "btag"):
        key = f"h_{src}_up"
        assert key in h_with.h, f"Missing key {key} in h_with.h"

    # Each UP integral must be >= the nominal (all weight factors >= 1)
    nominal_sum = float(h_with.h["h"].sum())
    for src in ("jec", "lep", "btag"):
        up_sum = float(h_with.h[f"h_{src}_up"].sum())
        assert up_sum >= nominal_sum - 1e-6, (
            f"UP sum ({up_sum}) should be >= nominal ({nominal_sum}) for {src}"
        )

    # --- with_syst=False ---
    h_without = _Hist()
    h_without.create(bins=10, min_val=0, max_val=5)
    fill_histogram_from_cache(cache_file, h_without, "njets", with_syst=False)

    for src in ("jec", "lep", "btag"):
        assert f"h_{src}_up" not in h_without.h
