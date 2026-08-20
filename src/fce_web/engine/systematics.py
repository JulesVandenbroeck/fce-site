"""Physics-motivated systematic uncertainty constants and helpers.

The arithmetic is vendored unchanged from the reference repo's
``engine/systematics.py`` (kskovpen/fce) -- every constant and every formula
here is bit-identical to the reference. ``typing`` and ``numpy`` are added
for the type hints, and this module had zero module-level mutable state to
begin with, so it needed no decoupling. It is the intended shared source of
truth for uncertainty magnitudes used by the later run-path modules
(``path_filter``, ``fitter``, ``plotter``) vendored in tasks B-007 onward.
"""
from typing import Union

import numpy as np

LUMI_UNC = 0.025       # 2.5% correlated luminosity uncertainty
JEC_PER_JET = 0.015    # 1.5% per jet (Jet Energy Correction)
LEP_PER_EL = 0.01      # 1.0% per electron
LEP_PER_MU = 0.005     # 0.5% per muon
BTAG_PER_BJET = 0.02   # 2.0% per b-tagged jet
BTAG_WP = 0.7          # b-tagging working point (btag score threshold)

# Object/weight-based systematic sources (order defines histogram keys h_{src}_up)
SYST_SOURCES = ("jec", "lep", "btag")

#: A count that may be a plain scalar or a numpy array of per-event counts.
Count = Union[int, float, np.ndarray]


def event_syst_factor(source: str, njets: Count, nel: Count, nmu: Count, nbjets: Count) -> Count:
    """Return the per-event UP weight multiplier for the given systematic source.

    Works on both scalars and numpy arrays (plain arithmetic vectorises).

    Parameters
    ----------
    source : str
        One of 'jec', 'lep', 'btag'.
    njets : int or array-like
        Number of jets in the event.
    nel : int or array-like
        Number of electrons in the event.
    nmu : int or array-like
        Number of muons in the event.
    nbjets : int or array-like
        Number of b-tagged jets in the event (btag score > BTAG_WP).

    Returns
    -------
    float or numpy array
        Multiplicative weight factor for the UP variation (always >= 1.0 for
        typical event multiplicities).
    """
    if source == "jec":
        return 1.0 + JEC_PER_JET * njets
    if source == "lep":
        return 1.0 + LEP_PER_EL * nel + LEP_PER_MU * nmu
    if source == "btag":
        return 1.0 + BTAG_PER_BJET * nbjets
    raise ValueError(f"Unknown systematic source: {source!r}")
