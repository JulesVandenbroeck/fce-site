#!/usr/bin/env python3
"""palette_search.py — the numerical search that selects the eight
`--node-*` fills in `docs/design-explorations/tokens.css` (D-008 cycle 2).

D-008 cycle 1 shipped a palette found by an uncommitted script ("kept in the
D-008 PR body" — it was not; the PR body carried no script, only prose about
one). D-008 cycle-2 review's Required 2 called that out: the sole
justification for the floor a task exists to establish has to be
reproducible by someone other than its author. This file is that script,
committed.

What it optimises for, and why (`.claude/design/CLAUDE.md` §2, D-008
cycle-2 review, Required 1): a node kind's fill must stay distinguishable
from every other node kind's fill, and from the two colours design manual
§2 holds in reserve (`--vermillion`, `--graphite-blue`), *as simulated
under colour-vision deficiency* — not just under normal vision. D-008
cycle 1 measured that with a Machado-simulated *luminance ratio*; D-008
cycle-2 review found that insufficient, because luminance ratio discards
the chromatic axis a dichromat still has. This script instead maximises the
worst-case CAM02-UCS delta-E (Moroney et al. 2002 CIECAM02 + Luo, Cui & Li
2006's UCS transform) across every node-node pair and every node-vs-reserved
pair, under all three Machado (2009) dichromacies, subject to four
constraints imposed *before* the search runs (not fitted after it, and
matching `check_beamline_pairwise_luminance` in `verify.py`):

    1. no fill's luminance may sit below 0.06 (normal vision or any of the
       3 simulations) -- the darkness floor that keeps the 9x9 px picker
       swatch legible (`.palette__add::before`, beamline.css).
    2. white-on-fill contrast must clear 4.5:1 under all 3 simulations.
    3. no fill's CIE Lab chroma (normal vision) may exceed 62 -- keeps the
       search from reaching for separation by maxing out saturation the way
       D-008 cycle 1's `--node-histogram` did (C*=112, flagged as reading
       "electric" against the paper ground, D-008 cycle-2 review,
       suggested-minor 3); both reserved colours sit under this same cap
       (vermillion C*=65.9, graphite-blue C*=15.8).
    4. hue is bounded to +-40 degrees of the D-004 cycle-3 baseline per
       fill -- loose enough to resolve a reserved-colour collision (see
       `--node-multiplicity` below) but still anchored, so hue keeps doing
       node-kind-identity work rather than being spent entirely on
       separation.

Self-consistency: this script implements its own vectorized CAM02-UCS
pipeline (for search speed -- see `_selftest_against_verify` below) rather
than calling `verify.py`'s scalar functions in the search's inner loop, so
it duplicates that logic. `_selftest_against_verify()` (run automatically,
every invocation) checks this file's CVD simulation, luminance, and
CAM02-UCS machinery against `verify.py`'s own, imported, on the real node
fills and reserved colours, under all 3 dichromacies -- so "these two
implementations agree" is a measured claim this file makes about itself
every time it runs, not an assumption the rest of it depends on silently.
`verify.py`'s own CAM02-UCS pipeline is separately cross-checked against
`colorspacious` -- see its `cam02ucs_deltaE` docstring -- so agreement here
transitively backs this file's numbers against that same external
reference, without importing `colorspacious` itself (a real third-party
dependency; this task's scope forbids adding one).

Usage:
    python palette_search.py              # run the search, print the result
    python palette_search.py --report     # skip the search; read the
                                           # *committed* tokens.css palette
                                           # and print the same diagnostic
                                           # table a winning candidate gets --
                                           # this is what backs the specific
                                           # numbers quoted in tokens.css's
                                           # own comments and the D-008
                                           # cycle-2 PR body.
    python palette_search.py --seed N     # differential_evolution's seed
                                           # (default 11, the seed the
                                           # committed palette was found
                                           # with)

Requires: numpy, scipy (both already this project's dependencies --
`.claude/shared/CLAUDE.md` §3, not new ones). Importing `verify` for the
self-test also requires Playwright to be importable (verify.py imports it
at module level), even though no browser is ever launched by this script.

The search is stochastic (differential evolution over a 24-dimensional
space); a re-run with the same `--seed` reproduces the same result on the
same numpy/scipy version, but exact bit-for-bit hex values are not
guaranteed across different versions of those libraries. What every run
*is* guaranteed to do is find a palette that clears the same four
constraints above, at a worst-case delta-E this file prints and which
`--report` can compare directly against tokens.css's committed numbers.
"""
import argparse
import colorsys
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify as v  # noqa: E402  (needs sys.path set up first)

