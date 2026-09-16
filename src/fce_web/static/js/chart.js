// Renders the finished run's histogram as interactive SVG into #results-chart
// (task F-008). Ported from docs/design-explorations/plot.js's
// renderHistogramFigure/drawLegend (D-003 exploration) -- geometry, stacking
// and the systematics-band formula are carried over unchanged; see the F-008
// PR body for exactly what was ported and what was deliberately left behind
// (the cutflow figure, legend toggling, the mplhep export, the Z gauge -- all
// out of scope, 2026-09-07 ruling).
//
// Contract (published in F-007's PR #46 body, run.js:6-22): on a finished
// ("done") run, #results-chart gets a `data-result` attribute (the raw
// GET /api/run/{id}/result JSON) and a bubbling `fce:result` CustomEvent
// fires on it with the parsed payload as `detail`. This module never fetches
// the result itself -- it only ever reads what run.js already handed it.
//
// samples[].weightsSquared is unconditionally null (docs/api.md semantics
// 8 -- no producer exists yet), but the reference renderer this is ported
// from never reads that field either: no MC statistical error band is drawn
// here, matching plot.js exactly. The systematics band and the ratio panel
// error bars are unaffected -- they are built from `systUp` and `data`
// (sqrt(N)), neither of which is nullable.

const SVG_NS = "http://www.w3.org/2000/svg";

function el(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) node.setAttribute(k, String(v));
  }
  return node;
}

function text(x, y, str, attrs = {}) {
  const node = el("text", { x, y, ...attrs });
  node.textContent = str;
  return node;
}

/** Linear scale: value in [d0,d1] -> pixel in [r0,r1]. */
function scaleLinear(d0, d1, r0, r1) {
  const m = (r1 - r0) / (d1 - d0);
  return (v) => r0 + (v - d0) * m;
}

/** "Nice numbers" axis-top chooser -- see plot.js:65-109 for the full
 * derivation of the 8% headroom multiplier and the five-step ladder. Ported
 * verbatim; not reinvented here. */
function niceCeilingAndStep(dataMax) {
  const max = dataMax * 1.08 || 1;
  const magnitude = Math.pow(10, Math.floor(Math.log10(max)));
  const steps = [1, 2, 2.5, 5, 10];
  for (const s of steps) {
    const step = s * magnitude;
    if (max / step <= 8) return { max, step };
  }
  return { max, step: 10 * magnitude };
}

// Figure geometry, unchanged from plot.js:124-142 -- the fixed 650x460 CSS
// px intrinsic size C1 requires.
const FIG = {
  left: 56,
  right: 12,
  headerH: 26,
  gap: 8,
  mainH: 288,
  ratioH: 96,
  xLabelH: 42,
  axesW: 412,
  legendGap: 20,
  legendW: 150,
};
FIG.h = 460;
FIG.axesTop = FIG.headerH + FIG.gap;
FIG.mainBottom = FIG.axesTop + FIG.mainH;
FIG.ratioBottom = FIG.mainBottom + FIG.ratioH;
FIG.axesLeft = FIG.left;
FIG.axesRight = FIG.axesLeft + FIG.axesW;
FIG.w = FIG.axesRight + FIG.legendGap + FIG.legendW + FIG.right;

const TICK_MAJOR = 6;
const TICK_MINOR = 3;

// Longest reveal chain in the reference's plot.css: legend animation-delay
// 1160ms + 380ms duration = 1540ms; 1600ms is that plus a small buffer
// (plot.js:710-712). D-016 owns the actual CSS durations and must keep this
// constant in step with whatever it builds, or update it here.
const REVEAL_TOTAL_MS = 1600;

