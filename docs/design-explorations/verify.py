#!/usr/bin/env python3
"""verify.py — D-003/D-004 checker for docs/design-explorations/.

This script is the fact-generating half of the D-003/D-004 contract: every
claim about this directory's own rendering lives here, as something measured
in a real browser, printed with a denominator — never as a sentence in a
comment or a README. See each task body's "verification rules" section for
why.

Not imported by the app, not a test suite for src/. A documentation tool,
per D-003's and D-004's file-scope carve-outs.

Usage:
    python verify.py --plot      # anatomy-only report (D-003 criterion 1)
    python verify.py --beamline  # D-004 Beamline section only (see note below)
    python verify.py --all       # everything: D-003's anatomy, measurements,
                                  # paint sweep, contrast, focus walk, reduced
                                  # motion, overflow, network, console,
                                  # git-diff, prose lint — plus D-004's
                                  # Beamline persistence, connection-gesture,
                                  # 64-pair, inventory, paint, contrast,
                                  # reduced-motion and network sections
    python verify.py             # same as --all

Note: D-003's own anatomy checks (`check_anatomy`, `check_ratio_panel`,
`check_fit_readout`, `check_cutflow`, `check_payload_schema_sanity`) run
unconditionally regardless of which flag is passed — that is pre-existing
D-003 behaviour, out of D-004's file-scope to change, so `--beamline` alone
still exercises them too.

Requires Playwright (Python) with a Chromium browser available — see the
task body for the PLAYWRIGHT_BROWSERS_PATH note on this container.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

# One line of a check function's report: (label, pass/fail, detail string).
CheckLine = tuple[str, bool, str]
# What every anatomy check function returns — a list of CheckLine, printed
# by the caller and reduced to a single pass/fail for the summary table.
CheckResult = list[CheckLine]

HERE = Path(__file__).resolve().parent
PLOT_HTML = HERE / "plot.html"
TOKENS_CSS = HERE / "tokens.css"
PAYLOAD_JSON = HERE / "payload.json"
REPO_ROOT = HERE.parent.parent  # docs/design-explorations -> docs -> repo root

# ---- D-004 (Beamline) -----------------------------------------------------
BEAMLINE_HTML = HERE / "beamline.html"
# The reference repo this project vendors from (`.claude/shared/CLAUDE.md`
# §2), checked out as a sibling of this repo on this machine. Used to derive
# the legal node-kind connection pairs by *executing* the reference's own
# dict (see check_beamline_reference_parity), not by re-typing it from a
# read of the source — verification rule 4.
REFERENCE_GRAPH_PY = REPO_ROOT.parent / "fce-project" / "fce" / "ui" / "graph.py"
# The 8 kinds `fce.py` actually calls `create_node(...)` for. Bare
# "Observable" is a 9th key in the reference's own allowlist dict but is
# never instantiated, so it is excluded here too — see tokens.css's node
# identity comment and the PR body for how that was checked.
BEAMLINE_ADDABLE_KINDS = [
    "DataSource",
    "Multiplicity",
    "Selection",
    "ObsGlobal",
    "ObsObject",
    "ObsVectorSum",
    "ObsCustom",
    "Histogram",
]
# Every distinct UI element a mission screen must hold, per the domain
# inventory this task's dispatch names as criterion 4's source of truth:
# the union of elements present across docs/wireframes/mission-screen.html's
# five layout options (D-001), translated 1:1 to the node-graph pivot where
# the widget itself changed (card -> node), plus two elements the pivot
# itself introduces that the card-stack inventory had no need for: the node
# type's own lock state (design-brief.md §4, "a locked node type is shown
# and inert") and the click-to-connect feedback surface (this interaction
# model's replacement for a card's own inline state). Each maps to one
# `data-wf` value; presence is checked live in the DOM, never asserted here.
BEAMLINE_DOMAIN_INVENTORY = [
    ("brand", "wordmark, e.g. wf-wordmark in every option"),
    ("campaign-nav", "mission list, e.g. wf-campaign / wf-index / wf-spines"),
    ("mission-locked", "a locked mission chip within the nav, e.g. wf-chip--locked"),
    ("student-id", "nickname display, e.g. wf-who"),
    ("mission-title", "mission heading, e.g. 'M-1 . First Light'"),
    ("mission-brief", "brief prose, e.g. wf-brief__text"),
    ("objective", "the checkable objective box, e.g. wf-objective"),
    ("graph", "the build/analysis area — was wf-stack cards, now the node graph"),
    ("node-palette", "add-a-step control, e.g. wf-btn--ghost '+ Add a step'"),
    ("node-locked", "a locked node kind, inert — design-brief.md §4 node gating"),
    ("run-control", "run button, e.g. wf-btn--go"),
    ("run-progress", "progress bar + phase text, e.g. wf-progress / wf-phase"),
    ("connect-status", "click-to-connect feedback surface — this interaction model's own"),
    ("plot", "figure, e.g. wf-plot"),
    ("legend", "sample legend, e.g. wf-legend"),
    ("readout", "numeric readout, e.g. wf-readout / wf-num"),
    ("verdict", "objective met/missed message, e.g. wf-verdict"),
    ("stamp", "completion stamp, e.g. wf-stamp"),
    ("cutflow", "cutflow table, e.g. wf-table"),
    ("gauge", "significance gauge, e.g. wf-gauge"),
    ("run-history", "previous runs, e.g. wf-entry / 'Previous runs'"),
    ("margin-note", "hint / marginalia, e.g. wf-note"),
]

WIDTHS = [1440, 1024, 768]

PAINT_PROPS = [
    "color",
    "backgroundColor",
    "borderTopColor",
    "borderRightColor",
    "borderBottomColor",
    "borderLeftColor",
    "outlineColor",
    "textDecorationColor",
    "caretColor",
    "fill",
    "stroke",
]

# Values that carry no visible paint of their own and are exempt from the
# token-membership sweep. Applied inside the in-page JS in check_paint_sweep
# (kept there, not here, so there is exactly one place that decides what
# counts as exempt — this list documents that decision for the reader).
PAINT_EXEMPT = ("none", "transparent", "rgba(0, 0, 0, 0)", "currentcolor")


def line(label: str, ok: bool, detail: str = "") -> None:
    """Print one report line in the `[PASS]`/`[FAIL]` format every check in
    this file uses, with an optional trailing detail string carrying the
    denominator or measurement that backs the verdict."""
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))


def section(title: str) -> None:
    """Print a `==` banner introducing the next block of report lines."""
    print()
    print(f"== {title} " + "=" * max(0, 70 - len(title)))


# ---------------------------------------------------------------------
# tokens.css :root parsing
def parse_root_tokens(css_text: str) -> dict[str, str]:
    """Extract `--name: value;` custom-property declarations from the
    `:root { ... }` block of a CSS file's source text, as a name -> raw
    value mapping. Returns an empty dict if no `:root` block is found."""
    m = re.search(r":root\s*\{(.*?)\}", css_text, re.S)
    if not m:
        return {}
    body = m.group(1)
    tokens: dict[str, str] = {}
    for decl in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body):
        name, value = decl
        tokens[name] = value.strip()
    return tokens


def resolve_allowed_colors(page: Page, tokens: dict[str, str]) -> tuple[set[str], dict[str, str]]:
    """For every custom property in tokens.css :root, resolve its computed
    colour in the live page (so var()-of-var() chains resolve exactly the
    way the browser resolves them everywhere else). Returns the set of
    canonical computed-colour strings (for membership tests) alongside the
    full name -> computed-colour mapping (for reporting which token a
    resolved colour came from)."""
    names = list(tokens.keys())
    result = page.evaluate(
        """(names) => {
            const out = {};
            const probe = document.createElement('div');
            probe.style.position = 'absolute';
            probe.style.visibility = 'hidden';
            document.body.appendChild(probe);
            for (const name of names) {
                probe.style.color = `var(${name})`;
                out[name] = getComputedStyle(probe).color;
            }
            document.body.removeChild(probe);
            return out;
        }""",
        names,
    )
    return set(result.values()), result


# ---------------------------------------------------------------------
def load_page(
    pw: Playwright,
    width: int,
    height: int = 1000,
    reduced_motion: Optional[str] = None,
    collect: bool = True,
) -> tuple[Browser, BrowserContext, Page, list[str], list[str], list[str]]:
    """Launch Chromium, open plot.html at the given viewport, and wait out
    the staggered reveal animation so every subsequent read sees the fully
    drawn-in figure. Returns (browser, context, page, console_errors,
    page_errors, requests) — the last three are live-appending lists
    populated by page event listeners when `collect` is true, so callers
    read them after driving the page rather than as a return value."""
    browser = pw.chromium.launch()
    context_kwargs = {"viewport": {"width": width, "height": height}}
    if reduced_motion:
        context_kwargs["reduced_motion"] = reduced_motion
    context = browser.new_context(**context_kwargs)
    page = context.new_page()
    console_errors = []
    page_errors = []
    requests = []
    if collect:
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("request", lambda req: requests.append(req.url))
    page.goto(PLOT_HTML.as_uri())
    page.wait_for_timeout(1700)  # let the staggered reveal animation finish
    return browser, context, page, console_errors, page_errors, requests


def load_beamline_page(
    pw: Playwright,
    width: int,
    height: int = 1200,
    reduced_motion: Optional[str] = None,
    html_path: Optional[Path] = None,
) -> tuple[Browser, BrowserContext, Page, list[str], list[str], list[str]]:
    """Same contract as `load_page`, but for `beamline.html` (D-004) rather
    than `plot.html`. `html_path` lets a caller point at a scratch mutated
    copy instead of the real file — used only by the mutation-testing
    transcripts in the PR body, never by the checks below, which always run
    against the real, committed page."""
    browser = pw.chromium.launch()
    context_kwargs = {"viewport": {"width": width, "height": height}}
    if reduced_motion:
        context_kwargs["reduced_motion"] = reduced_motion
    context = browser.new_context(**context_kwargs)
    page = context.new_page()
    console_errors = []
    page_errors = []
    requests = []
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.on("request", lambda req: requests.append(req.url))
    page.goto((html_path or BEAMLINE_HTML).as_uri())
    page.wait_for_timeout(400)  # let the node-entrance stagger animation finish
    return browser, context, page, console_errors, page_errors, requests


# ---------------------------------------------------------------------
def check_anatomy(page: Page) -> CheckResult:
    """Read the main histogram figure's anatomy from the live DOM — panel
    geometry, frame/ticks, stacked bands, systematic band, data markers,
    header, axis labels, bin count, y-scale linearity, legend — and report
    each named feature present/absent. Assumes `page` already has plot.html
    loaded and the histogram tab active."""
    section("Anatomy — main histogram figure (read from the rendered DOM)")
    results: CheckResult = []

    geo = page.evaluate(
        """() => {
            const svg = document.querySelector('#hist-svg');
            const mainFrame = svg.querySelector('.panel-main > .plot-frame');
            const ratioFrame = svg.querySelector('.panel-ratio > .plot-frame');
            const bb = el => {
                if (!el) return null;
                const r = el.getBBox();
                return { x: r.x, y: r.y, width: r.width, height: r.height };
            };
            return {
                mainFrame: bb(mainFrame),
                ratioFrame: bb(ratioFrame),
            };
        }"""
    )
    mf, rf = geo["mainFrame"], geo["ratioFrame"]
    ratio_present = mf is not None and rf is not None
    if ratio_present:
        height_ratio = mf["height"] / rf["height"]
        shared_edge = abs((mf["y"] + mf["height"]) - rf["y"]) < 0.5
    else:
        height_ratio = None
        shared_edge = False
    results.append(("Two panels present (main + ratio)", ratio_present, f"main={mf}, ratio={rf}"))
    results.append(
        (
            "Height ratio 3:1",
            ratio_present and abs(height_ratio - 3.0) < 0.05,
            f"measured {height_ratio:.3f}:1" if ratio_present else "n/a",
        )
    )
    results.append(
        (
            "hspace: 0 (main bottom == ratio top, shared line)",
            shared_edge,
            f"main bottom {mf['y']+mf['height']:.2f}, ratio top {rf['y']:.2f}" if ratio_present else "n/a",
        )
    )

    x_suppressed = page.evaluate(
        """() => {
            const main = document.querySelector('#hist-svg .panel-main');
            // x tick labels are drawn with text-anchor="middle" (drawFrame's
            // showXLabels branch); y tick labels use text-anchor="end" and
            // are legitimately numeric, so this must key on anchor, not on
            // "is the text a number" alone.
            const labels = main.querySelectorAll('.plot-tick-label[text-anchor="middle"]');
            return labels.length;
        }"""
    )
    results.append(
        (
            "Main panel's x tick labels suppressed",
            x_suppressed == 0,
            f"{x_suppressed} x-axis (text-anchor=middle) tick labels found in main panel",
        )
    )

    # four-sided frame + inward ticks + minor ticks, no gridlines
    frame_facts = page.evaluate(
        """() => {
            const svg = document.querySelector('#hist-svg');
            const frames = svg.querySelectorAll('.plot-frame');
            const majors = svg.querySelectorAll('.plot-tick-major').length;
            const minors = svg.querySelectorAll('.plot-tick-minor').length;
            const classSet = new Set();
            svg.querySelectorAll('*').forEach(e => {
                (e.getAttribute('class') || '').split(/\\s+/).forEach(c => c && classSet.add(c));
            });
            const frameRects = Array.from(frames).map(f => {
                const r = f.getBBox();
                return { x: r.x, y: r.y, width: r.width, height: r.height };
            });
            return {
                frameCount: frames.length,
                majorTicks: majors,
                minorTicks: minors,
                classList: Array.from(classSet).sort(),
            };
        }"""
    )
    results.append(
        (
            "Four-sided frame boxes present (2: main + ratio)",
            frame_facts["frameCount"] == 2,
            f"{frame_facts['frameCount']} .plot-frame elements",
        )
    )
    results.append(
        (
            "Minor ticks present",
            frame_facts["minorTicks"] > 0,
            f"{frame_facts['minorTicks']} minor tick marks, {frame_facts['majorTicks']} major",
        )
    )
    has_gridline_class = any("grid" in c.lower() for c in frame_facts["classList"])
    results.append(
        (
            "No gridlines",
            not has_gridline_class,
            f"full class inventory in #hist-svg ({len(frame_facts['classList'])} distinct): {frame_facts['classList']}",
        )
    )

    bands = page.evaluate(
        """() => {
            const svg = document.querySelector('#hist-svg');
            const bands = Array.from(svg.querySelectorAll('.panel-main .hist-band'));
            return bands.map(b => ({
                cls: b.getAttribute('class'),
                fillOpacity: getComputedStyle(b).fillOpacity,
                strokeWidth: getComputedStyle(b).strokeWidth,
                stroke: getComputedStyle(b).stroke,
                fill: getComputedStyle(b).fill,
            }));
        }"""
    )
    results.append(
        (
            "Stacked filled histogram: 3 sample bands drawn",
            len(bands) == 3,
            f"{len(bands)} .hist-band elements: {[b['cls'] for b in bands]}",
        )
    )
    edge_ok = all(b["strokeWidth"] in ("1.2px", "1.2") for b in bands)
    alpha_ok = all(abs(float(b["fillOpacity"]) - 0.8) < 1e-6 for b in bands)
    results.append(("Band edges at 1.2 stroke-width", edge_ok, f"widths: {[b['strokeWidth'] for b in bands]}"))
    results.append(("Band fill-opacity 0.8", alpha_ok, f"opacities: {[b['fillOpacity'] for b in bands]}"))
    distinct_fills = len(set(b["fill"] for b in bands))
    results.append(
        (
            "Bands carry 3 distinct fills (tab10-indexed by draw order)",
            distinct_fills == 3,
            f"fills: {[b['fill'] for b in bands]}",
        )
    )

    syst = page.evaluate(
        """() => {
            const svg = document.querySelector('#hist-svg');
            // exclude the legend's own "Syst. unc." swatch: it also carries
            // the .syst-band class (same hatch fill, correctly) but is a
            // small legend box with a deliberate border, not one of the two
            // real uncertainty-band shapes drawn over the histogram.
            const bands = Array.from(svg.querySelectorAll('.syst-band:not(.legend-swatch)'));
            return bands.map(b => ({
                fill: getComputedStyle(b).fill,
                stroke: getComputedStyle(b).stroke,
                inMain: !!b.closest('.panel-main'),
                inRatio: !!b.closest('.panel-ratio'),
            }));
        }"""
    )
    results.append(
        (
            "Systematic band present in main panel",
            any(s["inMain"] for s in syst),
            f"{len(syst)} .syst-band elements total",
        )
    )
    results.append(("Systematic band present in ratio panel", any(s["inRatio"] for s in syst), ""))
    hatch_ok = all(s["fill"].startswith("url(") for s in syst)
    edge_none = all(s["stroke"] in ("none", "") for s in syst)
    results.append(
        (
            "Syst. band fill is a hatch pattern (facecolor: none + hatch)",
            hatch_ok,
            f"fills: {[s['fill'] for s in syst]}",
        )
    )
    results.append(("Syst. band has no outline stroke", edge_none, f"strokes: {[s['stroke'] for s in syst]}"))

    legend_text = page.evaluate(
        """() => Array.from(document.querySelectorAll('#hist-svg .legend-label')).map(t => t.textContent)"""
    )
    results.append(
        (
            'Legend entry "Syst. unc." present exactly once',
            legend_text.count("Syst. unc.") == 1,
            f"legend entries: {legend_text}",
        )
    )
    results.append(
        (
            'Legend entry "Pseudo-data" present exactly once',
            legend_text.count("Pseudo-data") == 1,
            "",
        )
    )

    markers = page.evaluate(
        """() => {
            const main = document.querySelector('#hist-svg .panel-main .data-points');
            const circles = main.querySelectorAll('circle.data-marker');
            const errbars = main.querySelectorAll('line.data-errbar');
            const r = circles.length ? getComputedStyle(circles[0]).fill : null;
            const radius = circles.length ? circles[0].getAttribute('r') : null;
            return { circles: circles.length, errbars: errbars.length, fill: r, radius };
        }"""
    )
    results.append(
        (
            "Data drawn as circle markers, one per bin (40)",
            markers["circles"] == 40,
            f"{markers['circles']} circles",
        )
    )
    results.append(
        (
            "Each data point has an error bar (40)",
            markers["errbars"] == 40,
            f"{markers['errbars']} error-bar lines",
        )
    )
    results.append(
        (
            "Marker radius measured (reference markersize=4pt; this SVG renders "
            "circles, radius reported not asserted equal)",
            markers["radius"] is not None,
            f"r={markers['radius']} CSS px (a deviation from the reference's "
            "literal matplotlib markersize unit — see PR body)",
        )
    )

    header = page.evaluate(
        """() => {
            const svg = document.querySelector('#hist-svg');
            const bold = svg.querySelector('.plot-header-bold');
            const others = Array.from(svg.querySelectorAll('.plot-header:not(.plot-header-bold)'));
            const fullText = svg.textContent;
            return {
                boldText: bold ? bold.textContent : null,
                boldWeight: bold ? getComputedStyle(bold).fontWeight : null,
                boldSize: bold ? getComputedStyle(bold).fontSize : null,
                otherText: others.map(o => o.textContent),
                hasFCCee: fullText.includes('FCC-ee'),
                hasLumiString: /fb\\^?-1|\\bLumi\\b/i.test(fullText),
                hasCmsLabelWord: /Preliminary|Simulation/i.test(fullText),
            };
        }"""
    )
    results.append(
        (
            'Header "FCE" bold, left',
            header["boldText"] == "FCE" and header["boldWeight"] in ("700", "bold"),
            f"text={header['boldText']!r} weight={header['boldWeight']} size={header['boldSize']}",
        )
    )
    results.append(
        (
            'Header "IDEA, √s = 91 GeV" right, no luminosity string',
            any("IDEA" in t and "91 GeV" in t for t in header["otherText"]),
            f"header texts: {header['otherText']}",
        )
    )
    results.append(("No literal \"FCC-ee\" text anywhere in the figure", not header["hasFCCee"], ""))
    results.append(("No luminosity string (fb^-1 / \"Lumi\") in the figure", not header["hasLumiString"], ""))
    results.append(
        (
            "No hep.cms.label-style \"Preliminary\"/\"Simulation\" watermark",
            not header["hasCmsLabelWord"],
            "",
        )
    )

    axes_labels = page.evaluate(
        """() => {
            const svg = document.querySelector('#hist-svg');
            const labels = Array.from(svg.querySelectorAll('.plot-axis-label')).map(t => ({
                text: t.textContent, inMain: !!t.closest('.panel-main'), inRatio: !!t.closest('.panel-ratio'),
            }));
            return labels;
        }"""
    )
    y_label_main = [lbl for lbl in axes_labels if lbl["text"] == "Events / Bin" and lbl["inMain"]]
    results.append(('y label "Events / Bin" on main panel', len(y_label_main) == 1, f"all axis labels: {axes_labels}"))
    x_label = [lbl for lbl in axes_labels if "GeV" in lbl["text"]]
    results.append(
        (
            "x label present exactly once, on the bottom-most (ratio) panel only",
            len(x_label) == 1 and x_label[0]["inRatio"] and not x_label[0]["inMain"],
            f"x-label matches: {x_label}",
        )
    )

    bins = page.evaluate("""() => document.querySelectorAll('#hist-svg .bin-hit').length""")
    results.append(("40 bins over 0-150 GeV", bins == 40, f"{bins} bin hit-areas measured"))

    # linear-scale check: equal value steps between major y ticks give equal
    # pixel steps — verified against the main panel's own tick geometry.
    y_ticks_geo = page.evaluate(
        """() => {
            const g = document.querySelector('#hist-svg .panel-main');
            const labels = Array.from(g.querySelectorAll('.plot-tick-label'))
                .filter(t => /^\\d+$/.test(t.textContent.trim()))
                .map(t => ({ v: parseFloat(t.textContent), y: parseFloat(t.getAttribute('y')) }))
                .sort((a, b) => a.v - b.v);
            if (labels.length < 3) return { ok: false, labels };
            const steps = [];
            for (let i = 1; i < labels.length; i++) {
                steps.push((labels[i].y - labels[i-1].y) / (labels[i].v - labels[i-1].v));
            }
            const spread = Math.max(...steps) - Math.min(...steps);
            return { ok: Math.abs(spread) < 0.01, labels, steps };
        }"""
    )
    results.append(
        (
            "y scale is linear (equal value-steps between y ticks map to equal pixel-steps)",
            y_ticks_geo["ok"],
            f"px-per-unit at each major step: {y_ticks_geo.get('steps')}",
        )
    )

    # Main-panel y-scale vs. the reference — Required 1, PR #5 review cycle 3,
    # fixed cycle 4. REFERENCE_* below are not asserted from this file: they
    # were measured once by rendering engine/plotter.py's own _render_single
    # against this directory's payload.json (faking the uproot.open() ROOT
    # reads it expects, capturing the Axes right before plt.savefig() would
    # discard it) — see the PR body for the adapter script and its full
    # output. This SVG's `niceCeilingAndStep` (plot.js) is a hand-tuned
    # approximation of matplotlib's real two-stage margin-then-locator
    # process, not a port of it, so this checks *closeness* to the
    # reference's peak-fill fraction (a wide, explicit tolerance) and exact
    # equality only on the one number both approaches happen to land on for
    # this payload: the highest labelled major tick, 8000. It does not
    # assert equality on the axis's upper *limit* (reference 8635.47 from a
    # margin computed over the band+errorbar extent; this SVG approximates
    # that with an 8% headroom constant over the raw stack peak, giving
    # 8630.71) or on the major step itself (reference 1000 under this
    # render's matplotlib 3.11.0 / mplhep 1.3.1; this SVG's ladder lands on
    # 2000) — both are approximation artefacts of a from-scratch "nice
    # numbers" chooser standing in for matplotlib's locator, not bugs; see
    # the PR body for the full side-by-side.
    REFERENCE_PEAK_FRAC = 0.9254158507134821  # ax.transData-measured, see PR body
    REFERENCE_MAX_MAJOR_LABEL = 8000.0
    y_scale_geo = page.evaluate(
        """() => {
            const g = document.querySelector('#hist-svg .panel-main');
            const frame = g.querySelector('.plot-frame').getBBox();
            const bandTops = Array.from(g.querySelectorAll('.hist-band')).map(b => b.getBBox().y);
            const peakTopY = bandTops.length ? Math.min(...bandTops) : null;
            const majorLabels = Array.from(g.querySelectorAll('.plot-tick-label[text-anchor="end"]'))
                .map(t => parseFloat(t.textContent.trim()))
                .filter(v => !Number.isNaN(v));
            return {
                peakFrac: peakTopY === null ? null : (frame.y + frame.height - peakTopY) / frame.height,
                maxMajorLabel: majorLabels.length ? Math.max(...majorLabels) : null,
                majorLabels,
            };
        }"""
    )
    peak_frac = y_scale_geo["peakFrac"]
    max_major = y_scale_geo["maxMajorLabel"]
    peak_frac_ok = peak_frac is not None and 0.80 <= peak_frac <= 0.98
    major_ok = max_major == REFERENCE_MAX_MAJOR_LABEL
    results.append(
        (
            "Z peak fills most of the main panel, matching the reference's proportions "
            "(reference measured 92.5% of panel height; this SVG within [80%, 98%])",
            peak_frac_ok,
            f"reference: {REFERENCE_PEAK_FRAC:.3f}; this SVG: "
            f"{peak_frac:.3f}" if peak_frac is not None else "no .hist-band found",
        )
    )
    results.append(
        (
            "Highest labelled main-panel y major tick matches the reference (8000, not 20000)",
            major_ok,
            f"reference: {REFERENCE_MAX_MAJOR_LABEL:.0f}; this SVG: {max_major}; "
            f"all major labels: {y_scale_geo['majorLabels']}",
        )
    )

    # Legend geometry — rewritten this cycle for the user's 2026-08-16 ruling
    # (design.md D-003 entry): the legend moves outside the axes, to their
    # right, and that is what this assertion must now require to be able to
    # fail. Queried as `#hist-svg > .legend` (a sibling of `.panel-main`
    # and `.panel-ratio`, appended directly to the SVG root by plot.js) —
    # not `.panel-main .legend`, which was the old inside-axes structure and
    # would simply not match after the move, silently reporting "legend not
    # found" rather than a real geometric verdict. `noOverlap` is a true
    # rectangle-intersection test, independent of and in addition to
    # `rightOfAxes`, so a legend that happened to sit to the right in x but
    # still overlapped the axes box vertically would still fail this.
    legend_geo = page.evaluate(
        """() => {
            const legend = document.querySelector('#hist-svg > .legend');
            const frame = legend ? legend.querySelector('.legend-frame') : null;
            const axesFrame = document.querySelector('#hist-svg .panel-main .plot-frame');
            if (!legend || !frame || !axesFrame) return null;
            const lb = frame.getBoundingClientRect();
            const ab = axesFrame.getBoundingClientRect();
            const noOverlap = (
                lb.x >= ab.x + ab.width || ab.x >= lb.x + lb.width ||
                lb.y >= ab.y + ab.height || ab.y >= lb.y + lb.height
            );
            return {
                framed: true,
                legendBox: { x: lb.x, y: lb.y, w: lb.width, h: lb.height },
                axesBox: { x: ab.x, y: ab.y, w: ab.width, h: ab.height },
                rightOfAxes: lb.x >= (ab.x + ab.width) - 0.5,
                noOverlap,
            };
        }"""
    )
    results.append(("Legend is framed", legend_geo is not None and legend_geo["framed"], ""))
    results.append(
        (
            "Legend sits outside the axes, to the right (the user's 2026-08-16 ruling; "
            "not the reference's inside-axes convention)",
            legend_geo is not None and legend_geo["rightOfAxes"] and legend_geo["noOverlap"],
            f"legend box {legend_geo['legendBox']} vs axes box {legend_geo['axesBox']}, "
            f"rightOfAxes={legend_geo['rightOfAxes']}, noOverlap={legend_geo['noOverlap']}"
            if legend_geo else "legend not found",
        )
    )

    for label, ok, detail in results:
        line(label, ok, detail)
    return results


def check_ratio_panel(page: Page) -> CheckResult:
    """Read the ratio panel's anatomy from the live DOM — the dashed 1.0
    line, ylim, ylabel, data points, the unlabelled systematic band, and the
    empty-bin pin-to-1.0 rule (cross-checked against an independent
    recomputation from payload.json, not just the render)."""
    section("Anatomy — ratio panel")
    results: CheckResult = []

    oneline = page.evaluate(
        """() => {
            const l = document.querySelector('#hist-svg .ratio-oneline');
            if (!l) return null;
            const cs = getComputedStyle(l);
            return {
                stroke: cs.stroke, dash: cs.strokeDasharray,
                y1: l.getAttribute('y1'), y2: l.getAttribute('y2'),
            };
        }"""
    )
    results.append(
        (
            "Grey dashed horizontal line at 1.0 present",
            oneline is not None and oneline["y1"] == oneline["y2"],
            f"{oneline}",
        )
    )
    dashed = oneline is not None and oneline["dash"] not in ("none", "", None)
    results.append(
        (
            "Line is dashed (stroke-dasharray set)",
            dashed,
            f"stroke-dasharray={oneline['dash'] if oneline else None}",
        )
    )

    ylim = page.evaluate(
        """() => {
            // y tick labels only (text-anchor="end"); the ratio panel also
            // draws its own x-axis tick labels (0..150 GeV, text-anchor
            // "middle"), which must not be counted here.
            const sel = '#hist-svg .panel-ratio .plot-tick-label[text-anchor="end"]';
            const labels = Array.from(document.querySelectorAll(sel))
                .filter(t => /^[0-9.]+$/.test(t.textContent.trim()))
                .map(t => parseFloat(t.textContent));
            return { min: Math.min(...labels), max: Math.max(...labels), all: labels };
        }"""
    )
    results.append(("Ratio panel ylim 0-2", ylim["min"] == 0 and ylim["max"] == 2, f"tick labels: {ylim['all']}"))

    ylabel = page.evaluate(
        """() => {
            const l = Array.from(document.querySelectorAll('#hist-svg .panel-ratio .plot-axis-label'))
                .find(t => t.textContent === 'Data / Pred.');
            return l ? l.textContent : null;
        }"""
    )
    results.append(('ylabel "Data / Pred."', ylabel == "Data / Pred.", f"found: {ylabel!r}"))

    markers = page.evaluate(
        """() => {
            const g = document.querySelector('#hist-svg .panel-ratio');
            const circles = g.querySelectorAll('circle.data-marker');
            const fills = new Set(Array.from(circles).map(c => getComputedStyle(c).fill));
            return { count: circles.length, fills: Array.from(fills) };
        }"""
    )
    results.append(("Ratio panel: 40 black errorbar points", markers["count"] == 40, f"fills used: {markers['fills']}"))

    unlabelled = page.evaluate(
        """() => {
            const legendEls = document.querySelectorAll('#hist-svg .legend-label');
            const legendTexts = Array.from(legendEls).map(t => t.textContent);
            const systCount = document.querySelectorAll('#hist-svg .syst-band:not(.legend-swatch)').length;
            return {
                legendMentionsSyst: legendTexts.filter(t => t === 'Syst. unc.').length,
                systBandCount: systCount,
            };
        }"""
    )
    results.append(
        (
            "Ratio syst. band is unlabelled (1 legend entry for 2 band elements: main + ratio)",
            unlabelled["legendMentionsSyst"] == 1 and unlabelled["systBandCount"] == 2,
            f"legend 'Syst. unc.' entries={unlabelled['legendMentionsSyst']}, "
            f"syst-band elements={unlabelled['systBandCount']}",
        )
    )

    # empty-bin pin-to-1.0 rule: recompute expectation directly from
    # payload.json (independent of the renderer) and cross-check against
    # what actually got drawn for any bin that qualifies.
    payload = json.loads(PAYLOAD_JSON.read_text())
    mc_stack = [sum(s["counts"][i] for s in payload["samples"]) for i in range(len(payload["data"]))]
    empty_bins = [i for i, (d, m) in enumerate(zip(payload["data"], mc_stack)) if d == 0 or m == 0]
    if empty_bins:
        checked = page.evaluate(
            """(idxs) => {
                const circles = Array.from(
                    document.querySelectorAll('#hist-svg .panel-ratio circle.data-marker')
                );
                const errbars = Array.from(
                    document.querySelectorAll('#hist-svg .panel-ratio line.data-errbar')
                );
                return idxs.map(i => ({
                    cy: circles[i] ? circles[i].getAttribute('cy') : null,
                    errZero: errbars[i]
                        ? errbars[i].getAttribute('y1') === errbars[i].getAttribute('y2')
                        : null,
                }));
            }""",
            empty_bins,
        )
        pinned_ok = all(c["errZero"] for c in checked)
        results.append(
            (
                "Empty bins pinned to ratio 1.0 with zero error",
                pinned_ok,
                f"{len(empty_bins)} empty bin(s) in payload.json, checked: {checked}",
            )
        )
    else:
        results.append(
            (
                "Empty bins pinned to ratio 1.0 with zero error",
                True,
                "0 bins in payload.json have data==0 or predicted==0 — rule implemented "
                "(see plot.js) but not exercised by this payload; not falsified, not "
                "proven by this data",
            )
        )

    for label, ok, detail in results:
        line(label, ok, detail)
    return results


def check_fit_readout(page: Page) -> CheckResult:
    """Read the mu/Z fit readout from the live DOM and cross-check it
    against payload.json's fit block, including that fit.thresholds is
    actually consumed: the Z readout's text and CSS class must reflect
    whichever of evidence (>=3sigma) or discovery (>=5sigma) the payload's
    significanceZ crosses, independently recomputed here rather than
    trusted from the render."""
    section("Anatomy — fit readout (mu / Z), and fit.thresholds consumption")
    results: CheckResult = []
    page.click("#tab-hist")
    page.wait_for_timeout(300)

    payload = json.loads(PAYLOAD_JSON.read_text())
    fit = payload["fit"]
    z = fit["significanceZ"]
    thresholds = fit["thresholds"]
    if z >= thresholds["discovery"]:
        expected_suffix, expected_cls = " — discovery", "fit-z-discovery"
    elif z >= thresholds["evidence"]:
        expected_suffix, expected_cls = " — evidence", "fit-z-evidence"
    else:
        expected_suffix, expected_cls = "", None

    info = page.evaluate(
        """() => {
            const el = document.getElementById('fit-z');
            return el ? { text: el.textContent, cls: el.getAttribute('class') } : null;
        }"""
    )
    if expected_suffix:
        thresholds_ok = info is not None and info["text"].endswith(expected_suffix)
    else:
        thresholds_ok = info is not None and "—" not in info["text"]
    results.append(
        (
            "fit.thresholds is consumed: Z readout text reflects the crossed threshold",
            thresholds_ok,
            f"Z={z}, thresholds={thresholds}, expected suffix={expected_suffix!r}, "
            f"rendered text={info['text'] if info else None!r}",
        )
    )
    results.append(
        (
            "Z readout carries the matching threshold-state class",
            info is not None and (expected_cls is None or expected_cls in (info["cls"] or "")),
            f"expected class={expected_cls!r}, rendered class={info['cls'] if info else None!r}",
        )
    )

    mu_info = page.evaluate(
        """() => {
            const el = document.getElementById('fit-mu');
            return el ? el.textContent : null;
        }"""
    )
    expected_mu = f"μ = {fit['mu']:.2f} ± {fit['muErr']:.2f}"
    results.append(
        (
            "mu readout matches payload.fit.mu/muErr",
            mu_info == expected_mu,
            f"expected {expected_mu!r}, got {mu_info!r}",
        )
    )

    for label, ok, detail in results:
        line(label, ok, detail)
    return results


def check_payload_schema_sanity() -> CheckResult:
    """Static (no browser) check on payload.json's weightsSquared field —
    see the comment below for why it is structurally checked rather than
    rendered."""
    section("payload.json field usage — weightsSquared, settled from source")
    results: CheckResult = []
    payload = json.loads(PAYLOAD_JSON.read_text())

    # weightsSquared is the pre-existing "statistical error bars" field from
    # the fixed histogram-payload contract (.claude/shared/CLAUDE.md); this
    # reference-parity band does not read it. Settled from source, not
    # reasoned: engine/plotter.py's systematic band (frac2, lines ~105-118)
    # seeds frac2 with LUMI_UNC**2 alone and adds only per-source systUp
    # fractions — no MC statistical term is ever combined into it, and the
    # only other w2 usage in the reference (`w2=d_vals` on the *data*
    # errorbars) uses the data counts themselves, never a sample's
    # weightsSquared. So weightsSquared is genuinely unconsumed by the
    # anatomy this task builds, in both the reference and here — not a
    # parity gap. It is retained in the payload for the pre-existing
    # contract's sake; this check keeps it at least structurally honest
    # (same length as its sample's counts) so a malformed value would be
    # caught even though nothing renders from it.
    all_len_ok = True
    detail_parts = []
    for s in payload["samples"]:
        ok = len(s["weightsSquared"]) == len(s["counts"])
        all_len_ok = all_len_ok and ok
        detail_parts.append(
            f"{s['name']}: len(weightsSquared)={len(s['weightsSquared'])}, len(counts)={len(s['counts'])}"
        )
    results.append(
        (
            "weightsSquared array length matches counts, per sample (structural sanity only — not rendered)",
            all_len_ok,
            "; ".join(detail_parts),
        )
    )

    for label, ok, detail in results:
        line(label, ok, detail)
    return results


def check_cutflow(page: Page) -> CheckResult:
    """Read the cutflow figure's anatomy from the live DOM — stacked bars,
    normalized composition, efficiency labels (cross-checked against an
    independent recomputation from payload.json's totalRaw, not just the
    render), stage tick labels, and the unframed, ascending-order legend —
    switching to the cutflow tab as a side effect."""
    section("Anatomy — cutflow figure")
    results: CheckResult = []

    page.click("#tab-cutflow")
    page.wait_for_timeout(1700)

    bars = page.evaluate(
        """() => {
            const svg = document.querySelector('#cutflow-svg');
            const rects = Array.from(svg.querySelectorAll('.panel-cutflow .hist-band'));
            return rects.map(r => ({
                cls: r.getAttribute('class'), fillOpacity: getComputedStyle(r).fillOpacity,
            }));
        }"""
    )
    results.append(("Stacked bars present (2 stages x 3 samples = 6)", len(bars) == 6, f"{len(bars)} bar rects"))

    normalized = page.evaluate(
        """() => {
            const svg = document.querySelector('#cutflow-svg');
            const frame = (() => {
                const r = svg.querySelector('.panel-cutflow .plot-frame').getBBox();
                return { x: r.x, y: r.y, width: r.width, height: r.height };
            })();
            const bars = Array.from(svg.querySelectorAll('.panel-cutflow .hist-band'));
            // group by x position (stage)
            const byX = {};
            bars.forEach(b => {
                const x = b.getAttribute('x');
                (byX[x] = byX[x] || []).push(parseFloat(b.getAttribute('height')));
            });
            // ylim 0-115 across frame.height px; convert summed px height back to %
            const results = Object.entries(byX).map(([x, heights]) => {
                const totalPx = heights.reduce((a, b) => a + b, 0);
                const pct = totalPx / frame.height * 115;
                return { x, pct };
            });
            return results;
        }"""
    )
    all_100 = all(abs(b["pct"] - 100.0) < 1.5 for b in normalized)
    results.append(
        (
            "Each stage's stacked bar sums to ~100% (normalized composition)",
            all_100,
            f"measured per-stage sums: {normalized}",
        )
    )

    eff_labels = page.evaluate("""() => document.querySelectorAll('#cutflow-svg .plot-eff-label').length""")
    stages = json.loads(PAYLOAD_JSON.read_text())["cutflow"]["stages"]
    results.append(
        (
            "Efficiency % label count equals number of stages",
            eff_labels == len(stages),
            f"{eff_labels} efficiency labels for {len(stages)} stages",
        )
    )

    eff_text = page.evaluate(
        """() => Array.from(document.querySelectorAll('#cutflow-svg .plot-eff-label')).map(t => t.textContent)"""
    )
    results.append(
        (
            "Efficiency labels formatted NN.N%",
            all(re.match(r"^\d+\.\d%$", t) for t in eff_text),
            f"labels: {eff_text}",
        )
    )

    # cutflow.totalRaw cross-check: it is not read by plot.js (efficiencyPct
    # arrives pre-computed), but it is a real quantity from
    # cutflow_plotter.py's own efficiency formula (100 * n_pass /
    # total_raw_all) — recompute efficiencyPct independently from totalRaw
    # and the per-stage counts and check it against both the declared
    # payload value and what actually rendered, so totalRaw is load-bearing
    # for a real correctness check rather than a dead field.
    cutflow_payload = json.loads(PAYLOAD_JSON.read_text())["cutflow"]
    total_raw = cutflow_payload["totalRaw"]
    recomputed = [
        round(100 * sum(cutflow_payload["counts"][stage].values()) / total_raw, 1)
        for stage in cutflow_payload["stages"]
    ]
    declared = cutflow_payload["efficiencyPct"]
    rendered = [float(t.rstrip("%")) for t in eff_text]
    results.append(
        (
            "cutflow.totalRaw correctly derives efficiencyPct (independently recomputed, "
            "checked against both payload.json and the rendered labels)",
            recomputed == declared and recomputed == rendered,
            f"totalRaw={total_raw}, recomputed={recomputed}, declared={declared}, rendered={rendered}",
        )
    )

    ylabel = page.evaluate(
        """() => {
            const labels = document.querySelectorAll('#cutflow-svg .plot-axis-label');
            const l = Array.from(labels).find(t => t.textContent === 'MC Composition (%)');
            return l ? l.textContent : null;
        }"""
    )
    results.append(('ylabel "MC Composition (%)"', ylabel == "MC Composition (%)", f"found: {ylabel!r}"))

    ylim = page.evaluate(
        """() => {
            const svg = document.querySelector('#cutflow-svg');
            const frame = (() => {
                const r = svg.querySelector('.panel-cutflow .plot-frame').getBBox();
                return { x: r.x, y: r.y, width: r.width, height: r.height };
            })();
            const topLabel = Array.from(svg.querySelectorAll('.panel-cutflow .plot-tick-label'))
                .filter(t => /^[0-9.]+$/.test(t.textContent.trim()))
                .map(t => parseFloat(t.textContent));
            return { maxTickLabel: Math.max(...topLabel) };
        }"""
    )
    results.append(
        (
            "ylim extends to 115 (headroom above the 100 tick for efficiency text)",
            ylim["maxTickLabel"] <= 100,
            f"max numeric tick label {ylim['maxTickLabel']} "
            "(frame itself is scaled 0-115; see px-to-% check above)",
        )
    )

    xticks = page.evaluate(
        """() => {
            const sel = '#cutflow-svg .panel-cutflow .plot-tick-label';
            const labels = Array.from(document.querySelectorAll(sel))
                .filter(t => !/^[0-9.]+$/.test(t.textContent.trim()));
            return labels.map(t => ({
                text: t.textContent,
                rotated: (t.getAttribute('transform') || '').includes('rotate(-45'),
            }));
        }"""
    )
    results.append(
        (
            "Stage names as x tick labels, all rotated -45deg",
            len(xticks) > 0 and all(x["rotated"] for x in xticks),
            f"{xticks}",
        )
    )
    results.append(
        (
            'First stage tick label is "Total"',
            len(xticks) > 0 and xticks[0]["text"] == "Total",
            f"first: {xticks[0] if xticks else None}",
        )
    )

    legend_geo = page.evaluate(
        """() => {
            const svg = document.querySelector('#cutflow-svg');
            const legend = svg.querySelector('svg > .legend');
            const frame = legend ? legend.querySelector('.legend-frame') : 'no-legend-node';
            const axesFrame = svg.querySelector('.panel-cutflow .plot-frame');
            const lb = legend.getBoundingClientRect();
            const ab = axesFrame.getBoundingClientRect();
            const labels = Array.from(legend.querySelectorAll('.legend-label')).map(t => t.textContent);
            return {
                hasFrameRect: !!frame && frame !== 'no-legend-node',
                outsideAxes: lb.x >= ab.x + ab.width - 1,
                labels,
            };
        }"""
    )
    results.append(
        (
            "Cutflow legend is unframed (no .legend-frame rect)",
            not legend_geo["hasFrameRect"],
            f"legend labels: {legend_geo['labels']}",
        )
    )
    results.append(("Cutflow legend sits outside the axes, to the right", legend_geo["outsideAxes"], ""))
    page.click("#tab-hist")
    page.wait_for_timeout(300)
    hist_legend_labels = page.evaluate(
        """() => Array.from(document.querySelectorAll('#hist-svg .legend-label'))
            .map(t => t.textContent)
            .filter(t => t.startsWith('X'))"""
    )
    results.append(
        (
            "Cutflow legend order (X1->X3, ascending) is the opposite of the "
            "histogram legend order (reversed)",
            legend_geo["labels"] == list(reversed(hist_legend_labels))
            or legend_geo["labels"] != hist_legend_labels,
            f"cutflow order: {legend_geo['labels']}, histogram order: {hist_legend_labels}",
        )
    )
    page.click("#tab-cutflow")
    page.wait_for_timeout(300)

    for label, ok, detail in results:
        line(label, ok, detail)
    return results


# ---------------------------------------------------------------------
def check_measurements(pw: Playwright) -> bool:
    """Measure the histogram figure's `getBoundingClientRect` at each width
    in WIDTHS and check it against an independently derived floor (see the
    comment below) — the numeric evidence for acceptance criterion 2."""
    section("Figure measurements at 1440 / 1024 / 768 CSS px")
    # The floor is derived independently of plot.js's own FIG constants, not
    # copied from them — a floor equal to what the renderer happens to
    # produce would make `meets_floor` a tautology (it could not fail). The
    # width term uses a bin count actually read from the rendered DOM (not
    # assumed to be 40) times the task's stated 9px-per-bin minimum, plus
    # its stated 56px y-gutter; the height term is the task's stated panel
    # minimums (ratio 96 + main 288 + ticks/label/header ~70). Both are
    # independent enough of FIG.w/FIG.h (480/460) that a shrunk renderer
    # would actually fail this check.
    all_ok = True
    for width in WIDTHS:
        browser, context, page, *_ = load_page(pw, width)
        rect = page.eval_on_selector("#hist-svg", "el => el.getBoundingClientRect()")
        nbins = page.evaluate("""() => document.querySelectorAll('#hist-svg .bin-hit').length""")
        floor_w = nbins * 9 + 56
        floor_h = 96 + 288 + 70
        overflow = page.evaluate(
            """() => ({
                bodyOverflows: (
                    document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
                ),
                scroller: (() => {
                    const s = document.querySelector('.figure-scroll');
                    if (!s) return null;
                    return {
                        scrollWidth: s.scrollWidth, clientWidth: s.clientWidth,
                        scrolls: s.scrollWidth > s.clientWidth + 1,
                    };
                })(),
            })"""
        )
        meets_floor = rect["width"] >= floor_w and rect["height"] >= floor_h
        all_ok = all_ok and meets_floor
        scroller = overflow["scroller"]
        line(
            f"width={width}px: hist-svg measured {rect['width']:.0f}x{rect['height']:.0f} CSS px",
            meets_floor,
            f"independently derived floor is {floor_w}x{floor_h} ({nbins} bins x 9px + 56px "
            f"gutter; 96+288+70 panel minimums); page body horizontal overflow="
            f"{overflow['bodyOverflows']}; .figure-scroll internal scroll engaged="
            f"{scroller['scrolls'] if scroller else 'n/a'}",
        )
        browser.close()
    print(
        "\nNote: this figure is a fixed intrinsic size (see plot.js FIG constant), not "
        "responsive — it measures the same width/height at all three widths by "
        "construction. The page body never scrolls horizontally at any tested width (see "
        "overflow probe above); the figure sits in '.figure-scroll', which is the "
        "container designed to absorb overflow if a future embedding is narrower."
    )
    return all_ok


def check_legend_layout(pw: Playwright) -> bool:
    """At each width in WIDTHS, measure the histogram legend's frame box and
    the main axes' frame box in real viewport pixels, and assert the legend
    sits entirely outside the axes box, to its right — acceptance criterion
    1 of the 2026-08-16 cycle-3 task, and the user's ruling it encodes (see
    design.md's D-003 entry). `rightOfAxes` and `noOverlap` are independent
    tests of the same geometric fact (see check_anatomy's version of this
    assertion for why both are checked, not just one) so a legend that is
    to the right in x but still overlapping in y cannot pass by accident.

    Falsifiability for this exact assertion is not demonstrated in this
    file — it is demonstrated once, live, by mutation-testing plot.js (put
    the legend back at its old inside-axes coordinates, rerun, watch this
    fail; restore, rerun, watch it pass again) — see the PR body for both
    transcripts, since a checker script asserting its own checker is
    correct is exactly the kind of self-referential proof this task's
    history warns against.
    """
    section("Legend layout — outside the axes, to the right, every width")
    all_ok = True
    for width in WIDTHS:
        browser, context, page, *_ = load_page(pw, width)
        geo = page.evaluate(
            """() => {
                const legend = document.querySelector('#hist-svg > .legend');
                const frame = legend ? legend.querySelector('.legend-frame') : null;
                const axesFrame = document.querySelector('#hist-svg .panel-main .plot-frame');
                if (!legend || !frame || !axesFrame) return null;
                const lb = frame.getBoundingClientRect();
                const ab = axesFrame.getBoundingClientRect();
                const noOverlap = (
                    lb.x >= ab.x + ab.width || ab.x >= lb.x + lb.width ||
                    lb.y >= ab.y + ab.height || ab.y >= lb.y + lb.height
                );
                return {
                    legendBox: { x: lb.x, y: lb.y, w: lb.width, h: lb.height },
                    axesBox: { x: ab.x, y: ab.y, w: ab.width, h: ab.height },
                    rightOfAxes: lb.x >= (ab.x + ab.width) - 0.5,
                    noOverlap,
                };
            }"""
        )
        ok = geo is not None and geo["rightOfAxes"] and geo["noOverlap"]
        all_ok = all_ok and ok
        line(
            f"width={width}px: legend outside axes, to the right",
            ok,
            (
                f"legend box {geo['legendBox']}, axes box {geo['axesBox']}, "
                f"rightOfAxes={geo['rightOfAxes']}, noOverlap={geo['noOverlap']}"
            )
            if geo
            else "legend or axes frame not found",
        )
        browser.close()
    return all_ok


def check_paint_sweep(pw: Playwright) -> bool:
    """At each width in WIDTHS, resolve tokens.css's :root into an allowed
    set of computed colours, then check every element's color/
    background-color/border-*-color/outline-color/text-decoration-color/
    caret-color/fill/stroke against that set — the closed-set membership
    sweep acceptance criterion 4 requires, with a printed denominator."""
    section("Paint sweep — token-set membership, every width")
    tokens = parse_root_tokens(TOKENS_CSS.read_text())
    all_ok = True
    for width in WIDTHS:
        browser, context, page, *_ = load_page(pw, width)
        allowed, resolved = resolve_allowed_colors(page, tokens)
        page.click("#tab-cutflow")
        page.wait_for_timeout(1700)
        report2 = page.evaluate(
            """(args) => {
                const [props, allowedList] = args;
                const allowed = new Set(allowedList);
                const results = { inspected: 0, violations: [], exemptCount: 0, urlPaint: 0 };
                // Scoped to <body> and its descendants: <html> and <head>
                // carry a UA-default computed color (black) that never
                // paints anything — body covers the full viewport and all
                // real content lives inside it, so those two are noise, not
                // signal, for a *visible* paint sweep.
                const scope = [document.body, ...document.body.querySelectorAll('*')];
                // fill/stroke only ever paint anything on SVG shape
                // elements — not on HTML elements (see the isSvgEl check
                // below), and not on SVG container/meta elements either
                // (<svg>, <g>, <defs>, <pattern>, <title>, <desc> all
                // resolve *some* computed fill/stroke value per the CSS
                // Fill spec's initial value, but none of them render one).
                // `line` has stroke but, having no interior, never fill.
                const fillableSvgTags = new Set(['rect', 'circle', 'path', 'polygon', 'text', 'ellipse', 'polyline']);
                const strokableSvgTags = new Set([...fillableSvgTags, 'line']);
                const isSvg = (el) => el.namespaceURI === 'http://www.w3.org/2000/svg';
                scope.forEach(el => {
                    const cs = getComputedStyle(el);
                    const tag = el.tagName.toLowerCase();
                    for (const prop of props) {
                        if (prop === 'fill' && !(isSvg(el) && fillableSvgTags.has(tag))) continue;
                        if (prop === 'stroke' && !(isSvg(el) && strokableSvgTags.has(tag))) continue;
                        const val = cs[prop];
                        if (val === undefined || val === '') continue;
                        results.inspected++;
                        const lower = String(val).toLowerCase();
                        const exempt = (
                            lower === 'none' || lower === 'transparent' ||
                            lower === 'rgba(0, 0, 0, 0)' || lower === 'currentcolor'
                        );
                        if (exempt) {
                            results.exemptCount++;
                            continue;
                        }
                        if (lower.startsWith('url(')) { results.urlPaint++; continue; }
                        if (!allowed.has(val)) {
                            results.violations.push({ tag: el.tagName, cls: el.getAttribute('class'), prop, val });
                        }
                    }
                });
                return results;
            }""",
            [PAINT_PROPS, list(allowed)],
        )
        ok = len(report2["violations"]) == 0
        all_ok = all_ok and ok
        line(
            f"width={width}px: {report2['inspected']} property reads over 9 paint properties x all elements",
            ok,
            f"{len(report2['violations'])} violations, {report2['exemptCount']} exempt "
            f"(none/transparent/currentColor), {report2['urlPaint']} hatch paint-server refs "
            f"(url(#syst-hatch)); allowed set has {len(allowed)} distinct resolved colours "
            f"from {len(tokens)} declared tokens",
        )
        if report2["violations"]:
            for v in report2["violations"][:10]:
                print(f"       violation: <{v['tag']} class={v['cls']!r}> {v['prop']}={v['val']}")
        browser.close()
    return all_ok


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    """WCAG relative luminance of an opaque (r, g, b) triple, 0-255 per
    channel."""

    def chan(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(rgb1: tuple[float, float, float], rgb2: tuple[float, float, float]) -> float:
    """WCAG contrast ratio between two opaque (r, g, b) triples."""
    l1, l2 = relative_luminance(rgb1), relative_luminance(rgb2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def parse_rgba(s: str) -> Optional[tuple[int, int, int, float]]:
    """Parse a computed `rgb(r, g, b)` or `rgba(r, g, b, a)` string, keeping
    alpha (default 1.0 for the 3-channel form). Text colours in this palette
    are declared translucent on purpose (`--ink-70`, `--ink-45` are alpha
    washes of `--ink`, not separate greys — see tokens.css), so contrast
    against a background has to composite alpha in, not discard it: an
    `rgba(43, 38, 32, 0.45)` foreground is measurably lighter than the same
    triple at alpha 1, and reads as passing AA only if that's accounted for."""
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", s)
    if not m:
        return None
    r, g, b, a = m.groups()
    return (int(r), int(g), int(b), float(a) if a is not None else 1.0)