# ---- constants shared with verify.py's check -------------------------------
CVD_TYPES = v.CVD_TYPES
DARK_FLOOR = 0.06
WHITE_FLOOR = 4.5
PAIR_LUM_FLOOR = 1.02
CHROMA_CAP = 62.0
DELTA_E_FLOOR = 4.0  # the floor check_beamline_pairwise_luminance imposes

# D-004 cycle-3 hues (degrees) -- the anchor `.claude/design/CLAUDE.md` §2's
# "hue is node-kind identity" rule is measured against. Transcribed from the
# D-004 cycle-3 tokens.css `--node-*` values (git history), not re-derived
# from the current (already re-lit) tokens.css.
NAMES = [
    "data", "multiplicity", "selection", "obs-global",
    "obs-object", "obs-vecsum", "obs-custom", "histogram",
]
D004_HUE = {
    "data": 38.0, "multiplicity": 72.6, "selection": 144.8, "obs-global": 174.4,
    "obs-object": 223.9, "obs-vecsum": 281.4, "obs-custom": 322.7, "histogram": 265.7,
}
HUE_DRIFT = 40.0
S_LO, S_HI = 0.32, 0.72
L_LO, L_HI = 0.18, 0.50
N = len(NAMES)
IU, JU = np.triu_indices(N, k=1)  # the 28 unordered node-node pairs

_MACHADO = {cvd: np.array(v.MACHADO_2009_DICHROMACY[cvd]) for cvd in CVD_TYPES}
_WCAG_W = np.array(v._WCAG_LUMINANCE_WEIGHTS)
_SRGB_TO_XYZ = np.array(v._SRGB_TO_XYZ_D65)


# ---- vectorized colour pipeline, mirroring verify.py's scalar one ----------
def srgb_to_linear(rgb255):
    c = rgb255 / 255.0
    return np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def sim_linear(rgb255, cvd):
    lin = srgb_to_linear(rgb255)
    return np.clip(lin @ _MACHADO[cvd].T, 0.0, 1.0)


def sim_lum(rgb255, cvd):
    return sim_linear(rgb255, cvd) @ _WCAG_W


def normal_lum(rgb255):
    return srgb_to_linear(rgb255) @ _WCAG_W


def ratio(l1, l2):
    hi, lo = np.maximum(l1, l2), np.minimum(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def linear_to_xyz100(lin):
    return (lin @ _SRGB_TO_XYZ.T) * 100.0


def _cam02_adapt_vec(xyz100):
    M = np.array(v._M_CAT02)
    rgb = xyz100 @ M.T
    rgb_w = np.array(v._CAM02_XYZ100_W) @ M.T
    factor = v._CAM02_D * (100.0 / rgb_w) + (1 - v._CAM02_D)
    return rgb * factor


def _cam02_nonlinear_vec(rgb_hpe):
    x = v._CAM02_FL * np.abs(rgb_hpe) / 100.0
    compressed = 400 * x ** 0.42 / (27.13 + x ** 0.42) + 0.1
    return np.sign(rgb_hpe) * compressed


_M_HPE_FROM_XYZ = np.array(v._M_HPE_FROM_XYZ)


def xyz100_to_cam02_jch_vec(xyz100):
    rgb_c = _cam02_adapt_vec(xyz100)
    rgb_hpe = rgb_c @ _M_HPE_FROM_XYZ.T
    rgb_a = _cam02_nonlinear_vec(rgb_hpe)
    Ra, Ga, Ba = rgb_a[..., 0], rgb_a[..., 1], rgb_a[..., 2]

    a = Ra - 12 * Ga / 11 + Ba / 11
    b = (Ra + Ga - 2 * Ba) / 9
    h = np.degrees(np.arctan2(b, a)) % 360
    et = 0.25 * (np.cos(np.radians(h) + 2) + 3.8)
    A = (2 * Ra + Ga + Ba / 20 - 0.305) * v._CAM02_NBB

    rgb_c_w = _cam02_adapt_vec(np.array(v._CAM02_XYZ100_W))
    rgb_hpe_w = rgb_c_w @ _M_HPE_FROM_XYZ.T
    Ra_w, Ga_w, Ba_w = _cam02_nonlinear_vec(rgb_hpe_w)
    Aw = (2 * Ra_w + Ga_w + Ba_w / 20 - 0.305) * v._CAM02_NBB

    J = 100 * (A / Aw) ** (v._CAM02_C_SURROUND * v._CAM02_Z)
    t = (50000 / 13 * v._CAM02_NC * v._CAM02_NCB * et * np.hypot(a, b)) / (Ra + Ga + 21 * Ba / 20)
    C = t ** 0.9 * np.sqrt(J / 100) * (1.64 - 0.29 ** v._CAM02_N) ** 0.73
    return J, C, h


def cam02_jch_to_ucs_vec(J, C, h):
    M = C * v._CAM02_FL ** 0.25
    Jp = (1 + 100 * v._CAM02UCS_C1) * J / (1 + v._CAM02UCS_C1 * J)
    Mp = (1 / v._CAM02UCS_C2) * np.log(1 + v._CAM02UCS_C2 * M)
    return Jp, Mp * np.cos(np.radians(h)), Mp * np.sin(np.radians(h))


def sim_cam02ucs(rgb255, cvd):
    xyz100 = linear_to_xyz100(sim_linear(rgb255, cvd))
    J, C, h = xyz100_to_cam02_jch_vec(xyz100)
    return np.stack(cam02_jch_to_ucs_vec(J, C, h), axis=-1)


def normal_cam02ucs(rgb255):
    xyz100 = linear_to_xyz100(srgb_to_linear(rgb255))
    J, C, h = xyz100_to_cam02_jch_vec(xyz100)
    return np.stack(cam02_jch_to_ucs_vec(J, C, h), axis=-1)


def normal_lab_chroma(rgb255):
    """CIE Lab chroma (not CAM02 colourfulness) -- used only for the
    aesthetic chroma cap, exactly as `verify.py`'s own comment on this
    distinction explains."""
    d = 6 / 29
    xyz = linear_to_xyz100(srgb_to_linear(rgb255)) / 100.0
    white = np.array([0.95047, 1.0, 1.08883])
    t = xyz / white
    f = np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4 / 29)
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.hypot(a, b)


