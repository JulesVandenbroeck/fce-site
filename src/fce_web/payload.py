"""Reads a completed run's histogram output back into the ``HISTOGRAM_SCHEMA``
payload (``docs/api.md``, task B-019).

``RunResult`` carries no bin data (``fce_web.runs.RunResult``) -- the engine
stops once it has written ``output/hist{plot_idx}_{sample}.root``
(``fce_web.engine.analytical_loop.py:201``). Nothing before this module read
those files back; this is the missing half of the run -> chart pipe.

The read path mirrors the reference repo's ``engine/plotter.py:51-63``
(not vendored into this repo, per ``docs/api.md``'s citation note): open the
file with ``uproot.open``, index the nominal histogram by its key ``"h"``,
then ``.values()`` for bin contents and ``.axes[0].edges()`` for bin edges.
Systematic variations live in the same file under ``f"h_{src}_up"``
(``fce_web.engine.path_filter``, filled only when a sample was processed
with ``with_syst=True`` -- every sample except ``data``,
``analytical_loop.py:211``) and are read the same way, one key per source in
``fce_web.engine.systematics.SYST_SOURCES``.

This module is a pure read: no HTTP, no module-level mutable state. A
missing or unreadable histogram file raises :class:`PayloadError` rather
than silently producing a half-built payload -- a wrong number reaching a
student is exactly what ``.claude/backend/CLAUDE.md`` says is never
simplified away.
"""
from __future__ import annotations

import os
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import uproot

from fce_web.engine.systematics import LUMI_UNC, SYST_SOURCES


class PayloadError(RuntimeError):
    """A run's ``output/`` directory could not be read into a histogram payload.

    Raised for a missing histogram file, one that fails to open (a
    truncated or corrupt write), one with no nominal ``"h"`` histogram, or
    one whose bin edges disagree with the other samples in the same run.
    """


def _hist_path(hdir: str, plot_idx: int, sample: str) -> str:
    return os.path.join(hdir, "output", f"hist{plot_idx}_{sample}.root")


def _read_key(path: str, key: str) -> Optional[Tuple[List[float], List[float]]]:
    """Read one histogram keyed *key* out of *path*, the way
    ``engine/plotter.py:51-63`` reads the reference's output files.

    Returns ``None`` if *path* opens fine but does not carry *key* -- the
    legitimate "this sample has no variation template for this source"
    case. Raises :class:`PayloadError` if *path* cannot be opened at all
    (missing file, truncated write).
    """
    try:
        with uproot.open(path) as f:
            if key not in f:
                return None
            h = f[key]
            return h.values().tolist(), h.axes[0].edges().tolist()
    except Exception as exc:
        raise PayloadError(f"could not read {key!r} from {path}: {exc}") from exc


def _read_nominal(path: str) -> Tuple[List[float], List[float]]:
    nominal = _read_key(path, "h")
    if nominal is None:
        raise PayloadError(f"{path} has no nominal histogram ('h') -- truncated write?")
    return nominal


def build_histogram_payload(
    hdir: str,
    plot_idx: int,
    mc_samples: Sequence[str],
    meta: Mapping[str, object],
    data_sample: str = "data",
    lumi_unc: float = LUMI_UNC,
) -> Dict[str, object]:
    """Build a dict valid against ``tests.test_api_contract.HISTOGRAM_SCHEMA``
    from the histogram files one ``run_analysis`` call wrote.

    Parameters
    ----------
    hdir : str
        The run's ``FCE_HOME`` -- histograms are read from
        ``{hdir}/output/hist{plot_idx}_{sample}.root``.
    plot_idx : int
        The histogram's ``plot_idx``, matching the ``HistogramConfig`` that
        produced it (``fce_web.engine.runconfig.HistogramConfig.plot_idx``).
    mc_samples : Sequence[str]
        The simulated sample names to stack, e.g. ``("X1", "X2", "X3")``.
        Draw order is preserved.
    meta : Mapping[str, object]
        ``HISTOGRAM_SCHEMA``'s ``meta`` object verbatim (``mission``,
        ``detector``, ``energy``, ``xLabel``, ``processNames``) -- run
        metadata this module has no way to derive from engine output alone,
        supplied by the caller.
    data_sample : str
        The sample name whose nominal histogram becomes the payload's
        top-level ``data`` field. Defaults to ``"data"``.
    lumi_unc : float
        Flat luminosity uncertainty fraction, broadcast to ``lumiUnc``.
        Defaults to ``fce_web.engine.systematics.LUMI_UNC``.

    Raises
    ------
    PayloadError
        If any required histogram file is missing, unreadable, or its bin
        edges disagree with the other samples read for this payload.
    """
    edges: Optional[List[float]] = None
    samples_payload: List[Dict[str, object]] = []
    data_counts: Optional[List[float]] = None

    # F7 (B-019 cycle 3): the data sample is read in the same loop as the mc
    # samples so the bin-edge-agreement guard exists once, not once per read
    # site -- a single HistogramConfig produces one binning for a run, so
    # this can only fire on a malformed output/ directory.
    reads = [(name, False) for name in mc_samples] + [(data_sample, True)]
    for name, is_data in reads:
        path = _hist_path(hdir, plot_idx, name)
        counts, sample_edges = _read_nominal(path)
        if edges is None:
            edges = sample_edges
        elif sample_edges != edges:
            raise PayloadError(f"{path}: bin edges disagree with the other samples in this run")

        if is_data:
            data_counts = counts
            continue

        syst_up: Dict[str, List[float]] = {}
        for src in SYST_SOURCES:
            variation = _read_key(path, f"h_{src}_up")
            if variation is not None:
                syst_up[src] = variation[0]

        samples_payload.append({
            "name": name,
            "counts": counts,
            "weightsSquared": None,
            "systUp": syst_up,
        })

    syst_sources = [
        src for src in SYST_SOURCES
        if any(src in sample["systUp"] for sample in samples_payload)
    ]

    return {
        "meta": dict(meta),
        "edges": edges,
        "lumiUnc": lumi_unc,
        "systSources": syst_sources,
        "samples": samples_payload,
        "data": data_counts,
    }