function drawFrame(container, rect, xTicks, yTicks, opts) {
  const { showXLabels, showYLabel, yLabel, xLabelText, xFmt, yFmt } = opts;
  const { x0, y0, x1, y1 } = rect;

  container.appendChild(
    el("rect", { class: "plot-frame reveal-frame", x: x0, y: y0, width: x1 - x0, height: y1 - y0, fill: "none" })
  );

  for (const t of xTicks) {
    const len = t.major ? TICK_MAJOR : TICK_MINOR;
    const tickCls = `plot-tick ${t.major ? "plot-tick-major" : "plot-tick-minor"}`;
    container.appendChild(el("line", { class: tickCls, x1: t.px, x2: t.px, y1: y0, y2: y0 + len }));
    container.appendChild(el("line", { class: tickCls, x1: t.px, x2: t.px, y1: y1, y2: y1 - len }));
    if (t.major && showXLabels) {
      container.appendChild(
        text(t.px, y1 + 16, xFmt ? xFmt(t.value) : String(t.value), { class: "plot-tick-label", "text-anchor": "middle" })
      );
    }
  }
  for (const t of yTicks) {
    const len = t.major ? TICK_MAJOR : TICK_MINOR;
    const tickCls = `plot-tick ${t.major ? "plot-tick-major" : "plot-tick-minor"}`;
    container.appendChild(el("line", { class: tickCls, x1: x0, x2: x0 + len, y1: t.px, y2: t.px }));
    container.appendChild(el("line", { class: tickCls, x1: x1, x2: x1 - len, y1: t.px, y2: t.px }));
    if (t.major) {
      container.appendChild(
        text(x0 - 6, t.px + 3, yFmt ? yFmt(t.value) : String(t.value), { class: "plot-tick-label", "text-anchor": "end" })
      );
    }
  }
  if (showXLabels && xLabelText) {
    container.appendChild(text((x0 + x1) / 2, y1 + 34, xLabelText, { class: "plot-axis-label", "text-anchor": "middle" }));
  }
  if (showYLabel && yLabel) {
    const cy = (y0 + y1) / 2;
    container.appendChild(
      text(16, cy, yLabel, { class: "plot-axis-label", "text-anchor": "middle", transform: `rotate(-90 16 ${cy})` })
    );
  }
}

function ticksFor(scale, dMin, dMax, majorStep, minorStep) {
  const out = [];
  const eps = majorStep / 1000;
  for (let v = dMin; v <= dMax + eps; v += minorStep) {
    const rounded = Math.round(v / minorStep) * minorStep;
    const isMajor = Math.abs(rounded % majorStep) < eps || Math.abs((rounded % majorStep) - majorStep) < eps;
    out.push({ value: Math.round(rounded * 1000) / 1000, px: scale(rounded), major: isMajor });
  }
  return out;
}

/** One sample's stacked band as a single filled step-outline polygon --
 * plot.js:244-264, unchanged. */
function bandPath(edges, xScale, yScale, bottoms, tops) {
  const n = edges.length - 1;
  const pts = [];
  for (let i = 0; i < n; i++) {
    const xL = xScale(edges[i]);
    const xR = xScale(edges[i + 1]);
    const yT = yScale(tops[i]);
    pts.push(`${xL},${yT}`, `${xR},${yT}`);
  }
  for (let i = n - 1; i >= 0; i--) {
    const xL = xScale(edges[i]);
    const xR = xScale(edges[i + 1]);
    const yB = yScale(bottoms[i]);
    pts.push(`${xR},${yB}`, `${xL},${yB}`);
  }
  return "M" + pts.join(" L") + " Z";
}

function hatchBandPath(edges, xScale, yScale, low, high) {
  return bandPath(edges, xScale, yScale, low, high);
}

/** "///" hatch pattern for the systematic-uncertainty band -- plot.js:275-289. */
function ensureHatchDefs() {
  const defs = el("defs");
  const pattern = el("pattern", {
    id: "syst-hatch",
    patternUnits: "userSpaceOnUse",
    width: 6,
    height: 6,
    patternTransform: "rotate(45)",
  });
  [0, 3, 6].forEach((x) => {
    pattern.appendChild(el("line", { class: "hatch-line", x1: x, x2: x, y1: -1, y2: 7 }));
  });
  defs.appendChild(pattern);
  return defs;
}

/** Static legend -- swatches, hatch and marker rows, no toggle interaction.
 * plot.js's drawLegend ported as-is; the palette-toggle button it also
 * shipped is out of scope here (C6). */