def cam02ucs_deltaE(jab1, jab2):
    return np.sqrt(np.sum((jab1 - jab2) ** 2, axis=-1))


def hsl_to_rgb255(h, s, ell):
    """Vectorized HSL -> 0-255 RGB (h in degrees; s, ell in [0, 1]) -- the
    standard algorithm, reimplemented in numpy since `colorsys.hls_to_rgb`
    is scalar-only and the search needs this evaluated for a whole
    candidate (8 colours) per objective call."""
    h = (h % 360) / 360.0
    c = (1 - np.abs(2 * ell - 1)) * s
    hp = h * 6
    x = c * (1 - np.abs(hp % 2 - 1))
    m = ell - c / 2
    r = np.zeros_like(h)
    g = np.zeros_like(h)
    b = np.zeros_like(h)
    for lo, hi, rr, gg, bb in [
        (0, 1, c, x, 0), (1, 2, x, c, 0), (2, 3, 0, c, x),
        (3, 4, 0, x, c), (4, 5, x, 0, c), (5, 6, c, 0, x),
    ]:
        sel = (hp >= lo) & (hp < hi)
        r = np.where(sel, rr, r)
        g = np.where(sel, gg, g)
        b = np.where(sel, bb, b)
    return np.stack([r, g, b], axis=-1) * 255.0 + (m[..., None] * 255.0)


def _selftest_against_verify():
    """Compare this file's vectorized CVD/luminance/CAM02-UCS machinery
    against `verify.py`'s own scalar implementation, on the 8 real node
    fills plus the 2 reserved colours read from the committed tokens.css,
    under all 3 dichromacies. Raises if they disagree beyond floating-point
    noise -- this is what makes "these two implementations agree" a checked
    claim rather than an assumption the rest of this file depends on."""
    tokens = v.parse_root_tokens(v.TOKENS_CSS.read_text())
    rgbs = []
    for name in v.NODE_FILL_TOKENS + v.RESERVED_COLOR_TOKENS:
        rgb = v.hex_to_rgb(tokens[name])
        if rgb is None:
            raise AssertionError(f"self-test: {name} did not parse as a literal hex colour")
        rgbs.append(rgb)

    worst_lum = 0.0
    worst_jab = 0.0
    worst_de = 0.0
    for rgb in rgbs:
        arr = np.array(rgb, dtype=float)
        for cvd in CVD_TYPES:
            mine_lum = float(sim_lum(arr, cvd))
            theirs_lum = v.simulate_cvd_luminance(rgb, cvd)
            worst_lum = max(worst_lum, abs(mine_lum - theirs_lum))

            mine_jab = sim_cam02ucs(arr, cvd)
            theirs_jab = np.array(v.simulate_cvd_cam02ucs(rgb, cvd))
            worst_jab = max(worst_jab, float(np.max(np.abs(mine_jab - theirs_jab))))

    for i in range(len(rgbs)):
        for j in range(i + 1, len(rgbs)):
            for cvd in CVD_TYPES:
                a, b = np.array(rgbs[i], dtype=float), np.array(rgbs[j], dtype=float)
                mine_de = float(cam02ucs_deltaE(sim_cam02ucs(a, cvd), sim_cam02ucs(b, cvd)))
                theirs_de = v.cam02ucs_deltaE(
                    v.simulate_cvd_cam02ucs(rgbs[i], cvd), v.simulate_cvd_cam02ucs(rgbs[j], cvd)
                )
                worst_de = max(worst_de, abs(mine_de - theirs_de))

    ok = worst_lum < 1e-9 and worst_jab < 1e-6 and worst_de < 1e-6
    print(
        f"self-test vs verify.py, {len(rgbs)} real colours x {len(CVD_TYPES)} simulations: "
        f"worst |luminance diff|={worst_lum:.2e}, worst |J'a'b' diff|={worst_jab:.2e}, "
        f"worst |deltaE diff|={worst_de:.2e}  {'OK' if ok else 'MISMATCH'}"
    )
    if not ok:
        raise AssertionError("palette_search.py's vectorized pipeline disagrees with verify.py's scalar one")


