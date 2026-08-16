// plot.js — D-003 exploration. Renders the reference-parity histogram (with
// ratio panel) and the cutflow figure as hand-written SVG, driven entirely
// by the hard-coded payload embedded in plot.html (#payload-data). No
// fetch(), so it also runs correctly from a file:// URL.
//
// This file is a one-task carve-out from the JS/CSS ownership split (see the
// D-003 task body) so the design role can build the reference-parity chart
// end to end. It is not imported by the app.
//
// Colour policy: every SVG element that carries paint sets a `class` that
// keys into a CSS rule in plot.css, which resolves to a var() in
// tokens.css. Nothing here writes a hex value or a `style=` attribute —
// the one exception is the tick/reveal geometry, which is layout, not
// paint. The two sample-colour schemes (tab10 parity vs. a frozen
// per-sample map) are both wired up permanently via the `data-palette`
// attribute on <body>; the toggle button flips the attribute, the CSS
// decides what each scheme looks like.
//
// Loaded as a classic script, not `type="module"`: Chromium refuses to
// fetch a module script from a file:// document even same-origin, and this
// page is meant to open directly from disk. Everything is wrapped in one
// IIFE below so nothing here becomes a real global.
(function () {

const SVG_NS = "http://www.w3.org/2000/svg";

/** Build an SVG element with the given tag, attributes, and children. */
function el(tag, attrs = {}, children = []) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) node.setAttribute(k, String(v));
  }
  for (const child of children) {
    if (child) node.appendChild(child);
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

/** A small "nice numbers" tick chooser: returns {max, majorStep} for an
 * axis running from 0 to at least `dataMax`, headroom included. */
function niceCeilingAndStep(dataMax) {
  const target = dataMax * 1.35 || 1;
  const magnitude = Math.pow(10, Math.floor(Math.log10(target)));
  const steps = [1, 2, 2.5, 5, 10];
  for (const s of steps) {
    const step = s * magnitude;
    const ceiling = Math.ceil(target / step) * step;
    if (ceiling / step <= 8) return { max: ceiling, step };
  }
  const step = 10 * magnitude;
  return { max: Math.ceil(target / step) * step, step };
}

// ---------------------------------------------------------------------
// Figure geometry — the numbers verify.py measures against the derived
// floor (≈480 x 460 CSS px for the two-panel histogram). This figure is a
// fixed-size SVG, not a responsive one: physics figures keep a fixed
// aspect and bin width the way a printed plot would, and the surrounding
// .figure-scroll container scrolls horizontally rather than the figure
// shrinking its anatomy to fit a narrow viewport. See plot.html's
// annotations panel for the reasoning.
const FIG = {
  w: 480,
  h: 460,
  left: 56,
  right: 12,
  headerH: 26,
  gap: 8,
  mainH: 288,
  ratioH: 96,
  xLabelH: 42,
};
FIG.axesTop = FIG.headerH + FIG.gap; // 34
FIG.mainBottom = FIG.axesTop + FIG.mainH; // 322 = ratio top (hspace: 0)
FIG.ratioBottom = FIG.mainBottom + FIG.ratioH; // 418
FIG.axesLeft = FIG.left;
FIG.axesRight = FIG.w - FIG.right; // 468
FIG.axesW = FIG.axesRight - FIG.axesLeft; // 412

const CUTFLOW = {
  w: 460,
  h: 380,
  left: 56,
  barsW: 220,
  legendGap: 24,
  legendW: 150,
  headerH: 26,
  topPad: 8,
  barsH: 246,
  xLabelH: 90,
};
CUTFLOW.axesTop = CUTFLOW.headerH + CUTFLOW.topPad; // 34
CUTFLOW.axesBottom = CUTFLOW.axesTop + CUTFLOW.barsH; // 280
CUTFLOW.axesRight = CUTFLOW.left + CUTFLOW.barsW;

const TICK_MAJOR = 6;
const TICK_MINOR = 3;

function loadPayload() {
  const node = document.getElementById("payload-data");
  return JSON.parse(node.textContent);
}

// ---------------------------------------------------------------------
// Four-sided frame + inward ticks (hep.style.ROOT), for one rectangular
// panel. `xTicks`/`yTicks` are arrays of {px, major}. Labels are drawn only
// where requested — the main panel suppresses its x tick labels because it
// shares its x-axis with the ratio panel below it.
function drawFrame(container, rect, xTicks, yTicks, opts) {
  const { showXLabels, showYLabel, yLabel, xLabelText, xFmt, yFmt } = opts;
  const { x0, y0, x1, y1 } = rect;

  container.appendChild(
    el("rect", {
      class: "plot-frame reveal-frame",
      x: x0,
      y: y0,
      width: x1 - x0,
      height: y1 - y0,
      fill: "none",
    })
  );

  for (const t of xTicks) {
    const len = t.major ? TICK_MAJOR : TICK_MINOR;
    const tickCls = `plot-tick ${t.major ? "plot-tick-major" : "plot-tick-minor"}`;
    container.appendChild(el("line", { class: tickCls, x1: t.px, x2: t.px, y1: y0, y2: y0 + len }));
    container.appendChild(el("line", { class: tickCls, x1: t.px, x2: t.px, y1: y1, y2: y1 - len }));
    if (t.major && showXLabels) {
      container.appendChild(
        text(t.px, y1 + 16, xFmt ? xFmt(t.value) : String(t.value), {
          class: "plot-tick-label",
          "text-anchor": "middle",
        })
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
        text(x0 - 6, t.px + 3, yFmt ? yFmt(t.value) : String(t.value), {
          class: "plot-tick-label",
          "text-anchor": "end",
        })
      );
    }
  }
  if (showXLabels && xLabelText) {
    container.appendChild(
      text((x0 + x1) / 2, y1 + 34, xLabelText, { class: "plot-axis-label", "text-anchor": "middle" })
    );
  }
  if (showYLabel && yLabel) {
    const cy = (y0 + y1) / 2;
    container.appendChild(
      text(16, cy, yLabel, {
        class: "plot-axis-label",
        "text-anchor": "middle",
        transform: `rotate(-90 16 ${cy})`,
      })
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

// ---------------------------------------------------------------------
// Builds one sample's stacked band as a single filled step-outline
// polygon (top boundary left to right, bottom boundary right to left),
// the SVG equivalent of mplhep's `histtype="fill"` for a stacked sample.
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

/** Hatched band outline (top boundary then bottom boundary, unclosed
 * pairs) matching fill_between(edges*2, low, high) in the reference. */
function hatchBandPath(edges, xScale, yScale, low, high) {
  return bandPath(edges, xScale, yScale, low, high);
}

/** "///" hatch pattern for the systematic-uncertainty band — three
 * diagonal strokes per 6x6 tile so the hatch is seamless across tile
 * boundaries. Colour is a class, not an attribute, so it stays a token. */
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

function renderHistogramFigure(root, payload) {
  root.textContent = "";
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
  titleEl.textContent = "m(l₁, l₂) stacked histogram with ratio panel";
  svg.appendChild(titleEl);
  const desc = el("desc");
  desc.id = "hist-desc";
  desc.textContent =
    "Stacked histogram of X1, X2 and X3 over pseudo-data, 40 bins from 0 to 150 GeV, with a data/prediction ratio panel below.";
  svg.appendChild(desc);
  svg.appendChild(ensureHatchDefs());

  const edges = payload.edges;
  const nbins = edges.length - 1;
  const xScale = scaleLinear(edges[0], edges[edges.length - 1], FIG.axesLeft, FIG.axesRight);

  // ---- stack + syst band (main panel) ---------------------------------
  const samples = payload.samples;
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
  const mcStack = running; // total MC per bin
  const mcMax = Math.max(...mcStack, ...payload.data);
  const { max: yMax, step: yStep } = niceCeilingAndStep(mcMax);

  const yScale = scaleLinear(0, yMax, FIG.mainBottom, FIG.axesTop);

  // Aggregate per-source up-variation across samples, then combine with
  // LUMI_UNC in quadrature exactly as engine/plotter.py does.
  const frac = new Array(nbins).fill(0);
  for (let i = 0; i < nbins; i++) {
    let frac2 = payload.lumiUnc * payload.lumiUnc;
    for (const src of payload.systSources) {
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

  // header — "FCE" bold left, "IDEA, sqrt(s) = 91 GeV" right, above the axes
  mainG.appendChild(text(FIG.axesLeft, 16, "FCE", { class: "plot-header plot-header-bold" }));
  mainG.appendChild(
    text(FIG.axesRight, 16, `${payload.meta.detector}, √s = ${payload.meta.energy}`, {
      class: "plot-header",
      "text-anchor": "end",
    })
  );

  // stacked bands, bottom (X1) to top (X3) — draw order defines the stack
  samples.forEach((s, si) => {
    mainG.appendChild(
      el("path", {
        class: `sample-${s.name.toLowerCase()} hist-band reveal-band s${si}`,
        d: bandPath(edges, xScale, yScale, stackBottoms[si], stackTops[si]),
        "fill-opacity": 0.8,
      })
    );
  });

  // systematic band, main panel — facecolor none, grey hatch, no edge stroke
  mainG.appendChild(
    el("path", {
      class: "syst-band reveal-band s3",
      d: hatchBandPath(edges, xScale, yScale, bandLow, bandHigh),
    })
  );

  // pseudo-data: sqrt(N) error bars + circle markers
  const dataG = el("g", { class: "data-points reveal-data" });
  for (let i = 0; i < nbins; i++) {
    const cx = xScale((edges[i] + edges[i + 1]) / 2);
    const d = payload.data[i];
    const err = Math.sqrt(Math.max(d, 0));
    const yC = yScale(d);
    const yLo = yScale(Math.max(d - err, 0));
    const yHi = yScale(d + err);
    dataG.appendChild(el("line", { class: "data-errbar", x1: cx, x2: cx, y1: yLo, y2: yHi }));
    dataG.appendChild(el("circle", { class: "data-marker", cx, cy: yC, r: 3 }));
  }
  mainG.appendChild(dataG);

  // interactive bin hit-areas — keyboard + hover readout, main panel only
  const readout = document.getElementById("plot-readout");
  const hitG = el("g", { class: "bin-hits" });
  for (let i = 0; i < nbins; i++) {
    const xL = xScale(edges[i]);
    const xR = xScale(edges[i + 1]);
    const label = `${edges[i].toFixed(1)}–${edges[i + 1].toFixed(1)} GeV: ${Math.round(mcStack[i])} predicted, ${payload.data[i]} data`;
    const hit = el("rect", {
      class: "bin-hit",
      x: xL,
      y: FIG.axesTop,
      width: Math.max(xR - xL, 0.01),
      height: FIG.mainH,
      fill: "none",
      tabindex: "0",
      role: "button",
      "aria-label": label,
    });
    const announce = () => {
      if (readout) readout.textContent = label;
    };
    hit.addEventListener("mouseenter", announce);
    hit.addEventListener("focus", announce);
    hitG.appendChild(hit);
  }
  mainG.appendChild(hitG);

  // frame + ticks (main panel: x labels suppressed, y label shown)
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

  // legend — framed, inside axes, upper right; stack order reversed (X3
  // first) to read top-to-bottom the way the stack reads bottom-to-top,
  // then "Syst. unc.", then "Pseudo-data" — matches mplhep's stacked-plot
  // legend ordering.
  const legendItems = [...samples].reverse().map((s) => ({
    kind: "swatch",
    cls: `sample-${s.name.toLowerCase()}`,
    label: payload.meta.processNames[s.name] || s.name,
  }));
  legendItems.push({ kind: "hatch", label: "Syst. unc." });
  legendItems.push({ kind: "marker", label: "Pseudo-data" });
  drawLegend(mainG, {
    x: FIG.axesRight - 158,
    y: FIG.axesTop + 6,
    w: 152,
    h: legendItems.length * 15 + 10,
    framed: true,
    items: legendItems,
  });

  // ---- ratio panel -------------------------------------------------------
  const ratioG = el("g", { class: "panel-ratio reveal-data" });
  svg.appendChild(ratioG);
  const ratioYScale = scaleLinear(0, 2, FIG.ratioBottom, FIG.mainBottom);
  const ratios = [];
  const ratioErrs = [];
  for (let i = 0; i < nbins; i++) {
    const d = payload.data[i];
    const empty = mcStack[i] === 0 || d === 0;
    const r = empty ? 1.0 : d / mcStack[i];
    const e = empty ? 0.0 : Math.sqrt(Math.max(d, 0)) / mcStack[i];
    ratios.push(r);
    ratioErrs.push(e);
  }
  // hatched band around 1.0, unlabelled
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
  yTicksRatio.push(
    ...[0.25, 0.75, 1.25, 1.75].map((v) => ({ value: v, px: ratioYScale(v), major: false }))
  );
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
      xLabelText: payload.meta.xLabel,
      xFmt: (v) => String(Math.round(v)),
    }
  );

  root.appendChild(svg);
}

function drawLegend(container, opts) {
  const { x, y, w, h, framed, items } = opts;
  const g = el("g", { class: `legend reveal-legend ${framed ? "legend-framed" : "legend-plain"}` });
  if (framed) {
    g.appendChild(el("rect", { class: "legend-frame", x, y, width: w, height: h }));
  }
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

function renderCutflowFigure(root, payload) {
  root.textContent = "";
  const cf = payload.cutflow;
  const svg = el("svg", {
    id: "cutflow-svg",
    viewBox: `0 0 ${CUTFLOW.w} ${CUTFLOW.h}`,
    width: CUTFLOW.w,
    height: CUTFLOW.h,
    role: "img",
    "aria-labelledby": "cutflow-title cutflow-desc",
  });
  const titleEl = el("title");
  titleEl.id = "cutflow-title";
  titleEl.textContent = "Normalized MC composition cutflow";
  svg.appendChild(titleEl);
  const descEl = el("desc");
  descEl.id = "cutflow-desc";
  descEl.textContent = `Stacked composition by stage: ${cf.stages.join(", ")}. Efficiency printed above each bar.`;
  svg.appendChild(descEl);

  svg.appendChild(text(CUTFLOW.left, 16, "FCE", { class: "plot-header plot-header-bold" }));
  svg.appendChild(
    text(CUTFLOW.axesRight, 16, `${payload.meta.detector}, √s = ${payload.meta.energy}`, {
      class: "plot-header",
      "text-anchor": "end",
    })
  );

  const yScale = scaleLinear(0, 115, CUTFLOW.axesBottom, CUTFLOW.axesTop);
  const nStages = cf.stages.length;
  const bandW = CUTFLOW.barsW / nStages;
  const barW = bandW * 0.6;

  // frame + y ticks only (x ticks are the rotated stage labels, drawn
  // separately below so they can rotate around their own anchor)
  const yTicks = ticksFor(yScale, 0, 100, 25, 12.5).map((t) => ({ ...t, px: yScale(t.value) }));
  const frameG = el("g", { class: "panel-cutflow" });
  svg.appendChild(frameG);
  frameG.appendChild(
    el("rect", {
      class: "plot-frame reveal-frame",
      x: CUTFLOW.left,
      y: CUTFLOW.axesTop,
      width: CUTFLOW.barsW,
      height: CUTFLOW.axesBottom - CUTFLOW.axesTop,
      fill: "none",
    })
  );
  for (const t of yTicks) {
    const len = t.major ? TICK_MAJOR : TICK_MINOR;
    frameG.appendChild(
      el("line", { class: "plot-tick", x1: CUTFLOW.left, x2: CUTFLOW.left + len, y1: t.px, y2: t.px })
    );
    frameG.appendChild(
      el("line", { class: "plot-tick", x1: CUTFLOW.axesRight, x2: CUTFLOW.axesRight - len, y1: t.px, y2: t.px })
    );
    if (t.major) {
      frameG.appendChild(
        text(CUTFLOW.left - 6, t.px + 3, String(t.value), { class: "plot-tick-label", "text-anchor": "end" })
      );
    }
  }
  const cy = (CUTFLOW.axesTop + CUTFLOW.axesBottom) / 2;
  frameG.appendChild(
    text(16, cy, "MC Composition (%)", {
      class: "plot-axis-label",
      "text-anchor": "middle",
      transform: `rotate(-90 16 ${cy})`,
    })
  );

  // bars: normalized composition per stage, canonical ascending order (X1
  // bottom .. X3 top), inward x ticks per stage centre
  cf.stages.forEach((stageName, si) => {
    const counts = cf.counts[stageName];
    const stageTotal = cf.samples.reduce((acc, s) => acc + (counts[s] || 0), 0);
    let bottom = 0;
    const barX = CUTFLOW.left + bandW * si + (bandW - barW) / 2;
    cf.samples.forEach((s) => {
      const frac = stageTotal > 0 ? (100 * (counts[s] || 0)) / stageTotal : 0;
      const y0 = yScale(bottom + frac);
      const y1 = yScale(bottom);
      frameG.appendChild(
        el("rect", {
          class: `sample-${s.toLowerCase()} hist-band reveal-band s${cf.samples.indexOf(s)}`,
          x: barX,
          y: y0,
          width: barW,
          height: Math.max(y1 - y0, 0),
          "fill-opacity": 0.85,
        })
      );
      bottom += frac;
    });
    // efficiency label above bar
    const effX = barX + barW / 2;
    const effY = yScale(bottom) - 8;
    frameG.appendChild(
      text(effX, effY, `${cf.efficiencyPct[si].toFixed(1)}%`, {
        class: "plot-eff-label",
        "text-anchor": "middle",
      })
    );
    // rotated stage tick label, first stage is "Total"
    const tickX = CUTFLOW.left + bandW * si + bandW / 2;
    frameG.appendChild(
      el("line", {
        class: "plot-tick",
        x1: tickX,
        x2: tickX,
        y1: CUTFLOW.axesBottom,
        y2: CUTFLOW.axesBottom - TICK_MAJOR,
      })
    );
    frameG.appendChild(
      text(tickX, CUTFLOW.axesBottom + 8, stageName, {
        class: "plot-tick-label",
        "text-anchor": "end",
        transform: `rotate(-45 ${tickX} ${CUTFLOW.axesBottom + 8})`,
      })
    );
  });

  // legend — outside the axes to the right, unframed, ascending sample
  // order (X1 -> X3): the opposite of the histogram's reversed, framed one.
  const legendItems = cf.samples.map((s) => ({
    kind: "swatch",
    cls: `sample-${s.toLowerCase()}`,
    label: payload.meta.processNames[s] || s,
  }));
  drawLegend(svg, {
    x: CUTFLOW.axesRight + CUTFLOW.legendGap,
    y: CUTFLOW.axesTop,
    w: CUTFLOW.legendW,
    h: legendItems.length * 15 + 10,
    framed: false,
    items: legendItems,
  });

  root.appendChild(svg);
}

function initTabs() {
  const tabs = Array.from(document.querySelectorAll(".tab-btn[role='tab']"));
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });
      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      const panelId = tab.getAttribute("aria-controls");
      document.querySelectorAll(".option-panel").forEach((p) => p.classList.remove("active"));
      const panel = document.getElementById(panelId);
      if (panel) panel.classList.add("active");
    });
  });
}

function initPaletteToggle() {
  const btn = document.getElementById("palette-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const current = document.body.dataset.palette;
    const next = current === "tab10" ? "frozen" : "tab10";
    document.body.dataset.palette = next;
    btn.setAttribute("aria-pressed", next === "frozen" ? "true" : "false");
    btn.textContent =
      next === "tab10" ? "Sample colours: tab10 (parity)" : "Sample colours: frozen per-sample map";
  });
}

function main() {
  const payload = loadPayload();
  const histRoot = document.getElementById("hist-figure");
  const cutflowRoot = document.getElementById("cutflow-figure");
  if (histRoot) renderHistogramFigure(histRoot, payload);
  if (cutflowRoot) renderCutflowFigure(cutflowRoot, payload);
  initTabs();
  initPaletteToggle();

  const muEl = document.getElementById("fit-mu");
  const zEl = document.getElementById("fit-z");
  if (muEl) muEl.textContent = `μ = ${payload.fit.mu.toFixed(2)} ± ${payload.fit.muErr.toFixed(2)}`;
  if (zEl) zEl.textContent = `Z = ${payload.fit.significanceZ.toFixed(1)}σ`;
}

document.addEventListener("DOMContentLoaded", main);

})();
