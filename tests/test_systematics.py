"""Tests for ``fce_web.engine.systematics``.

Ported from the reference repo's ``tests/test_systematics.py`` (kskovpen/fce).
One reference test is dropped:

- ``test_fill_histogram_syst_keys_created`` exercises
  ``engine.path_filter.fill_histogram_from_cache`` and
  ``engine.analytical_loop.hist``, neither of which exists yet in this repo --
  they are vendored by later tasks (B-007 onward). Porting it here would
  require creating modules outside this task's file scope.

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
# nbjets counting semantics
# The rule: nbjets = count of jets with btag score > BTAG_WP (=0.7).
# Tests the documented semantics directly, matching the logic in
# filter_raw_event_data: int(np.count_nonzero(np.asarray(jet_btag[i]) > BTAG_WP))
# ---------------------------------------------------------------------------

def _count_bjets(btags):
    """Mirror the counting logic from filter_raw_event_data."""
    return int(np.count_nonzero(np.asarray(btags) > BTAG_WP))


def test_nbjets_counting_all_below_wp():
    assert _count_bjets([0.1, 0.5, 0.69]) == 0


def test_nbjets_counting_all_above_wp():
    assert _count_bjets([0.8, 0.9, 1.0]) == 3


def test_nbjets_counting_mixed():
    assert _count_bjets([0.65, 0.71, 0.80, 0.60]) == 2


def test_nbjets_counting_exactly_at_wp_not_tagged():
    # Threshold is strictly greater-than (> 0.7), so 0.7 itself is NOT b-tagged.
    assert _count_bjets([0.7]) == 0


def test_nbjets_empty_jet_list():
    assert _count_bjets([]) == 0