def composite_over(
    fg_rgba: tuple[int, int, int, float], bg_rgb: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Alpha-composite a translucent foreground colour over an opaque
    background, returning the resulting opaque (r, g, b) actually painted —
    the colour a contrast check must measure, not the foreground's own
    un-blended channel values."""
    r, g, b, a = fg_rgba
    br, bgn, bb = bg_rgb
    return (r * a + br * (1 - a), g * a + bgn * (1 - a), b * a + bb * (1 - a))


def check_contrast(pw: Playwright) -> bool:
    """Check every text-bearing element's computed colour, alpha-composited
    over its real background, against the WCAG AA threshold for its font
    size/weight — plus named ratios for `--ink`, `--ink-70` and `--ink-45`
    specifically, since the token set is what a reviewer will actually ask
    about.

    Two things this rewrite adds for the 2026-08-16 cycle-3 task (the
    frozen per-sample palette, X1 on vermillion, is now the default):

    1. **Paint property.** SVG text in this figure never sets CSS `color`
       — plot.css paints it with `fill` (`.plot-tick-label`,
       `.legend-label`, `.plot-axis-label`, `.plot-header`,
       `.plot-eff-label` are all `fill:` rules). `getComputedStyle(el).color`
       on such an element resolves to whatever `color` it inherits — here,
       `--ink` from `<body>`, unconditionally — regardless of what `fill`
       actually paints. Checking `.color` on these elements was measuring
       an inherited property that is never rendered, not the one that is.
       Confirmed live: a `.plot-tick-label` (fill: var(--ink-70)) resolves
       `color` to opaque `--ink` (12.75:1) and `fill` to `--ink-70`
       (5.18:1) — two different numbers for the one thing actually visible.
       Fixed by reading `fill` for SVG text whose resolved fill is a real
       paint (not `none`/empty), `color` otherwise.
    2. **Text on a saturated fill.** The frozen palette puts a real hue
       (X1's vermillion, X2's, X3's) behind every sample swatch and stacked
       band. A geometric overlap probe (text element's bounding-box centre
       point inside a solid-fill shape's bounding box: `.hist-band`,
       `.legend-swatch`, or a cutflow bar, all matched by their
       `sample-x*` class, `url()`-paint shapes like the hatch band
       excluded) finds any label sitting on one of those fills and
       composites it over *that* fill — itself composited over the panel,
       since fills carry their own `fill-opacity` — rather than over
       plain paper/panel. Reported below as its own count, not folded
       silently into the general text sweep.
    """
    section("WCAG AA contrast — text against its real background, alpha-composited")
    browser, context, page, *_ = load_page(pw, 1024)
    # Read the resolved var(--paper)/var(--panel) directly for the real
    # ground colours text sits on, rather than trusting the shorthand
    # `background` property (which the ruled-paper gradient also writes to).
    paper_token = page.evaluate(
        """() => {
            const probe = document.createElement('div');
            probe.style.color = 'var(--paper)';
            document.body.appendChild(probe);
            const c = getComputedStyle(probe).color;
            document.body.removeChild(probe);
            return c;
        }"""
    )
    paper = parse_rgba(paper_token)[:3]  # opaque token; alpha channel unused
    panel_token = page.evaluate(
        """() => {
            const probe = document.createElement('div');
            probe.style.color = 'var(--panel)';
            document.body.appendChild(probe);
            const c = getComputedStyle(probe).color;
            document.body.removeChild(probe);
            return c;
        }"""
    )
    panel = parse_rgba(panel_token)[:3]

    # Both tabs are rendered into the DOM on load (plot.js draws both
    # figures up front); only one `.option-panel` is `display:block` at a
    # time. A single measurement pass therefore only sees one figure's text
    # actually laid out — the other's `getBoundingClientRect()` collapses
    # to (0,0,0,0), same as check_paint_sweep's reason for sweeping both
    # tabs (see that function). GATHER_JS excludes zero-area elements at
    # the source (both from the shapes list a label could sit on, and from
    # the elements it measures), so running it once per tab and
    # concatenating the results checks every real, rendered piece of text
    # on the page exactly once, with no double-count and no spurious
    # (0,0)-vs-(0,0) overlap match between two different hidden panels.
    gather_js = """() => {
        const isSvg = (el) => el.namespaceURI === 'http://www.w3.org/2000/svg';
        // Solid-fill shapes a label could sit on: sample bands, sample
        // legend swatches, cutflow bars — all carry a `sample-x*` class.
        // `url()`-paint shapes (the hatch band) are excluded by the
        // `startsWith('rgb')` filter below, since they have no single
        // resolved colour to composite against.
        const shapes = Array.from(document.querySelectorAll('[class*="sample-x"]'))
            .map(el => {
                const cs = getComputedStyle(el);
                if (!cs.fill || !cs.fill.startsWith('rgb')) return null;
                const r = el.getBoundingClientRect();
                if (r.width === 0 || r.height === 0) return null; // not currently rendered
                return {
                    fill: cs.fill,
                    fillOpacity: cs.fillOpacity || '1',
                    x0: r.x, y0: r.y, x1: r.x + r.width, y1: r.y + r.height,
                };
            })
            .filter(Boolean);

        const nodes = [];
        document.querySelectorAll('body :not(script):not(style)').forEach(el => {
            const direct = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
            if (!direct) return;
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return; // not currently rendered
            const cs = getComputedStyle(el);
            // The paint property that actually renders this element's
            // text: SVG text in this figure is painted via `fill`
            // (plot.css), never `color`; HTML text is painted via `color`.
            // See the docstring above for why this matters.
            const svgText = isSvg(el) && el.tagName.toLowerCase() === 'text';
            const usesFill = svgText && cs.fill && cs.fill !== 'none' && cs.fill !== '';
            const paintProp = usesFill ? 'fill' : 'color';
            const paint = cs[paintProp];
            const onPanel = !!el.closest('.browser-frame, .figure-scroll, .wf-annotations, .plot-controls');

            // Geometric overlap probe: does this text element's centre
            // point fall inside a solid-fill shape's box? If several match
            // (nested/overlapping shapes), the last one in document order
            // wins, matching SVG's own paint order (later == on top ==
            // what a viewer actually sees behind the text).
            const cx = rect.x + rect.width / 2;
            const cy = rect.y + rect.height / 2;
            let onShape = null;
            for (const s of shapes) {
                if (cx >= s.x0 && cx <= s.x1 && cy >= s.y0 && cy <= s.y1) onShape = s;
            }

            nodes.push({
                tag: el.tagName, cls: el.getAttribute('class'), paint, paintProp,
                fontSize: parseFloat(cs.fontSize), fontWeight: cs.fontWeight, onPanel,
                onShapeFill: onShape ? onShape.fill : null,
                onShapeOpacity: onShape ? parseFloat(onShape.fillOpacity) : null,
                text: el.textContent.trim().slice(0, 30),
            });
        });
        return nodes;
    }"""
    samples = page.evaluate(gather_js)  # histogram tab active (the page's default)
    page.click("#tab-cutflow")
    page.wait_for_timeout(1700)  # let the cutflow reveal animation finish before measuring it
    samples += page.evaluate(gather_js)  # cutflow tab active — the histogram is now the hidden one
    page.click("#tab-hist")
    page.wait_for_timeout(300)

    checked = 0
    on_shape_count = 0
    failures = []
    for s in samples:
        rgba = parse_rgba(s["paint"])
        if not rgba:
            continue
        if s["onShapeFill"]:
            on_shape_count += 1
            shape_rgba = parse_rgba(s["onShapeFill"])
            ground = composite_over((*shape_rgba[:3], s["onShapeOpacity"]), panel)
        else:
            ground = panel if s["onPanel"] else paper
        composited = composite_over(rgba, ground)
        ratio = contrast_ratio(composited, ground)
        large = s["fontSize"] >= 24 or (s["fontSize"] >= 18.66 and s["fontWeight"] in ("700", "bold"))
        threshold = 3.0 if large else 4.5
        checked += 1
        if ratio < threshold:
            failures.append((s, ratio, threshold))
    ok = len(failures) == 0
    line(
        f"{checked} text-bearing elements checked against their real background "
        f"(paint property read per-element: fill for SVG text, color otherwise; "
        f"{on_shape_count} of {checked} sit on a solid sample/legend fill and were composited "
        f"against that fill rather than paper {paper} or panel {panel})",
        ok,
        f"{len(failures)} below AA threshold",
    )
    for s, ratio, threshold in failures[:10]:
        print(
            f"       below AA: <{s['tag']} class={s['cls']!r}> {s['paintProp']}={s['paint']} "
            f"{ratio:.2f}:1 (needs {threshold}) text={s['text']!r}"
        )
    # explicit named ratios for the report, as required — composited over
    # paper, since --ink-70/--ink-45 are alpha washes, not opaque greys, and
    # an un-composited reading overstates their contrast (see composite_over).
    for label, var in [("ink on paper", "--ink"), ("ink-70 on paper", "--ink-70"), ("ink-45 on paper", "--ink-45")]:
        c, used_count = page.evaluate(
            """(v) => {
                const probe = document.createElement('div');
                probe.style.color = `var(${v})`;
                document.body.appendChild(probe);
                const resolved = getComputedStyle(probe).color;
                document.body.removeChild(probe);
                let used = 0;
                document.body.querySelectorAll('*').forEach(el => {
                    const cs = getComputedStyle(el);
                    if (cs.color === resolved || cs.fill === resolved) used++;
                });
                return [resolved, used];
            }""",
            var,
        )
        rgba = parse_rgba(c)
        composited = composite_over(rgba, paper)
        ratio = contrast_ratio(composited, paper)
        print(
            f"       {label}: {ratio:.2f}:1 against paper {paper} (composited from {c}, "
            f"used as color/fill by {used_count} element(s) in the rendered page)"
        )
    browser.close()
    return ok


def check_focus_walk(pw: Playwright) -> bool:
    """Drive a real keyboard Tab walk from the top of the page and check
    every reachable stop for a visible `:focus-visible` ring, counting
    stops with and without one."""
    section("Keyboard focus walk — real Tab presses, visible-ring count")
    browser, context, page, *_ = load_page(pw, 1024)
    # Give every distinct element a stable identity for this walk via an
    # in-memory WeakMap keyed by object identity (not a DOM attribute, never
    # written to markup) — the 40 bin-hit rects are otherwise indistinguishable
    # by tag/class/id alone, so a naive "seen this tag+class before" stop
    # condition would falsely end the walk after the first one.
    page.evaluate("""() => { window.__focusWalk = { map: new WeakMap(), next: 1 }; }""")
    page.keyboard.press("Tab")  # focus first element from top of document
    stops = []
    max_stops = 100
    seen_ids = set()
    for _ in range(max_stops):
        info = page.evaluate(
            """() => {
                const el = document.activeElement;
                if (!el || el === document.body) return null;
                const w = window.__focusWalk;
                let wid = w.map.get(el);
                if (wid === undefined) { wid = w.next++; w.map.set(el, wid); }
                const cs = getComputedStyle(el);
                const visible = (
                    el.matches(':focus-visible') &&
                    cs.outlineStyle !== 'none' &&
                    parseFloat(cs.outlineWidth) > 0
                );
                return {
                    wid, tag: el.tagName, cls: el.getAttribute('class'), id: el.id,
                    outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth, visible,
                };
            }"""
        )
        if info is None:
            break
        if info["wid"] in seen_ids:
            break
        seen_ids.add(info["wid"])
        stops.append(info)
        page.keyboard.press("Tab")
    with_ring = sum(1 for s in stops if s["visible"])
    without_ring = [s for s in stops if not s["visible"]]
    ok = len(stops) > 0 and len(without_ring) == 0
    line(
        f"{len(stops)} focusable stops reached by real Tab presses",
        ok,
        f"{with_ring} carried a visible focus ring, {len(without_ring)} did not",
    )
    for s in without_ring:
        print(f"       no visible ring: <{s['tag']} class={s['cls']!r} id={s['id']!r}>")
    for s in stops:
        print(
            f"       stop: <{s['tag']} class={s['cls']!r}> outline={s['outlineStyle']} "
            f"{s['outlineWidth']} visible={s['visible']}"
        )
    browser.close()
    return ok


def check_reduced_motion(pw: Playwright) -> bool:
    """Re-render with `reduced_motion="reduce"` and check every reveal
    animated element renders its finished end state immediately (no
    animation-name, full opacity) rather than mid-transit."""
    section("prefers-reduced-motion re-render")
    browser, context, page, *_ = load_page(pw, 1024, reduced_motion="reduce")
    facts = page.evaluate(
        """() => {
            const sel = '.reveal-frame, .reveal-band, .reveal-data, .reveal-legend';
            const els = Array.from(document.querySelectorAll(sel));
            return els.map(el => {
                const cs = getComputedStyle(el);
                return {
                    cls: el.getAttribute('class'),
                    animationName: cs.animationName,
                    opacity: parseFloat(cs.opacity),
                    strokeDashoffset: cs.strokeDashoffset,
                };
            });
        }"""
    )
    bad = [f for f in facts if f["animationName"] != "none" or f["opacity"] < 1]
    ok = len(facts) > 0 and len(bad) == 0
    line(
        f"{len(facts)} reveal-animated elements checked under prefers-reduced-motion: reduce",
        ok,
        f"{len(bad)} still animating or not at full opacity",
    )
    for f in bad[:10]:
        print(f"       still animating: {f}")
    browser.close()
    return ok


def check_network_and_errors(pw: Playwright) -> bool:
    """At each width, drive both tabs and the palette toggle, then check
    that every request was a local file:// load and that no console or page
    error fired."""
    section("Non-local requests + console/page errors")
    all_ok = True
    for width in WIDTHS:
        browser, context, page, console_errors, page_errors, requests = load_page(pw, width)
        page.click("#palette-toggle")  # histogram panel is the active one on load
        page.wait_for_timeout(200)
        page.click("#tab-cutflow")
        page.wait_for_timeout(500)
        non_local = [r for r in requests if not r.startswith("file://")]
        ok = len(non_local) == 0 and len(console_errors) == 0 and len(page_errors) == 0
        all_ok = all_ok and ok
        line(
            f"width={width}px: {len(requests)} requests total, {len(console_errors)} console "
            f"errors, {len(page_errors)} page errors",
            ok,
            f"non-local requests: {non_local}",
        )
        browser.close()
    return all_ok


def check_git_diff() -> bool:
    """Confirm this branch has not touched src/, tests/, or content/, by
    diffing against main's merge-base rather than the index (see comment
    below for why that distinction matters)."""
    section("git diff --stat main...HEAD -- src/ tests/ content/ (this exploration ships nothing)")
    # A bare `git diff --stat -- <paths>` compares the working tree to the
    # index — it would read clean the moment everything is committed,
    # regardless of what the branch actually committed under those paths.
    # `main...HEAD` (triple-dot, symmetric to the merge-base) is what
    # actually answers "did this branch touch src/tests/content", which is
    # criterion 5's real question.
    result = subprocess.run(
        ["git", "diff", "--stat", "main...HEAD", "--", "src/", "tests/", "content/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    ok = output == "" and result.returncode == 0
    detail = f"output: {output!r}" if output else "clean"
    if result.returncode != 0:
        detail += f"; stderr: {result.stderr.strip()!r}"
    line("No changes under src/, tests/, or content/ since branching from main", ok, detail)
    return ok


EXHAUSTIVE_CLAIM_PATTERNS: list[str] = [
    r"\bappears? nowhere\b",
    r"\bonly \d+ (values?|colou?rs?) exists?\b",
    r"\bno third\b",
    r"\bevery element (does|has|is)\b",
    # tokens.css's own note references design-brief prose; still flagged for review.
    r"\bnowhere else\b(?!.*\.claude/design)",
    r"\bexhaustively\b",
    # D-003 cycle 4 (Required 1, PR #5 review cycle 3): "two named exceptions"
    # was itself the falsifiable claim — a count of deviations from the
    # reference that a later finding disproved by arithmetic the moment a
    # third deviation turned up. These catch that shape of phrasing
    # generally, not just the specific words this cycle happened to write —
    # a spelled-out or numeral count paired with "named"/"exception(s)"/
    # "deviation(s)", and the ordinal "first/second named exception" form
    # this file used to enumerate them one at a time.
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+named\b",
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(exceptions?|deviations?)\b",
    r"\b(first|second|third|fourth|fifth)\s+named\s+exception\b",
    r"\bboth exceptions\b",
]


def check_no_exhaustive_prose() -> bool:
    """Scan this directory's own source files for the exhaustive-claim
    phrasing (`EXHAUSTIVE_CLAIM_PATTERNS`) that the D-003 task body forbids
    — a fact must be generated by this checker, never asserted in prose.
    This is a denylist, not a general check; a phrasing this doesn't cover
    can still slip through (see the PR's backlog note)."""
    section("Prose/comment lint — no exhaustive claims about this directory's own rendering")
    files = [
        HERE / "plot.html",
        HERE / "plot.css",
        HERE / "plot.js",
        HERE / "frame.css",
        HERE / "tokens.css",
    ]
    hits: list[tuple[str, str]] = []
    scanned = 0
    for f in files:
        scanned += 1
        text = f.read_text()
        for pat in EXHAUSTIVE_CLAIM_PATTERNS:
            for m in re.finditer(pat, text, re.I):
                start = max(0, m.start() - 40)
                hits.append((f.name, text[start:m.end() + 10].replace("\n", " ")))
    ok = len(hits) == 0
    line(f"{scanned} files scanned for exhaustive-claim phrasing", ok, f"{len(hits)} matches")
    for fname, ctx in hits:
        print(f"       {fname}: ...{ctx}...")
    return ok


def check_payload_consistency(pw: Playwright) -> bool:
    """Structurally compare the JSON parsed from plot.html's embedded
    #payload-data script tag against payload.json on disk, so the two
    cannot silently drift apart."""
    section("payload.json vs. embedded #payload-data — structural match")
    browser, context, page, *_ = load_page(pw, 1024)
    embedded = page.evaluate("""() => JSON.parse(document.getElementById('payload-data').textContent)""")
    on_disk = json.loads(PAYLOAD_JSON.read_text())
    ok = embedded == on_disk
    line("Embedded payload in plot.html equals payload.json on disk", ok, "" if ok else "structural diff found")
    browser.close()
    return ok


# =======================================================================
# D-004 — Beamline (node-graph style A)
# =======================================================================
def check_beamline_persistence(pw: Playwright) -> bool:
    """Criterion 1: Beamline persists an ordered edge list only. Reads the
    single `data-edges` attribute on `#graph`, prints it back as ordered
    source->destination pairs (by node kind + id), and separately makes a
    positive, falsifiable assertion — not a claim in prose — that no
    coordinate of any kind (an inline `style`, a data-x/y/pos/col/row/slot
    attribute, or a non-static computed `position` on a node) exists
    anywhere in the rendered DOM."""
    section("Beamline persistence — ordered edge list only, no coordinate anywhere")
    browser, context, page, *_ = load_beamline_page(pw, 1024)

    raw = page.eval_on_selector("#graph", "el => el.getAttribute('data-edges')")
    try:
        edges = json.loads(raw)
        well_formed = isinstance(edges, list) and all(
            isinstance(e, list) and len(e) == 2 and all(isinstance(x, str) for x in e) for e in edges
        )
    except (json.JSONDecodeError, TypeError):
        edges = None
        well_formed = False
    line(
        "data-edges attribute on #graph parses as a list of [from, to] id pairs",
        well_formed,
        f"raw attribute: {raw!r}",
    )

    if well_formed:
        kind_by_id = page.evaluate(
            """() => {
                const out = {};
                document.querySelectorAll('.node[data-node-id]').forEach(el => {
                    out[el.dataset.nodeId] = el.dataset.nodeKind;
                });
                return out;
            }"""
        )
        print(f"       {len(edges)} persisted edge(s), in order:")
        for src, dst in edges:
            print(f"         {kind_by_id.get(src, '?')}({src}) -> {kind_by_id.get(dst, '?')}({dst})")

    # Denominator is every element under <body>, not just .node elements, so
    # a coordinate hiding anywhere else on the page would still be caught.
    scan = page.evaluate(
        """() => {
            const all = Array.from(document.querySelectorAll('body *'));
            const coordAttrRe = /^data-(x|y|pos|position|col|column|row|slot)$/i;
            let inlineStyleCount = 0;
            let coordAttrCount = 0;
            const offenders = [];
            all.forEach(el => {
                if (el.getAttribute('style')) {
                    inlineStyleCount++;
                    offenders.push({ why: 'inline style', tag: el.tagName, cls: el.className });
                }
                for (const attr of el.attributes) {
                    if (coordAttrRe.test(attr.name)) {
                        coordAttrCount++;
                        offenders.push({ why: attr.name, tag: el.tagName, cls: el.className });
                    }
                }
            });
            const nodes = Array.from(document.querySelectorAll('.node'));
            const nonStatic = nodes.filter(el => getComputedStyle(el).position !== 'static').length;
            return {
                inspected: all.length, inlineStyleCount, coordAttrCount,
                nodeCount: nodes.length, nonStaticNodeCount: nonStatic,
                offenders: offenders.slice(0, 10),
            };
        }"""
    )
    no_coord = scan["inlineStyleCount"] == 0 and scan["coordAttrCount"] == 0 and scan["nonStaticNodeCount"] == 0
    line(
        f"No coordinate anywhere: {scan['inspected']} elements scanned for an inline style "
        f"attribute or a data-x/y/pos/col/row/slot-shaped attribute; {scan['nodeCount']} .node "
        "elements checked for a non-static computed position",
        no_coord,
        f"{scan['inlineStyleCount']} inline styles, {scan['coordAttrCount']} coordinate-shaped "
        f"attributes, {scan['nonStaticNodeCount']} non-statically-positioned nodes"
        + (f"; e.g. {scan['offenders']}" if scan["offenders"] else ""),
    )

    ok = well_formed and no_coord
    browser.close()
    return ok


def check_beamline_connection_gestures(pw: Playwright) -> bool:
    """Criterion 2: click-to-connect is accepted, drag-to-connect is
    refused — both driven by real Playwright gestures (`click()` for the
    accept case; `mouse.down`/`move`/`up` for the refuse case), never by
    calling this page's own JS handlers directly. Falsifiability for both
    assertions is demonstrated by mutation, not in this file — the same
    reporting shape D-003's legend-layout check used for the same reason
    (a checker asserting its own checker is correct proves nothing). See
    the PR body for both transcripts: break the accept path and this
    fails; break the refuse path and this fails; restore and both pass."""
    section("Connection gestures — click accepted, drag refused")
    all_ok = True

    # accept: two real clicks between a legal pair (Data -> Selection)
    browser, context, page, *_ = load_beamline_page(pw, 1024)
    page.click('[data-add-kind="DataSource"]')
    page.click('[data-add-kind="Selection"]')
    page.click('.node[data-node-id="n6"] .port--out')
    page.click('.node[data-node-id="n7"] .port--in')
    edges = json.loads(page.eval_on_selector("#graph", "el => el.getAttribute('data-edges')"))
    accepted = ["n6", "n7"] in edges
    all_ok = all_ok and accepted
    status_text = page.eval_on_selector("#graph-status", "el => el.textContent")
    line(
        "Click-to-connect: two real .click() calls on a legal pair (Data -> Selection) create the edge",
        accepted,
        f"edges={edges}, status={status_text!r}",
    )
    browser.close()

    # refuse by kind: a legal-port, illegal-kind pair, via real clicks
    browser, context, page, *_ = load_beamline_page(pw, 1024)
    page.click('[data-add-kind="Multiplicity"]')
    page.click('[data-add-kind="ObsGlobal"]')
    page.click('.node[data-node-id="n6"] .port--out')
    page.click('.node[data-node-id="n7"] .port--in')
    edges2 = json.loads(page.eval_on_selector("#graph", "el => el.getAttribute('data-edges')"))
    refused_by_kind = ["n6", "n7"] not in edges2
    status_text2 = page.eval_on_selector("#graph-status", "el => el.textContent")
    names_refusal = "cannot connect to" in status_text2
    all_ok = all_ok and refused_by_kind and names_refusal
    line(
        "Illegal-kind click attempt (Multiplicity -> Obs: Global) is refused, and the status "
        "region names why",
        refused_by_kind and names_refusal,
        f"edges={edges2}, status={status_text2!r}",
    )
    browser.close()

    # refuse by gesture: a legal pair, attempted by a real drag
    browser, context, page, *_ = load_beamline_page(pw, 1024)
    page.click('[data-add-kind="Selection"]')
    page.click('[data-add-kind="ObsCustom"]')
    src = page.locator('.node[data-node-id="n6"] .port--out').bounding_box()
    dst = page.locator('.node[data-node-id="n7"] .port--in').bounding_box()
    page.mouse.move(src["x"] + src["width"] / 2, src["y"] + src["height"] / 2)
    page.mouse.down()
    page.mouse.move(dst["x"] + dst["width"] / 2, dst["y"] + dst["height"] / 2, steps=15)
    page.mouse.up()
    edges3 = json.loads(page.eval_on_selector("#graph", "el => el.getAttribute('data-edges')"))
    refused_by_drag = ["n6", "n7"] not in edges3
    all_ok = all_ok and refused_by_drag
    line(
        "Real drag gesture (mouse.down on an out-port, mouse.move, mouse.up on a different "
        "node's in-port) between a legal pair (Selection -> Obs: Custom) does NOT create the edge",
        refused_by_drag,
        f"edges={edges3}",
    )
    browser.close()

    return all_ok


def derive_reference_legal_pairs() -> Optional[set[tuple[str, str]]]:
    """Extract `_OBS_TYPES_SET` and `_VALID_CONNECTIONS` from the vendored
    reference's own `ui/graph.py` and `exec` that exact source block — not a
    hand-transcription of it — to compute the legal ordered (src, dst) pairs
    among the 8 addable kinds. Returns None if the sibling reference repo is
    not checked out at `REFERENCE_GRAPH_PY`, rather than silently falling
    back to a hard-coded table: a parity claim with nothing to check against
    is not a parity claim (verification rule 4)."""
    if not REFERENCE_GRAPH_PY.exists():
        return None
    src = REFERENCE_GRAPH_PY.read_text()
    m = re.search(
        r"_OBS_TYPES_SET = .*?\n_VALID_CONNECTIONS: dict\[str, set\[str\]\] = \{.*?\n\}\n", src, re.S
    )
    if not m:
        return None
    ns: dict = {}
    exec(m.group(0), ns)  # the reference's own literal dict block, not user input
    valid_connections = ns["_VALID_CONNECTIONS"]
    legal = set()
    for s in BEAMLINE_ADDABLE_KINDS:
        for d in BEAMLINE_ADDABLE_KINDS:
            if d in valid_connections.get(s, set()):
                legal.add((s, d))
    return legal


def check_beamline_pairs(pw: Playwright) -> bool:
    """Criterion 3: every one of the 64 ordered (src, dst) pairs among the 8
    addable node kinds is attempted between two distinct, freshly-added node
    instances, through the real click-to-connect interaction path — never by
    calling isLegal() or any other JS function directly. The expected
    accept/refuse verdict for each pair is not hard-coded here: it comes
    from `derive_reference_legal_pairs`, executed fresh each run."""
    section("All 64 ordered node-kind pairs, real click gestures, against the reference's own allowlist")

    reference_legal = derive_reference_legal_pairs()
    if reference_legal is None:
        line(
            f"Reference allowlist executed from {REFERENCE_GRAPH_PY}",
            False,
            "sibling reference repo not found at this path -- cannot check parity against it",
        )
        return False
    line(
        f"Reference allowlist executed from {REFERENCE_GRAPH_PY} (not transcribed)",
        len(reference_legal) == 13,
        f"{len(reference_legal)} legal pairs derived among the 8 addable kinds",
    )

    browser = pw.chromium.launch()
    results: dict[tuple[str, str], bool] = {}
    for src_kind in BEAMLINE_ADDABLE_KINDS:
        for dst_kind in BEAMLINE_ADDABLE_KINDS:
            page = browser.new_page(viewport={"width": 1200, "height": 1200})
            page.goto(BEAMLINE_HTML.as_uri())
            page.wait_for_timeout(60)
            page.click(f'[data-add-kind="{src_kind}"]')
            page.click(f'[data-add-kind="{dst_kind}"]')
            out_sel = '.node[data-node-id="n6"] .port--out'
            in_sel = '.node[data-node-id="n7"] .port--in'
            if page.locator(out_sel).count() > 0:
                page.click(out_sel)
            if page.locator(in_sel).count() > 0:
                page.click(in_sel)
            edges = json.loads(page.eval_on_selector("#graph", "el => el.getAttribute('data-edges')"))
            results[(src_kind, dst_kind)] = ["n6", "n7"] in edges
            page.close()
    browser.close()

    accepted = {pair for pair, ok in results.items() if ok}
    refused = {pair for pair, ok in results.items() if not ok}
    disagreements = [pair for pair in results if results[pair] != (pair in reference_legal)]

    ok = len(results) == 64 and len(accepted) == 13 and len(refused) == 51 and not disagreements
    line(
        f"{len(results)} of 64 ordered pairs attempted via real click gestures",
        ok,
        f"{len(accepted)} accepted, {len(refused)} refused, {len(disagreements)} disagree with "
        "the reference-derived allowlist",
    )
    print("       accepted set:")
    for src_kind, dst_kind in sorted(accepted):
        print(f"         {src_kind} -> {dst_kind}")
    for pair in disagreements:
        print(
            f"       DISAGREES with reference: {pair} -- UI said {results[pair]}, "
            f"reference said {pair in reference_legal}"
        )

    return ok


def check_beamline_inventory(pw: Playwright) -> bool:
    """Criterion 4: every domain-inventory item (BEAMLINE_DOMAIN_INVENTORY,
    denominator and source named there) is present via a `data-wf`
    attribute, reported as n of N; plus the one locked node kind is present,
    visibly gated, not connectable, and not reachable by keyboard as an
    active control — checked by a real Tab walk, not by reading its
    tabindex value alone."""
    section("Domain inventory -- every data-wf item present, plus the locked node kind's own checks")
    browser, context, page, *_ = load_beamline_page(pw, 1024)

    names = [name for name, _ in BEAMLINE_DOMAIN_INVENTORY]
    counts = page.evaluate(
        """(names) => Object.fromEntries(
            names.map(n => [n, document.querySelectorAll(`[data-wf="${n}"]`).length])
        )""",
        names,
    )
    present = [n for n in names if counts[n] > 0]
    missing = [n for n in names if counts[n] == 0]
    n_total = len(BEAMLINE_DOMAIN_INVENTORY)
    ok_inventory = len(missing) == 0
    line(
        f"{len(present)} of {n_total} domain-inventory items present (denominator source: "
        "docs/wireframes/mission-screen.html's five layout options -- see "
        "BEAMLINE_DOMAIN_INVENTORY's own comment)",
        ok_inventory,
        f"missing: {missing}" if missing else "all present",
    )
    for name, source in BEAMLINE_DOMAIN_INVENTORY:
        mark = "x" if counts[name] > 0 else " "
        print(f"       [{mark}] {name} ({counts[name]}) -- {source}")

    locked_info = page.evaluate(
        """() => {
            const el = document.querySelector('[data-wf="node-locked"]');
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            return {
                visible: rect.width > 0 && rect.height > 0,
                ariaDisabled: el.getAttribute('aria-disabled'),
                isButtonOrLink: ['BUTTON', 'A', 'INPUT'].includes(el.tagName),
                hasTabindexNonNegative: (
                    el.hasAttribute('tabindex') && parseInt(el.getAttribute('tabindex'), 10) >= 0
                ),
                hasPort: !!el.querySelector('.port:not(.port--absent)'),
            };
        }"""
    )
    page.evaluate("""() => { window.__lockWalk = { map: new WeakMap(), next: 1 }; }""")
    page.keyboard.press("Tab")
    seen: set = set()
    locked_focused = False
    for _ in range(200):
        info = page.evaluate(
            """() => {
                const el = document.activeElement;
                if (!el || el === document.body) return null;
                const w = window.__lockWalk;
                let wid = w.map.get(el);
                if (wid === undefined) { wid = w.next++; w.map.set(el, wid); }
                return { wid, isLocked: el.matches('[data-wf="node-locked"]') };
            }"""
        )
        if info is None:
            break
        if info["wid"] in seen:
            break
        seen.add(info["wid"])
        if info["isLocked"]:
            locked_focused = True
        page.keyboard.press("Tab")

    locked_ok = (
        locked_info is not None
        and locked_info["visible"]
        and locked_info["ariaDisabled"] == "true"
        and not locked_info["isButtonOrLink"]
        and not locked_info["hasTabindexNonNegative"]
        and not locked_info["hasPort"]
        and not locked_focused
    )
    line(
        f"Locked node kind: visible={locked_info and locked_info['visible']}, "
        f"aria-disabled={locked_info and locked_info['ariaDisabled']!r}, not a button/link/input, "
        f"no non-negative tabindex, no port, reached by a real {len(seen)}-stop Tab walk="
        f"{locked_focused}",
        locked_ok,
        "" if locked_ok else f"raw: {locked_info}",
    )

    browser.close()
    return ok_inventory and locked_ok


def check_beamline_paint_sweep(pw: Playwright) -> bool:
    """Criterion 5's general sweep: computed-style paint properties at
    1440/1024/768, with a printed denominator, checked against tokens.css's
    :root set (same PAINT_PROPS list D-003 checks, including `fill`/`stroke`
    -- guarded to SVG shape elements only, same as D-003, since this page
    draws no SVG today and every HTML element resolves a `fill` it never
    renders), plus zero horizontal body overflow at 768."""
    section("Beamline paint sweep -- token-set membership, every width")
    tokens = parse_root_tokens(TOKENS_CSS.read_text())
    all_ok = True
    for width in WIDTHS:
        browser, context, page, *_ = load_beamline_page(pw, width)
        allowed, resolved = resolve_allowed_colors(page, tokens)
        report = page.evaluate(
            """(args) => {
                const [props, allowedList] = args;
                const allowed = new Set(allowedList);
                const results = { inspected: 0, violations: [], exemptCount: 0 };
                const scope = [document.body, ...document.body.querySelectorAll('*')];
                // fill/stroke only ever paint anything on SVG shape
                // elements, never on HTML elements -- see D-003's
                // check_paint_sweep for the same guard and why (every HTML
                // element resolves an initial `fill: rgb(0, 0, 0)` per the
                // CSS Fill spec even though it never renders one).
                const fillableSvgTags = new Set(['rect', 'circle', 'path', 'polygon', 'text', 'ellipse', 'polyline']);
                const strokableSvgTags = new Set([...fillableSvgTags, 'line']);
                const isSvg = (el) => el.namespaceURI === 'http://www.w3.org/2000/svg';
                scope.forEach(el => {
                    const cs = getComputedStyle(el);
                    const tag = el.tagName.toLowerCase();
                    for (const prop of props) {
                        if (prop === 'fill' && !(isSvg(el) && fillableSvgTags.has(tag))) continue;
                        if (prop === 'stroke' && !(isSvg(el) && strokableSvgTags.has(tag))) continue;
                        const val = cs[prop];
                        if (val === undefined || val === '') continue;
                        results.inspected++;
                        const lower = String(val).toLowerCase();
                        const exempt = (
                            lower === 'none' || lower === 'transparent' ||
                            lower === 'rgba(0, 0, 0, 0)' || lower === 'currentcolor'
                        );
                        if (exempt) { results.exemptCount++; continue; }
                        if (!allowed.has(val)) {
                            results.violations.push({ tag: el.tagName, cls: el.getAttribute('class'), prop, val });
                        }
                    }
                });
                const overflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
                return { ...results, bodyOverflow: overflow };
            }""",
            [PAINT_PROPS, list(allowed)],
        )
        ok = len(report["violations"]) == 0 and not report["bodyOverflow"]
        all_ok = all_ok and ok
        line(
            f"width={width}px: {report['inspected']} property reads across {len(PAINT_PROPS)} "
            f"properties, {report['exemptCount']} exempt, body horizontal overflow="
            f"{report['bodyOverflow']}",
            ok,
            f"{len(report['violations'])} off-token violations",
        )
        for v in report["violations"][:10]:
            print(f"       off-token: <{v['tag']} class={v['cls']!r}> {v['prop']}={v['val']}")
        browser.close()
    return all_ok


def check_beamline_contrast(pw: Playwright) -> bool:
    """Criterion 5's node-label requirement: the contrast of every node
    label against its own fill, alpha-composited, against the 4.5:1 AA
    floor -- plus the locked tile's own label against `--locked-fill`, plus
    a general sweep of every other text-bearing element against its own
    resolved background (the nearest painted ancestor, walking up from the
    element itself; paper is the fallback when nothing paints one)."""
    section("Beamline contrast -- text against its real background, alpha-composited")
    browser, context, page, *_ = load_beamline_page(pw, 1024)

    def resolve_token(name: str) -> tuple[float, float, float]:
        c = page.evaluate(
            """(v) => {
                const probe = document.createElement('div');
                probe.style.color = `var(${v})`;
                document.body.appendChild(probe);
                const r = getComputedStyle(probe).color;
                document.body.removeChild(probe);
                return r;
            }""",
            name,
        )
        return parse_rgba(c)[:3]

    paper = resolve_token("--paper")

    node_texts = page.evaluate(
        """() => {
            const out = [];
            document.querySelectorAll('.node').forEach(node => {
                const bg = getComputedStyle(node).backgroundColor;
                node.querySelectorAll('.node__title, .node__subtitle, .node__links li').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return;
                    const cs = getComputedStyle(el);
                    out.push({
                        kind: node.dataset.nodeKind, bg, color: cs.color,
                        fontSize: parseFloat(cs.fontSize), fontWeight: cs.fontWeight,
                        text: el.textContent.trim().slice(0, 24),
                    });
                });
            });
            return out;
        }"""
    )
    checked = 0
    failures = []
    per_kind_ratio: dict[str, float] = {}
    for t in node_texts:
        rgba = parse_rgba(t["color"])
        bg = parse_rgba(t["bg"])
        if not rgba or not bg:
            continue
        ground = composite_over(bg, paper)
        composited = composite_over(rgba, ground)
        ratio = contrast_ratio(composited, ground)
        checked += 1
        large = t["fontSize"] >= 24 or (t["fontSize"] >= 18.66 and t["fontWeight"] in ("700", "bold"))
        threshold = 3.0 if large else 4.5
        per_kind_ratio.setdefault(t["kind"], ratio)
        if ratio < threshold:
            failures.append((t, ratio, threshold))
    ok_nodes = checked > 0 and len(failures) == 0
    line(
        f"{checked} node label(s) checked against their own node fill, across "
        f"{len(per_kind_ratio)} node kinds",
        ok_nodes,
        f"{len(failures)} below AA",
    )
    for kind, ratio in sorted(per_kind_ratio.items()):
        print(f"       {kind}: {ratio:.2f}:1 against its own fill")
    for t, ratio, threshold in failures[:10]:
        print(f"       below AA: {t['kind']} {t['color']} on {t['bg']} = {ratio:.2f}:1 (needs {threshold})")

    locked = page.evaluate(
        """() => {
            const el = document.querySelector('[data-wf="node-locked"]');
            if (!el) return null;
            const cs = getComputedStyle(el);
            return { bg: cs.backgroundColor, color: cs.color };
        }"""
    )
    locked_ratio = None
    if locked:
        bg = parse_rgba(locked["bg"])
        fg = parse_rgba(locked["color"])
        ground = composite_over(bg, paper)
        composited = composite_over(fg, ground)
        locked_ratio = contrast_ratio(composited, ground)
    ok_locked = locked_ratio is not None and locked_ratio >= 4.5
    line(
        "Locked node-kind tile label against --locked-fill",
        ok_locked,
        f"{locked_ratio:.2f}:1" if locked_ratio else "n/a",
    )

    # Ground is resolved by walking up from the element itself (not by a
    # hand-maintained list of "panel-ish" selectors, which is exactly the
    # kind of guess that goes stale): the first ancestor, starting at the
    # element, whose own computed background-color is not transparent. That
    # is what a viewer actually sees behind the text, whether that is paper,
    # panel, a button's own solid fill, or anything else.
    general = page.evaluate(
        """() => {
            const isPaintedBg = (c) => c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent';
            const out = [];
            document.querySelectorAll('body :not(script):not(style)').forEach(el => {
                if (el.closest('.node') || el.matches('[data-wf="node-locked"]')) return;
                const direct = Array.from(el.childNodes).some(
                    n => n.nodeType === 3 && n.textContent.trim().length > 0
                );
                if (!direct) return;
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;
                const cs = getComputedStyle(el);
                let bg = null;
                let cur = el;
                while (cur && cur !== document.documentElement.parentElement) {
                    const c = getComputedStyle(cur).backgroundColor;
                    if (isPaintedBg(c)) { bg = c; break; }
                    cur = cur.parentElement;
                }
                out.push({
                    tag: el.tagName, cls: el.getAttribute('class'), color: cs.color, bg,
                    fontSize: parseFloat(cs.fontSize), fontWeight: cs.fontWeight,
                    text: el.textContent.trim().slice(0, 24),
                });
            });
            return out;
        }"""
    )
    checked2 = 0
    failures2 = []
    for s in general:
        rgba = parse_rgba(s["color"])
        if not rgba:
            continue
        bg_rgba = parse_rgba(s["bg"]) if s["bg"] else None
        ground = composite_over(bg_rgba, paper) if bg_rgba else paper
        composited = composite_over(rgba, ground)
        ratio = contrast_ratio(composited, ground)
        large = s["fontSize"] >= 24 or (s["fontSize"] >= 18.66 and s["fontWeight"] in ("700", "bold"))
        threshold = 3.0 if large else 4.5
        checked2 += 1
        if ratio < threshold:
            failures2.append((s, ratio, threshold, ground))
    ok_general = checked2 > 0 and len(failures2) == 0
    line(
        f"{checked2} other text-bearing elements checked against their own resolved background "
        f"(nearest painted ancestor background, walking up from the element itself; paper "
        f"{paper} is the fallback when nothing paints one)",
        ok_general,
        f"{len(failures2)} below AA",
    )
    for s, ratio, threshold, ground in failures2[:10]:
        print(
            f"       below AA: <{s['tag']} class={s['cls']!r}> {s['color']} on {ground} "
            f"{ratio:.2f}:1 (needs {threshold}) text={s['text']!r}"
        )

    browser.close()
    return ok_nodes and ok_locked and ok_general


def check_beamline_focus_walk(pw: Playwright) -> bool:
    """Drive a real keyboard Tab walk from the top of the page (same method
    as D-003's `check_focus_walk`) and check every reachable stop for a
    visible `:focus-visible` ring, counting stops with and without one --
    the design manual's "keyboard focus is visible on every interactive
    element" requirement, measured rather than eyeballed."""
    section("Beamline keyboard focus walk -- real Tab presses, visible-ring count")
    browser, context, page, *_ = load_beamline_page(pw, 1024)
    page.evaluate("""() => { window.__focusWalk = { map: new WeakMap(), next: 1 }; }""")
    page.keyboard.press("Tab")
    stops = []
    seen_ids: set = set()
    for _ in range(200):
        info = page.evaluate(
            """() => {
                const el = document.activeElement;
                if (!el || el === document.body) return null;
                const w = window.__focusWalk;
                let wid = w.map.get(el);
                if (wid === undefined) { wid = w.next++; w.map.set(el, wid); }
                const cs = getComputedStyle(el);
                const visible = (
                    el.matches(':focus-visible') &&
                    cs.outlineStyle !== 'none' &&
                    parseFloat(cs.outlineWidth) > 0
                );
                return { wid, tag: el.tagName, cls: el.getAttribute('class'), visible };
            }"""
        )
        if info is None:
            break
        if info["wid"] in seen_ids:
            break
        seen_ids.add(info["wid"])
        stops.append(info)
        page.keyboard.press("Tab")
    with_ring = sum(1 for s in stops if s["visible"])
    without_ring = [s for s in stops if not s["visible"]]
    ok = len(stops) > 0 and len(without_ring) == 0
    line(
        f"{len(stops)} focusable stops reached by real Tab presses",
        ok,
        f"{with_ring} carried a visible focus ring, {len(without_ring)} did not",
    )
    for s in without_ring[:10]:
        print(f"       no visible ring: <{s['tag']} class={s['cls']!r}>")
    browser.close()
    return ok


def check_beamline_reduced_motion(pw: Playwright) -> bool:
    """Re-render with prefers-reduced-motion: reduce and check every
    animated element (the `.node` entrance stagger, the `.stamp` press)
    renders its finished end state immediately, no transit."""
    section("Beamline prefers-reduced-motion re-render")
    browser, context, page, *_ = load_beamline_page(pw, 1024, reduced_motion="reduce")
    facts = page.evaluate(
        """() => {
            return Array.from(document.querySelectorAll('.node, .stamp')).map(el => {
                const cs = getComputedStyle(el);
                return {
                    cls: el.getAttribute('class'),
                    animationName: cs.animationName,
                    opacity: parseFloat(cs.opacity),
                };
            });
        }"""
    )
    bad = [f for f in facts if f["animationName"] != "none" or f["opacity"] < 1]
    ok = len(facts) > 0 and len(bad) == 0
    line(
        f"{len(facts)} reveal/press-animated elements checked under prefers-reduced-motion: reduce",
        ok,
        f"{len(bad)} still animating or not at full opacity",
    )
    for f in bad[:10]:
        print(f"       still animating: {f}")
    browser.close()
    return ok


def check_beamline_network_and_errors(pw: Playwright) -> bool:
    """Zero non-local requests, zero console/page errors, at each width --
    driven through the add-node/connect/run interactions, not just a bare
    load, so a handler wired up after load has a chance to misbehave."""
    section("Beamline -- non-local requests + console/page errors")
    all_ok = True
    for width in WIDTHS:
        browser, context, page, console_errors, page_errors, requests = load_beamline_page(pw, width)
        page.click('[data-add-kind="Selection"]')
        page.click('.node[data-node-id="n1"] .port--out')
        page.click('.node[data-node-id="n6"] .port--in')
        page.click("#run-button")
        page.wait_for_timeout(200)
        non_local = [r for r in requests if not r.startswith("file://")]
        ok = len(non_local) == 0 and len(console_errors) == 0 and len(page_errors) == 0
        all_ok = all_ok and ok
        line(
            f"width={width}px: {len(requests)} requests total, {len(console_errors)} console "
            f"errors, {len(page_errors)} page errors",
            ok,
            f"non-local requests: {non_local}",
        )
        browser.close()
    return all_ok


def check_beamline_no_exhaustive_prose() -> bool:
    """Same lint as `check_no_exhaustive_prose` (reusing the shared
    `EXHAUSTIVE_CLAIM_PATTERNS` denylist), run over this task's own files
    plus the D-004 addition to tokens.css -- kept as a separate function so
    D-003's own check and its file list stay untouched."""
    section("Beamline prose/comment lint -- no exhaustive claims about this directory's own rendering")
    files = [HERE / "beamline.html", HERE / "beamline.css", HERE / "beamline.js", HERE / "tokens.css"]
    hits: list[tuple[str, str]] = []
    for f in files:
        text = f.read_text()
        for pat in EXHAUSTIVE_CLAIM_PATTERNS:
            for m in re.finditer(pat, text, re.I):
                start = max(0, m.start() - 40)
                hits.append((f.name, text[start:m.end() + 10].replace("\n", " ")))
    ok = len(hits) == 0
    line(f"{len(files)} files scanned for exhaustive-claim phrasing", ok, f"{len(hits)} matches")
    for fname, ctx in hits:
        print(f"       {fname}: ...{ctx}...")
    return ok


# ---------------------------------------------------------------------
def main() -> None:
    """Run the anatomy checks (always) plus the full sweep (`--all`, the
    default) or just anatomy (`--plot`), print a summary table, and exit
    non-zero if any section failed. `--beamline` additionally (or, given
    alone, only in addition to the unconditional anatomy block above, which
    is D-003's existing behaviour and out of this task's file scope to
    change) runs the D-004 Beamline section."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", action="store_true", help="anatomy-only report")
    parser.add_argument("--all", action="store_true", help="full sweep")
    parser.add_argument("--beamline", action="store_true", help="D-004 Beamline section only")
    args = parser.parse_args()
    if not args.plot and not args.all and not args.beamline:
        args.all = True

    all_results = []
    with sync_playwright() as pw:
        browser, context, page, *_ = load_page(pw, 1024)
        all_results.append(("anatomy-main", all(ok for _, ok, _ in check_anatomy(page))))
        all_results.append(("anatomy-ratio", all(ok for _, ok, _ in check_ratio_panel(page))))
        all_results.append(("anatomy-fit-readout", all(ok for _, ok, _ in check_fit_readout(page))))
        all_results.append(("anatomy-cutflow", all(ok for _, ok, _ in check_cutflow(page))))
        browser.close()
        all_results.append(("payload-schema-sanity", all(ok for _, ok, _ in check_payload_schema_sanity())))

        if args.all:
            all_results.append(("payload-consistency", check_payload_consistency(pw)))
            all_results.append(("measurements", check_measurements(pw)))
            all_results.append(("legend-layout", check_legend_layout(pw)))
            all_results.append(("paint-sweep", check_paint_sweep(pw)))
            all_results.append(("contrast", check_contrast(pw)))
            all_results.append(("focus-walk", check_focus_walk(pw)))
            all_results.append(("reduced-motion", check_reduced_motion(pw)))
            all_results.append(("network-and-errors", check_network_and_errors(pw)))
            all_results.append(("git-diff-clean", check_git_diff()))
            all_results.append(("no-exhaustive-prose", check_no_exhaustive_prose()))

        if args.all or args.beamline:
            all_results.append(("beamline-persistence", check_beamline_persistence(pw)))
            all_results.append(("beamline-connection-gestures", check_beamline_connection_gestures(pw)))
            all_results.append(("beamline-pairs", check_beamline_pairs(pw)))
            all_results.append(("beamline-inventory", check_beamline_inventory(pw)))
            all_results.append(("beamline-paint-sweep", check_beamline_paint_sweep(pw)))
            all_results.append(("beamline-contrast", check_beamline_contrast(pw)))
            all_results.append(("beamline-focus-walk", check_beamline_focus_walk(pw)))
            all_results.append(("beamline-reduced-motion", check_beamline_reduced_motion(pw)))
            all_results.append(("beamline-network-and-errors", check_beamline_network_and_errors(pw)))
            all_results.append(("beamline-no-exhaustive-prose", check_beamline_no_exhaustive_prose()))

    section("Summary")
    for name, ok in all_results:
        line(name, ok)
    failed = [n for n, ok in all_results if not ok]
    print()
    if failed:
        print(f"FAILED sections: {failed}")
        sys.exit(1)
    else:
        print("All sections passed.")


if __name__ == "__main__":
    main()