function drawLegend(container, opts) {
  const { x, y, w, h, items } = opts;
  const g = el("g", { class: "legend legend-framed" });
  g.appendChild(el("rect", { class: "legend-frame", x, y, width: w, height: h }));
  items.forEach((item, i) => {
    const rowY = y + 10 + i * 15;
    if (item.kind === "swatch") {
      g.appendChild(el("rect", { class: `${item.cls} legend-swatch`, x: x + 8, y: rowY - 7, width: 14, height: 9 }));
    } else if (item.kind === "hatch") {
      g.appendChild(el("rect", { class: "syst-band legend-swatch", x: x + 8, y: rowY - 7, width: 14, height: 9 }));
    } else if (item.kind === "marker") {
      g.appendChild(el("circle", { class: "data-marker", cx: x + 15, cy: rowY - 2, r: 3 }));
    }
    g.appendChild(text(x + 28, rowY, item.label, { class: "legend-label" }));
  });
  container.appendChild(g);
}

/** Play the ink-draw reveal on `panel` exactly once, skipping it entirely
 * under prefers-reduced-motion -- plot.js:714-739, ported unchanged. The
 * settled (unarmed) state is what CSS renders with no `.reveal-armed`
 * class present, so skipping the class is what leaves the final geometry
 * (already fully computed either way -- this module never animates a `d`
 * attribute, only a class) with no motion applied to it (C5). */
function armReveal(panel) {
  if (!panel || panel.dataset.revealed === "true") return;
  panel.dataset.revealed = "true";
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }
  panel.classList.add("reveal-armed");
  window.setTimeout(() => panel.classList.remove("reveal-armed"), REVEAL_TOTAL_MS);
}

/** Renders the histogram (main + ratio panel) plus a keyboard/hover-readout
 * live region into `container`, replacing whatever was there. `payload` is
 * the histogram payload shape docs/api.md defines (meta/edges/lumiUnc/
 * systSources/samples/data), read straight off the `fce:result` event's
 * `detail` -- see this file's header comment. */