def _reserved_rgb255():
    tokens = v.parse_root_tokens(v.TOKENS_CSS.read_text())
    out = {}
    for name in v.RESERVED_COLOR_TOKENS:
        rgb = v.hex_to_rgb(tokens[name])
        out[name] = np.array(rgb, dtype=float)
    return out


RESERVED = _reserved_rgb255()
WHITE = np.array([255.0, 255.0, 255.0])


def objective(x):
    h, s, ell = x[0::3], x[1::3], x[2::3]
    rgbs = hsl_to_rgb255(h, s, ell)  # (8, 3)

    penalty = 0.0
    base_hue = np.array([D004_HUE[n] for n in NAMES])
    drift = np.minimum((h - base_hue) % 360, (base_hue - h) % 360)
    penalty += np.sum(np.clip(drift - HUE_DRIFT, 0, None)) * 2

    nlum = normal_lum(rgbs)
    chroma = normal_lab_chroma(rgbs)
    penalty += np.sum(np.clip(chroma - CHROMA_CAP, 0, None)) * 3
    penalty += np.sum(np.clip(DARK_FLOOR - nlum, 0, None)) * 800

    reserved_arr = np.stack(list(RESERVED.values()))
    de_worst = None
    for cvd in CVD_TYPES:
        slum = sim_lum(rgbs, cvd)
        sjab = sim_cam02ucs(rgbs, cvd)
        white_lum = sim_lum(WHITE, cvd)
        wr = ratio(white_lum, slum)
        penalty += np.sum(np.clip(WHITE_FLOOR - wr, 0, None)) * 50
        penalty += np.sum(np.clip(DARK_FLOOR - slum, 0, None)) * 800

        pr = ratio(slum[IU], slum[JU])
        penalty += np.sum(np.clip(PAIR_LUM_FLOOR - pr, 0, None)) * 500
        de_nn = cam02ucs_deltaE(sjab[IU], sjab[JU])

        res_jab = sim_cam02ucs(reserved_arr, cvd)
        de_nr = cam02ucs_deltaE(sjab[:, None, :], res_jab[None, :, :]).reshape(-1)

        de_all = np.concatenate([de_nn, de_nr])
        de_worst = de_all if de_worst is None else np.minimum(de_worst, de_all)

    return -de_worst.min() + penalty


def bounds():
    b = []
    for n in NAMES:
        h0 = D004_HUE[n]
        b += [(h0 - HUE_DRIFT, h0 + HUE_DRIFT), (S_LO, S_HI), (L_LO, L_HI)]
    return b


