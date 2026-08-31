#!/usr/bin/env python3
"""Renders the reference repo's (``kskovpen/fce``) OWN ``run_physics_loop`` and
dumps its histogram output to JSON -- the golden file task B-012 diffs our
decoupled engine (``fce_web.engine.driver.run_analysis``) against.

This script is deliberately the *only* thing in this repository that ever
imports the reference checkout. It is invoked as a subprocess by
``tests/test_engine_parity.py`` (never in-process with pytest -- criterion
1) because importing ``engine.analytical_loop`` there pulls the reference's
``ui``/``ui.state`` package into ``sys.modules`` under bare top-level names,
and ``ui.state`` is exactly the global-mutable-state module
``.claude/shared/CLAUDE.md`` says this project exists to eliminate. Nothing
here imports anything from ``fce_web`` -- the point of a separate script
(user ruling, 2026-08-20) is that the proof and the thing it proves must not
share a hand.

The reference's ``paths.get_fce_home()`` (``paths.py``:13) memoises its
answer in a module-level global the first time it is called, reading
``os.environ["FCE_HOME"]`` at that moment -- and
``engine/analytical_loop.py``:17 calls it at *import time*
(``hdir = get_fce_home()``), so ``FCE_HOME`` must be set in this process's
environment *before* ``engine.analytical_loop`` is imported. ``main()``
below sets it explicitly from the ``--fce-home`` argument rather than
relying on whatever the parent process happened to already export, which is
what makes repeated / concurrent renders into different homes safe.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List


def _discover_samples(dataset_dir: str) -> List[str]:
    """The sample names with a ``.root`` file directly under *dataset_dir*,
    sorted for a deterministic run order. Reimplemented independently of
    ``fce_web.engine.driver._discover_active_samples`` -- this script must
    not import anything from ``fce_web`` (module docstring) -- even though
    the two do the same trivial directory listing.
    """
    if not os.path.isdir(dataset_dir):
        return []
    return sorted(
        entry[: -len(".root")]
        for entry in os.listdir(dataset_dir)
        if entry.endswith(".root")
    )


def _ensure_dataset_link(fce_home: str, real_datasets_dir: str, detector: str, energy: str) -> str:
    """Make ``<fce_home>/datasets/<detector>/<energy>`` resolve to the real,
    shared dataset directory via a symlink, so the reference's own
    ``_find_data_file`` (which looks under ``hdir``) can read the real ROOT
    files while ``<fce_home>/cache`` and ``<fce_home>/output`` -- the
    directories this render actually writes to -- stay private to this
    render. Never copies the (multi-hundred-MB) datasets.
    """
    energy_dir = energy.replace(" ", "")
    src = os.path.join(real_datasets_dir, detector, energy_dir)
    dest_parent = os.path.join(fce_home, "datasets", detector)
    os.makedirs(dest_parent, exist_ok=True)
    dest = os.path.join(dest_parent, energy_dir)
    if not os.path.exists(dest):
        os.symlink(src, dest)
    return dest


def _plot_indices(cfg: dict) -> List[int]:
    """Every ``plot_idx`` this config's histograms will be written under,
    from ``cfg["selections"][*]["histograms"]`` (falling back to the
    top-level ``cfg["histograms"]`` the way ``run_physics_loop`` itself
    does when ``selections`` is empty).
    """
    selections = cfg.get("selections") or []
    histograms = []
    for sel in selections:
        histograms.extend(sel.get("histograms", []))
    if not histograms:
        histograms = cfg.get("histograms", [])
    indices = sorted({h.get("plot_idx", 0) for h in histograms})
    return indices or [0]


def _dump_histograms(fce_home: str, cfg: dict, active_samples: List[str]) -> dict:
    """Read back every ``hist{plot_idx}_{sample}.root`` this render wrote,
    and return ``{plot_idx: {sample: {key: {"edges": [...], "counts": [...]}}}}``.

    ``key`` ranges over whatever ``write_final_histograms``
    (``engine/path_final.py``) actually wrote for that sample -- ``h`` alone
    for ``data`` samples, plus ``h_jec_up``/``h_lep_up``/``h_btag_up`` for
    every simulated sample -- so the per-source systematic variations are
    part of the golden file, not just the nominal histogram.
    """
    import uproot

    result: Dict[str, Dict[str, dict]] = {}
    for plot_idx in _plot_indices(cfg):
        per_sample: Dict[str, dict] = {}
        for sample in active_samples:
            path = os.path.join(fce_home, "output", f"hist{plot_idx}_{sample}.root")
            if not os.path.exists(path):
                continue
            with uproot.open(path) as f:
                keys = sorted({k.split(";")[0] for k in f.keys()})
                per_hist = {}
                for key in keys:
                    counts, edges = f[key].to_numpy()
                    per_hist[key] = {
                        "edges": [float(x) for x in edges],
                        "counts": [float(x) for x in counts],
                    }
                per_sample[sample] = per_hist
        result[str(plot_idx)] = per_sample
    return result


def render(reference_root: str, real_datasets_dir: str, fce_home: str,
           config_path: str, out_path: str) -> None:
    """Drive the reference's own ``run_physics_loop`` against *config_path*,
    writing its histogram output under *fce_home*, then dump every bin edge
    and content -- nominal and every systematic-variation key -- to
    *out_path* as JSON.
    """
    if not os.path.isdir(reference_root):
        raise SystemExit(
            f"reference checkout not found at {reference_root!r} -- cannot render"
        )
    if not os.path.isdir(real_datasets_dir):
        raise SystemExit(
            f"datasets directory not found at {real_datasets_dir!r} -- cannot render"
        )

    # Explicit, not inherited: set *before* the reference is imported, per
    # the module docstring above. Overwrites anything this process happened
    # to already have exported.
    os.environ["FCE_HOME"] = fce_home
    os.makedirs(fce_home, exist_ok=True)

    with open(config_path) as f:
        cfg = json.load(f)

    dataset_dir = _ensure_dataset_link(
        fce_home, real_datasets_dir, cfg["detector"], cfg["energy"],
    )
    active_samples = _discover_samples(dataset_dir)
    if not active_samples:
        raise SystemExit(f"no .root files found under {dataset_dir!r}")

    sys.path.insert(0, reference_root)
    from engine.analytical_loop import run_physics_loop  # the reference's own code

    processed = run_physics_loop(cfg, active_samples, active_samples, cfg["energy"])
    if not processed:
        raise SystemExit(
            "the reference's run_physics_loop reported no processed data "
            f"(active_samples={active_samples!r}, fce_home={fce_home!r})"
        )

    golden = _dump_histograms(fce_home, cfg, active_samples)
    with open(out_path, "w") as f:
        json.dump(golden, f, indent=2, sort_keys=True)
        f.write("\n")


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-root", required=True,
                        help="path to the kskovpen/fce checkout")
    parser.add_argument("--datasets-dir", required=True,
                        help="path to the real <detector>/<energy> ROOT dataset tree, "
                             "e.g. ~/.fce/datasets")
    parser.add_argument("--fce-home", required=True,
                        help="scratch FCE_HOME this render writes cache/output into; "
                             "must be distinct from any other render's")
    parser.add_argument("--config", required=True,
                        help="path to the analysis config JSON")
    parser.add_argument("--out", required=True,
                        help="where to write the golden JSON")
    return parser.parse_args(argv)


def main(argv: List[str] = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    render(
        reference_root=os.path.abspath(os.path.expanduser(args.reference_root)),
        real_datasets_dir=os.path.abspath(os.path.expanduser(args.datasets_dir)),
        fce_home=os.path.abspath(os.path.expanduser(args.fce_home)),
        config_path=os.path.abspath(os.path.expanduser(args.config)),
        out_path=os.path.abspath(os.path.expanduser(args.out)),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