function renderHistogramFigure(container, payload) {
  container.textContent = "";

  const readout = document.createElement("p");
  readout.className = "chart-readout";
  readout.id = "chart-readout";
  readout.setAttribute("aria-live", "polite");
  readout.textContent = "Hover or tab into a bin for its range and yield.";
  container.appendChild(readout);

  const edges = payload.edges || [];
  const samples = payload.samples || [];
  const nbins = edges.length - 1;
  if (nbins < 1 || samples.length === 0) {
    const empty = document.createElement("p");
    empty.className = "chart-empty";
    empty.textContent = "No histogram data for this run.";
    container.appendChild(empty);
    return;
  }

  const figureWrap = document.createElement("div");
  figureWrap.className = "chart-figure";
  container.appendChild(figureWrap);

  const svg = el("svg", {
    id: "hist-svg",
    viewBox: `0 0 ${FIG.w} ${FIG.h}`,
    width: FIG.w,
    height: FIG.h,
    role: "img",
    "aria-labelledby": "hist-title hist-desc",
  });
  const titleEl = el("title");
  titleEl.id = "hist-title";
  titleEl.textContent = `${payload.meta && payload.meta.xLabel ? payload.meta.xLabel : "Histogram"} stacked histogram with ratio panel`;
  svg.appendChild(titleEl);
  const desc = el("desc");
  desc.id = "hist-desc";
  desc.textContent = `Stacked histogram of ${samples.map((s) => s.name).join(", ")} over pseudo-data, ${nbins} bins, with a data/prediction ratio panel below.`;
  svg.appendChild(desc);
  svg.appendChild(ensureHatchDefs());

  const xScale = scaleLinear(edges[0], edges[edges.length - 1], FIG.axesLeft, FIG.axesRight);

  const stackBottoms = samples.map(() => new Array(nbins).fill(0));
  const stackTops = samples.map(() => new Array(nbins).fill(0));
  const running = new Array(nbins).fill(0);
  samples.forEach((s, si) => {
    for (let i = 0; i < nbins; i++) {
      stackBottoms[si][i] = running[i];
      running[i] += s.counts[i];
      stackTops[si][i] = running[i];
    }
  });
  const mcStack = running;
  const data = payload.data || new Array(nbins).fill(0);
  const mcMax = Math.max(...mcStack, ...data);
  const { max: yMax, step: yStep } = niceCeilingAndStep(mcMax);
  const yScale = scaleLinear(0, yMax, FIG.mainBottom, FIG.axesTop);

  // Systematics band -- docs/api.md semantics 1: sum systUp over samples
  // first, take the fractional delta against the summed nominal, add
  // lumiUnc in quadrature, then mirror. Ported from plot.js:334-356.
  const lumiUnc = payload.lumiUnc || 0;
  const systSources = payload.systSources || [];
  const frac = new Array(nbins).fill(0);
  for (let i = 0; i < nbins; i++) {
    let frac2 = lumiUnc * lumiUnc;
    for (const src of systSources) {
      let up = 0;
      let any = false;
      for (const s of samples) {
        if (s.systUp && s.systUp[src]) {
          up += s.systUp[src][i];
          any = true;
        }
      }
      if (any && mcStack[i] > 0) {
        const f = (up - mcStack[i]) / mcStack[i];
        frac2 += f * f;
      }
    }
    frac[i] = mcStack[i] > 0 ? Math.sqrt(frac2) : 0;
  }
  const bandLow = mcStack.map((v, i) => v - v * frac[i]);
  const bandHigh = mcStack.map((v, i) => v + v * frac[i]);

  const mainG = el("g", { class: "panel-main" });
  svg.appendChild(mainG);

  mainG.appendChild(text(FIG.axesLeft, 16, "FCE", { class: "plot-header plot-header-bold" }));
  if (payload.meta) {
    mainG.appendChild(
      text(FIG.axesRight, 16, `${payload.meta.detector}, √s = ${payload.meta.energy}`, {
        class: "plot-header",
        "text-anchor": "end",
      })
    );
  }

  samples.forEach((s, si) => {
    mainG.appendChild(
      el("path", {
        class: `sample-${s.name.toLowerCase()} hist-band reveal-band s${si}`,
        d: bandPath(edges, xScale, yScale, stackBottoms[si], stackTops[si]),
        "fill-opacity": 0.8,
      })
    );
  });

  mainG.appendChild(
    el("path", { class: "syst-band reveal-band s3", d: hatchBandPath(edges, xScale, yScale, bandLow, bandHigh) })
  );

  // Pseudo-data: sqrt(N) error bars + circle markers -- the convention the
  // physics community reads these plots by (docs/api.md, docs/design-brief.md
  // §5). No MC statistical error is drawn: weightsSquared is unconditionally
  // null and the reference this is ported from never draws one either.
  const dataG = el("g", { class: "data-points reveal-data" });
  for (let i = 0; i < nbins; i++) {
    const cx = xScale((edges[i] + edges[i + 1]) / 2);
    const d = data[i];
    const err = Math.sqrt(Math.max(d, 0));
    const yC = yScale(d);
    const yLo = yScale(Math.max(d - err, 0));
    const yHi = yScale(d + err);
    dataG.appendChild(el("line", { class: "data-errbar", x1: cx, x2: cx, y1: yLo, y2: yHi }));
    dataG.appendChild(el("circle", { class: "data-marker", cx, cy: yC, r: 3 }));
  }
  mainG.appendChild(dataG);

  // Interactive bin hit-areas -- hover and keyboard both call the same
  // announce(), matching plot.js:403-444's Suggested-major fix: a focusable
  // role="button" must itself do the one thing its label promises when
  // activated, not only on focus.
  const hitG = el("g", { class: "bin-hits" });
  for (let i = 0; i < nbins; i++) {
    const xL = xScale(edges[i]);
    const xR = xScale(edges[i + 1]);
    const label = `${edges[i].toFixed(1)}–${edges[i + 1].toFixed(1)} GeV: ${Math.round(mcStack[i])} predicted, ${data[i]} data`;
    const hit = el("rect", {
      class: "bin-hit",
      x: xL,
      y: FIG.axesTop,
      width: Math.max(xR - xL, 0.01),
      height: FIG.mainH,
      fill: "none",
      "pointer-events": "all",
      tabindex: "0",
      role: "button",
      "aria-label": label,
    });
    const announce = () => {
      readout.textContent = label;
    };
    hit.addEventListener("mouseenter", announce);
    hit.addEventListener("focus", announce);
    hit.addEventListener("click", announce);
    hit.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " " || ev.key === "Spacebar") {
        ev.preventDefault();
        announce();
      }
    });
    hitG.appendChild(hit);
  }
  mainG.appendChild(hitG);

  const xMajor = 25;
  const xMinor = 5;
  const xTicksMain = ticksFor(xScale, edges[0], edges[edges.length - 1], xMajor, xMinor);
  const yTicksMain = ticksFor(yScale, 0, yMax, yStep, yStep / 2);
  drawFrame(
    mainG,
    { x0: FIG.axesLeft, y0: FIG.axesTop, x1: FIG.axesRight, y1: FIG.mainBottom },
    xTicksMain,
    yTicksMain,
    { showXLabels: false, showYLabel: true, yLabel: "Events / Bin" }
  );

  // Static legend -- stack order reversed (last sample first) so it reads
  // top-to-bottom the way the stack reads bottom-to-top, matching mplhep's
  // stacked-plot legend ordering (plot.js:459-480). No toggle (C6).
  const processNames = (payload.meta && payload.meta.processNames) || {};
  const legendItems = [...samples].reverse().map((s) => ({
    kind: "swatch",
    cls: `sample-${s.name.toLowerCase()}`,
    label: processNames[s.name] || s.name,
  }));
  legendItems.push({ kind: "hatch", label: "Syst. unc." });
  legendItems.push({ kind: "marker", label: "Pseudo-data" });
  drawLegend(svg, {
    x: FIG.axesRight + FIG.legendGap,
    y: FIG.axesTop,
    w: FIG.legendW,
    h: legendItems.length * 15 + 10,
    items: legendItems,
  });

  // ---- ratio panel --------------------------------------------------
  const ratioG = el("g", { class: "panel-ratio reveal-data" });
  svg.appendChild(ratioG);
  const ratioYScale = scaleLinear(0, 2, FIG.ratioBottom, FIG.mainBottom);
  const ratios = [];
  const ratioErrs = [];
  for (let i = 0; i < nbins; i++) {
    const d = data[i];
    const empty = mcStack[i] === 0 || d === 0;
    const r = empty ? 1.0 : d / mcStack[i];
    const e = empty ? 0.0 : Math.sqrt(Math.max(d, 0)) / mcStack[i];
    ratios.push(r);
    ratioErrs.push(e);
  }
  ratioG.appendChild(
    el("path", {
      class: "syst-band reveal-band s3",
      d: hatchBandPath(
        edges,
        xScale,
        ratioYScale,
        frac.map((f) => 1 - f),
        frac.map((f) => 1 + f)
      ),
    })
  );
  ratioG.appendChild(
    el("line", {
      class: "ratio-oneline",
      x1: FIG.axesLeft,
      x2: FIG.axesRight,
      y1: ratioYScale(1),
      y2: ratioYScale(1),
    })
  );
  for (let i = 0; i < nbins; i++) {
    const cx = xScale((edges[i] + edges[i + 1]) / 2);
    const r = Math.min(Math.max(ratios[i], 0), 2);
    const yLo = ratioYScale(Math.max(r - ratioErrs[i], 0));
    const yHi = ratioYScale(Math.min(r + ratioErrs[i], 2));
    ratioG.appendChild(el("line", { class: "data-errbar", x1: cx, x2: cx, y1: yLo, y2: yHi }));
    ratioG.appendChild(el("circle", { class: "data-marker", cx, cy: ratioYScale(r), r: 3 }));
  }
  const yTicksRatio = [0, 0.5, 1, 1.5, 2].map((v) => ({ value: v, px: ratioYScale(v), major: true }));
  yTicksRatio.push(...[0.25, 0.75, 1.25, 1.75].map((v) => ({ value: v, px: ratioYScale(v), major: false })));
  const xTicksRatio = ticksFor(xScale, edges[0], edges[edges.length - 1], xMajor, xMinor);
  drawFrame(
    ratioG,
    { x0: FIG.axesLeft, y0: FIG.mainBottom, x1: FIG.axesRight, y1: FIG.ratioBottom },
    xTicksRatio,
    yTicksRatio,
    {
      showXLabels: true,
      showYLabel: true,
      yLabel: "Data / Pred.",
      xLabelText: (payload.meta && payload.meta.xLabel) || "",
      xFmt: (v) => String(Math.round(v)),
    }
  );

  figureWrap.appendChild(svg);
  armReveal(figureWrap);
}

function onResult(event) {
  const container = event.currentTarget;
  renderHistogramFigure(container, event.detail || {});
}

function init() {
  const chart = document.getElementById("results-chart");
  if (!chart) return;
  chart.addEventListener("fce:result", onResult);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