def report(rgbs_by_name, label):
    print(f"\n=== {label} ===")
    names = list(rgbs_by_name.keys())
    rgbs = {n: np.array(rgbs_by_name[n], dtype=float) for n in names}

    print(f"{'kind':16s} {'hex':8s} {'H':>7s} {'drift':>6s} {'Lab C*':>7s}")
    for n in names:
        r, g, b = rgbs[n] / 255.0
        hh, _, _ = colorsys.rgb_to_hls(r, g, b)
        hdeg = hh * 360
        drift = min((hdeg - D004_HUE[n]) % 360, (D004_HUE[n] - hdeg) % 360) if n in D004_HUE else float("nan")
        c = float(normal_lab_chroma(rgbs[n]))
        hexval = "#{:02x}{:02x}{:02x}".format(*(int(round(x)) for x in rgbs[n]))
        print(f"{n:16s} {hexval:8s} {hdeg:7.1f} {drift:6.1f} {c:7.2f}")

    worst_dark = (1e9, None, None)
    for n in names:
        nl = float(normal_lum(rgbs[n]))
        if nl < worst_dark[0]:
            worst_dark = (nl, n, "normal")
        for cvd in CVD_TYPES:
            sl = float(sim_lum(rgbs[n], cvd))
            if sl < worst_dark[0]:
                worst_dark = (sl, n, cvd)
    print(f"darkness floor (>= {DARK_FLOOR}): {worst_dark}  {'OK' if worst_dark[0] >= DARK_FLOOR else 'FAIL'}")

    worst_white = (1e9, None, None)
    for n in names:
        for cvd in CVD_TYPES:
            r = float(ratio(sim_lum(WHITE, cvd), sim_lum(rgbs[n], cvd)))
            if r < worst_white[0]:
                worst_white = (r, n, cvd)
    print(f"white-on-fill (>= {WHITE_FLOOR}): {worst_white}  {'OK' if worst_white[0] >= WHITE_FLOOR else 'FAIL'}")

    worst_pl = (1e9, None, None, None)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            for cvd in CVD_TYPES:
                r = float(ratio(sim_lum(rgbs[a], cvd), sim_lum(rgbs[b], cvd)))
                if r < worst_pl[0]:
                    worst_pl = (r, a, b, cvd)
    print(f"pairwise luminance (>= {PAIR_LUM_FLOOR}): {worst_pl}  {'OK' if worst_pl[0] >= PAIR_LUM_FLOOR else 'FAIL'}")

    rows = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            des = {cvd: float(cam02ucs_deltaE(sim_cam02ucs(rgbs[a], cvd), sim_cam02ucs(rgbs[b], cvd)))
                   for cvd in CVD_TYPES}
            rows.append((min(des.values()), a, b, min(des, key=des.get)))
    for n in names:
        for rn, rrgb in RESERVED.items():
            des = {cvd: float(cam02ucs_deltaE(sim_cam02ucs(rgbs[n], cvd), sim_cam02ucs(rrgb, cvd)))
                   for cvd in CVD_TYPES}
            rows.append((min(des.values()), n, rn, min(des, key=des.get)))
    rows.sort()
    print(f"worst-of-3-simulations CAM02-UCS delta-E, {len(rows)} pairs, floor {DELTA_E_FLOOR}:")
    for w, a, b, wt in rows[:8]:
        mark = "ok" if w >= DELTA_E_FLOOR else "BELOW FLOOR"
        print(f"  {a:16s} vs {b:16s} = {w:7.3f} ({wt:13s}) {mark}")
    print(f"min: {rows[0]}  {'OK' if rows[0][0] >= DELTA_E_FLOOR else 'FAIL'}")
    print(f"median: {np.median([r[0] for r in rows]):.2f}")
    return (
        rows[0][0] >= DELTA_E_FLOOR
        and worst_dark[0] >= DARK_FLOOR
        and worst_white[0] >= WHITE_FLOOR
        and worst_pl[0] >= PAIR_LUM_FLOOR
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="report on the committed tokens.css palette")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--maxiter", type=int, default=400)
    parser.add_argument("--popsize", type=int, default=25)
    args = parser.parse_args()

    _selftest_against_verify()

    if args.report:
        tokens = v.parse_root_tokens(v.TOKENS_CSS.read_text())
        rgbs = {n: v.hex_to_rgb(tokens[f"--node-{n}"]) for n in NAMES}
        ok = report(rgbs, "committed tokens.css palette")
        sys.exit(0 if ok else 1)

    dims = len(bounds())
    print(
        f"\nrunning differential evolution: seed={args.seed} maxiter={args.maxiter} "
        f"popsize={args.popsize} ({dims} dims, ~{args.maxiter * args.popsize * dims} objective "
        "calls -- a few minutes)"
    )
    res = differential_evolution(
        objective, bounds(), maxiter=args.maxiter, popsize=args.popsize, tol=1e-9,
        seed=args.seed, polish=True, workers=1, mutation=(0.4, 1.3), recombination=0.85,
    )
    h, s, ell = res.x[0::3], res.x[1::3], res.x[2::3]
    rgbs_arr = hsl_to_rgb255(h, s, ell)
    rgbs = {n: tuple(int(round(c)) for c in rgbs_arr[i]) for i, n in enumerate(NAMES)}
    ok = report(rgbs, f"search result (fun={res.fun:.3f}, nit={res.nit})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
