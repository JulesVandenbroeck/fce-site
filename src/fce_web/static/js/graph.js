// Drives the analysis canvas inside templates/shell.html (#canvas-wrap):
// placing, dragging, and connecting nodes on the free-canvas "Bench" style
// the user ruled on 2026-09-01 (docs/design-brief.md §4). Ported from
// docs/design-explorations/bench.html:200-725 (F-005) -- see that file's own
// header comment for the design history. shell.js (F-004) owns the palette
// and mission-panel collapse toggles; this module owns everything the graph
// itself does.
//
// The palette this ships is the FOUR kinds the 2026-09-01/02 rulings settled
// on -- Multiplicity, Selection, Observable, Histogram -- already the
// buttons shell.html renders (`.palette__add[data-add-kind]`). `DataSource`
// is never drawn; the server synthesises it at submit from the mission's
// dataset (`src/fce_web/graph.py`, C4/C5 there). A fifth, locked tile lives
// in shell.html next to the four palette buttons.
//
// Exported model (the contract F-007 serialises): the canvas container
// (#canvas-wrap) carries one `data-graph` attribute, a JSON object
//   { nodes: [ { id, kind, x, y, config? }, ... ], edges: [ [from, to], ... ] }
// `nodes` is a list, matching the shape `build_run_config` requires
// (`src/fce_web/graph.py:120,122-123` -- a list of objects with `id` and
// `kind`; `config` is optional there and is only ever sent for `Observable`
// nodes here, carrying `{ mode }` -- F-006, the merged node's in-node mode
// toggle. `x`/`y` ride along as keys the server does not read. Edges are an
// ordered [from, to] pair list, same shape bench.html and graph.py both use.
//
// F-006 also owns the `Observable` node's grow-in-place interior (source:
// docs/design-explorations/observable.html): a native <details> holding a
// radio-group mode toggle, ported as markup+behaviour only. F-011 built the
// per-mode forms this header used to say were missing -- see
// buildObservableInterior's own comment for how they wire into `config`.
// growNode() resizes the node's foreignObject to its measured content box,
// no fixed numbers guessed.
//
// VALID_CONNECTIONS below is a courtesy check only, trimmed to the four
// palette kinds. `src/fce_web/graph.py`'s `VALID_CONNECTIONS` is the
// authority (B-020); a client that disagrees with the server is a bug in
// the client, not a second source of truth.

import {
  OBJECTS,
  VECTOR_SUM_OBJECTS,
  PROPERTIES,
  OBJECT_PROPERTIES,
  COUNTS,
  COMPARISONS,
  VECTOR_SUM_QUANTITIES,
  MULT_COMPARISONS,
  LEPTON_TYPES,
  buildSelectionExpr,
  globalConfig,
  objectConfig,
  vectorSumConfig,
  customConfig,
} from "./expr.js";

const SVG_NS = "http://www.w3.org/2000/svg";

const NODE_KINDS = [
  { kind: "Multiplicity", label: "Multiplicity", cls: "multiplicity", hasIn: true, hasOut: true },
  { kind: "Selection", label: "Selection", cls: "selection", hasIn: true, hasOut: true },
  { kind: "Observable", label: "Observable", cls: "observable", hasIn: true, hasOut: true },
  { kind: "Histogram", label: "Histogram", cls: "histogram", hasIn: true, hasOut: false },
];

const KIND_BY_NAME = Object.fromEntries(NODE_KINDS.map((k) => [k.kind, k]));

// Mirrors fce_web/graph.py:VALID_CONNECTIONS, trimmed to the rows a client
// can ever ask about -- the four placeable kinds. `Selection` may also
// legally reach ObsGlobal/ObsObject/ObsVectorSum/ObsCustom server-side, but
// those are never node kinds here (Observable's `mode` field stands in for
// them), so they are not listed.
const VALID_CONNECTIONS = {
  Multiplicity: ["Multiplicity", "Selection"],
  Selection: ["Selection", "Observable"],
  Observable: ["Histogram"],
  Histogram: [],
};

function isLegal(srcKind, dstKind) {
  return (VALID_CONNECTIONS[srcKind] || []).includes(dstKind);
}

const NODE_W = 160;
// Tall enough that the unstyled node's content (title, subtitle, ports,
// links) never overflows the foreignObject's own clip box before D-015
// gives it real layout -- an overflowing port is invisible to hit-testing
// even though getBoundingClientRect still reports it.
const NODE_H = 104;
const NUDGE = 12;
const NUDGE_BIG = 40;

// ---- pan/zoom (F-016, ported from docs/design-explorations/canvas-frame.html)
// The canvas is a bounded "sheet" the SVG's viewBox covers -- #canvas-wrap
// pans it via its own native `overflow: auto` scrolling (never a free
// transform, per the N13 ruling: that is what buys real scrollbars and
// keyboard arrow-key panning for free), and zoom scales the SVG's rendered
// width/height against that viewBox. `sheet` starts at the floor and is
// only ever grown, in applyZoom -- see its own comment for why that
// direction is load-bearing (D-021's monotonic-sheet rule, this task's C5).
const SHEET_MIN_W = 1200;
const SHEET_MIN_H = 900;
const SHEET_PAD = 240; // surface units of spare paper beyond the viewport
const ZOOM_MIN = 0.5;
const ZOOM_MAX = 2.0;
const ZOOM_STEP = 0.25;
const FIT_PAD = 24;

let zoom = 1;
const sheet = { w: SHEET_MIN_W, h: SHEET_MIN_H }; // surface units, rewritten by applyZoom

// The only state this module keeps.
const graphState = {
  nodes: new Map(), // id -> { kind, x, y, config?, rangePreset? }
  edges: [], // [fromId, toId][]
  nextId: 1,
  spawnIndex: 0,
  keyboardArmed: null, // { id, kind } while an out-port is armed via Enter/Space
};

// F-012, C3: a Histogram node's applyPreset(range, label), keyed by node id
// -- how an upstream Observable's update() re-presets a connected
// Histogram's range without a second graph model; looked up through the
// same graphState.edges list `attemptConnect` and `renderEdges` already use.
const histogramInteriors = new Map();

let els = {};

function nodeLabel(id) {
  const n = graphState.nodes.get(id);
  return n ? `${KIND_BY_NAME[n.kind].label} (${id})` : id;
}

function persistUI() {
  const nodes = [];
  graphState.nodes.forEach((n, id) => {
    const out = { id, kind: n.kind, x: n.x, y: n.y };
    if (n.config) out.config = n.config;
    nodes.push(out);
  });
  els.wrap.setAttribute("data-graph", JSON.stringify({ nodes, edges: graphState.edges }));
}

function setStatus(text) {
  els.status.textContent = text;
}

// w/h default to the collapsed size; moveNodeTo passes the measured box.
// Clamps against the live `sheet`, not a fixed canvas size -- the sheet
// only grows (applyZoom), so a node already placed near its far edge never
// becomes unreachable as the sheet grows around it.
function clampToCanvas(x, y, w = NODE_W, h = NODE_H) {
  return {
    x: Math.max(0, Math.min(sheet.w - w, x)),
    y: Math.max(0, Math.min(sheet.h - h, y)),
  };
}

const clampZoom = (z) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z));

// Grow the sheet to the zoom, then paint it. The third term in each Math.max
// is what makes the sizing monotonic in the content it holds: without it the
// sheet would shrink on zoom-in and a node parked out on a wide 50% sheet
// would fall outside the scroll range at 200% -- D-021's F2, the defect
// this task's C5 exists to keep fixed.
function applyZoom() {
  const nodes = Array.from(graphState.nodes.values());
  const maxNodeX = nodes.length ? Math.max(...nodes.map((n) => n.x)) : 0;
  const maxNodeY = nodes.length ? Math.max(...nodes.map((n) => n.y)) : 0;
  sheet.w = Math.max(
    SHEET_MIN_W,
    Math.ceil(els.wrap.clientWidth / zoom) + 2 * SHEET_PAD,
    maxNodeX + NODE_W + SHEET_PAD
  );
  sheet.h = Math.max(
    SHEET_MIN_H,
    Math.ceil(els.wrap.clientHeight / zoom) + 2 * SHEET_PAD,
    maxNodeY + NODE_H + SHEET_PAD
  );
  els.svg.setAttribute("viewBox", `0 0 ${sheet.w} ${sheet.h}`);
  els.svg.setAttribute("width", sheet.w * zoom);
  els.svg.setAttribute("height", sheet.h * zoom);
  els.canvasBg.setAttribute("width", sheet.w);
  els.canvasBg.setAttribute("height", sheet.h);
  els.zoomReadout.textContent = `${Math.round(zoom * 100)}%`;
  els.zoomIn.disabled = zoom >= ZOOM_MAX - 0.001;
  els.zoomOut.disabled = zoom <= ZOOM_MIN + 0.001;
}

// Zoom about a point, so wheel-zoom keeps whatever is under the cursor under
// the cursor. With no anchor (the buttons) it holds the centre of the
// viewport, which is the only sensible anchor with no pointer to ask.
function setZoom(next, anchorX, anchorY) {
  const prev = zoom;
  const wanted = clampZoom(next);
  if (Math.abs(wanted - prev) < 0.001) return;
  const r = els.wrap.getBoundingClientRect();
  const ax = (anchorX === undefined ? r.left + r.width / 2 : anchorX) - r.left;
  const ay = (anchorY === undefined ? r.top + r.height / 2 : anchorY) - r.top;
  const cx = (els.wrap.scrollLeft + ax) / prev;
  const cy = (els.wrap.scrollTop + ay) / prev;
  zoom = wanted;
  applyZoom();
  els.wrap.scrollLeft = cx * zoom - ax;
  els.wrap.scrollTop = cy * zoom - ay;
}

// The strip of canvas no overlay covers, in viewport-local px: between the
// two side panels, below the zoom toolbar, above the drawer.
function clearBand() {
  const v = els.wrap.getBoundingClientRect();
  const left = document.getElementById("palette").getBoundingClientRect().right;
  const right = document.getElementById("mission-panel").getBoundingClientRect().left;
  const top = document.getElementById("zoom-controls").getBoundingClientRect().bottom;
  const bottom = document.getElementById("drawer").getBoundingClientRect().top;
  return {
    x: left - v.left,
    y: top - v.top,
    w: Math.max(NODE_W, right - left),
    h: Math.max(NODE_H, bottom - top),
  };
}

// The one reset affordance (N13): scale and scroll so the whole graph is on
// screen -- a known state, which "back to 100%" is not. With no nodes yet
// there is nothing to fit around, so this just resets zoom/scroll instead of
// asking an empty #nodes-layer for a bounding box.
function fit() {
  if (graphState.nodes.size === 0) {
    zoom = 1;
    applyZoom();
    els.wrap.scrollLeft = 0;
    els.wrap.scrollTop = 0;
    return;
  }
  const bb = els.nodesLayer.getBBox();
  const band = clearBand();
  zoom = clampZoom(Math.min(band.w / (bb.width + 2 * FIT_PAD), band.h / (bb.height + 2 * FIT_PAD)));
  applyZoom();
  els.wrap.scrollLeft = bb.x * zoom - band.x - (band.w - bb.width * zoom) / 2;
  els.wrap.scrollTop = bb.y * zoom - band.y - (band.h - bb.height * zoom) / 2;
}

// A left-drag that STARTS on the paper pans; one that starts on a node moves
// that node instead (startNodeDrag/startConnectDrag, below) -- decided by
// where the drag begins, never by a mode.
function wirePan() {
  els.wrap.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0 || ev.target.closest(".node")) return;
    ev.preventDefault();
    els.wrap.setPointerCapture(ev.pointerId);
    els.wrap.classList.add("is-panning");
    let px = ev.clientX;
    let py = ev.clientY;
    function onMove(moveEv) {
      els.wrap.scrollLeft -= moveEv.clientX - px;
      els.wrap.scrollTop -= moveEv.clientY - py;
      px = moveEv.clientX;
      py = moveEv.clientY;
    }
    // lostpointercapture -- not pointerup -- so a cancelled pointer (the
    // browser taking over for a system gesture, e.g.) still tears the pan
    // down instead of leaving `is-panning` stuck and `onMove` listening
    // forever (N31): capture is released on pointerup AND pointercancel
    // alike, and this fires for both.
    function onRelease() {
      els.wrap.classList.remove("is-panning");
      els.wrap.removeEventListener("pointermove", onMove);
      els.wrap.removeEventListener("lostpointercapture", onRelease);
    }
    els.wrap.addEventListener("pointermove", onMove);
    els.wrap.addEventListener("lostpointercapture", onRelease);
  });

  // passive:false -- the page must not scroll while the canvas zooms.
  els.wrap.addEventListener(
    "wheel",
    (ev) => {
      ev.preventDefault();
      setZoom(zoom - Math.sign(ev.deltaY) * ZOOM_STEP, ev.clientX, ev.clientY);
    },
    { passive: false }
  );
}

// The node element's own rendered box (getBoundingClientRect), converted
// from screen pixels to the SVG's user-unit space via the same CTM
// clientToSvgPoint already uses -- not the foreignObject, which D-015 never
// resizes past its collapsed width/height for an opened node.
// Takes the already-looked-up foreignObject rather than an id: every caller
// routes through moveNodeTo, which only ever runs once a node is already
// rendered (growNode bails out first if it is not), so there is exactly one
// DOM query per move, not two.
function measuredSize(fo) {
  const div = fo.querySelector(".node");
  const r = div.getBoundingClientRect();
  const p1 = clientToSvgPoint(r.left, r.top);
  const p2 = clientToSvgPoint(r.right, r.bottom);
  return { w: p2.x - p1.x, h: p2.y - p1.y };
}

function nextSpawnPoint() {
  const perRow = 4;
  const i = graphState.spawnIndex++;
  const col = i % perRow;
  const row = Math.floor(i / perRow);
  return clampToCanvas(16 + col * 172, 16 + row * 132);
}

function clientToSvgPoint(clientX, clientY) {
  const pt = els.svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  return pt.matrixTransform(els.svg.getScreenCTM().inverse());
}

function foreignObjectFor(id) {
  return els.nodesLayer.querySelector(`foreignObject[data-node-id="${id}"]`);
}

// C2/C4: the node grows in place -- no flyout, no guessed pixel numbers.
// D-013 measured the opened footprint against its own (not-yet-shipped) CSS
// and found the width constant across modes, only height varies; here there
// is no CSS yet, so height is resized to whatever the unstyled content
// actually measures, every time that content changes. Width is left alone --
// a block element's "auto" width fills its foreignObject container rather
// than shrinking to its content, so measuring it would just read back
// whatever width was set last, not the content's real size.
function growNode(id) {
  const fo = foreignObjectFor(id);
  if (!fo) return;
  const div = fo.querySelector(".node");
  if (!div) return;
  // .node is height:100% of the foreignObject, so scrollHeight would just
  // read back whatever height was set last -- never shrinking on re-collapse
  // -- unless the fo is first reset to its floor, forcing the (now shorter)
  // interior to overflow it before the real content height is measured.
  fo.setAttribute("height", NODE_H);
  fo.setAttribute("height", Math.max(NODE_H, Math.ceil(div.scrollHeight)));
  // Re-clamp against the freshly measured box -- growing near an edge (not
  // just dragging into one) must not spill the node off the canvas either.
  const node = graphState.nodes.get(id);
  if (node) {
    moveNodeTo(id, node.x, node.y);
    persistUI();
  }
}

function portCenterSvg(id, role) {
  const sel = `.node[data-node-id="${id}"] .port--${role}`;
  const portEl = els.wrap.querySelector(sel);
  if (!portEl) return null;
  const r = portEl.getBoundingClientRect();
  return clientToSvgPoint(r.left + r.width / 2, r.top + r.height / 2);
}

function renderEdges() {
  els.edgesLayer.textContent = "";
  graphState.edges.forEach(([from, to]) => {
    const p1 = portCenterSvg(from, "out");
    const p2 = portCenterSvg(to, "in");
    if (!p1 || !p2) return;
    const midX = (p1.x + p2.x) / 2;
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("class", "edge");
    path.setAttribute("d", `M ${p1.x} ${p1.y} C ${midX} ${p1.y}, ${midX} ${p2.y}, ${p2.x} ${p2.y}`);
    path.setAttribute("marker-end", "url(#canvas-arrowhead)");
    els.edgesLayer.appendChild(path);
  });
}

function moveNodeTo(id, x, y) {
  const n = graphState.nodes.get(id);
  if (!n) return;
  const fo = foreignObjectFor(id);
  const { w, h } = measuredSize(fo);
  const clamped = clampToCanvas(x, y, w, h);
  n.x = clamped.x;
  n.y = clamped.y;
  fo.setAttribute("x", clamped.x);
  fo.setAttribute("y", clamped.y);
  renderEdges();
}

// Cycle 2 F5: the four node interiors below (Observable, Selection,
// Multiplicity, Histogram) each open the same way -- bring the node to the
// end of #nodes-layer so its grown box paints over whatever else sits at
// that canvas position (SVG has no z-index), and refocus the summary that
// reparenting under `appendChild` otherwise drops focus from (C6/C8).
function wireInteriorToggle(details, summary, id) {
  details.addEventListener("toggle", () => {
    if (details.open) {
      els.nodesLayer.appendChild(foreignObjectFor(id));
      summary.focus();
    }
    growNode(id);
  });
}

// ---- Observable node interior (F-006, docs/design-explorations/observable.html) ----

function h(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  });
  children.forEach((c) => node.appendChild(c));
  return node;
}

// Module scope: both buildObservableInterior (the toggle) and buildNodeEl
// (the initial subtitle, C9) need the same four modes and labels.
const MODES = [
  { value: "ObsGlobal", label: "Global" },
  { value: "ObsObject", label: "Object" },
  { value: "ObsVectorSum", label: "Vector sum" },
  { value: "ObsCustom", label: "Custom" },
];

// F-011, plan "Decisions" #3: a freshly placed node must already run.
// VectorSum(l1, l2, mass) is the default for every mode's own fallback too.
const DEFAULT_MODE = "ObsVectorSum";
const DEFAULT_VECTOR_SUM_OBJECTS = ["l1", "l2"];

function propertyOptions(select, objectName) {
  select.textContent = "";
  OBJECT_PROPERTIES[objectName].forEach((propName) => {
    const prop = PROPERTIES.find((p) => p.name === propName);
    select.appendChild(h("option", { value: prop.name, text: prop.label }));
  });
}

// Global: a count, or MET pt (plan table row 1).
function buildGlobalPanel(uid, onChange) {
  const wrap = h("div", { class: "obs-panel" });
  const select = h("select", { id: uid("global-qty"), name: uid("global-qty") });
  COUNTS.forEach((c) => select.appendChild(h("option", { value: c.name, text: c.label })));
  select.appendChild(h("option", { value: "met_pt", text: globalConfig("met_pt").label }));
  select.addEventListener("change", onChange);
  wrap.appendChild(h("label", { for: uid("global-qty"), text: "Quantity" }));
  wrap.appendChild(select);
  return {
    el: wrap,
    getConfig: () => globalConfig(select.value),
    // F-012, C3: met_pt has no COUNTS entry of its own -- it is a physical
    // pt like any object's, so its preset comes from PROPERTIES' "pt".
    getRange: () =>
      select.value === "met_pt"
        ? PROPERTIES.find((p) => p.name === "pt").range
        : COUNTS.find((c) => c.name === select.value).range,
  };
}

// Object: object + property (plan table row 2).
function buildObjectPanel(uid, onChange) {
  const wrap = h("div", { class: "obs-panel" });
  const objSelect = h("select", { id: uid("obj-object"), name: uid("obj-object") });
  OBJECTS.forEach((o) => objSelect.appendChild(h("option", { value: o.name, text: o.label })));
  const propSelect = h("select", { id: uid("obj-property"), name: uid("obj-property") });
  propertyOptions(propSelect, objSelect.value);

  objSelect.addEventListener("change", () => {
    propertyOptions(propSelect, objSelect.value);
    onChange();
  });
  propSelect.addEventListener("change", onChange);

  wrap.appendChild(h("label", { for: uid("obj-object"), text: "Object" }));
  wrap.appendChild(objSelect);
  wrap.appendChild(h("label", { for: uid("obj-property"), text: "Property" }));
  wrap.appendChild(propSelect);
  return {
    el: wrap,
    getConfig: () => objectConfig(objSelect.value, propSelect.value),
    getRange: () => PROPERTIES.find((p) => p.name === propSelect.value).range,
  };
}

// VectorSum: tick objects, then mass or pt (plan table row 3, default).
function buildVectorSumPanel(uid, onChange) {
  const wrap = h("div", { class: "obs-panel" });
  const fieldset = h("fieldset", {});
  fieldset.appendChild(h("legend", { text: "Objects to sum" }));
  const checkboxes = VECTOR_SUM_OBJECTS.map((o) => {
    const cbId = uid(`vs-${o.name}`);
    const input = h("input", { type: "checkbox", id: cbId, name: uid("vs"), value: o.name });
    if (DEFAULT_VECTOR_SUM_OBJECTS.includes(o.name)) input.checked = true;
    fieldset.appendChild(h("span", { class: "obs-panel__opt" }, [input, h("label", { for: cbId, text: o.label })]));
    return input;
  });
  // At least one object must stay ticked -- an empty sum is not an
  // expression. Reverting a would-be-empty uncheck is cheaper than a
  // validation message for a control this small.
  checkboxes.forEach((cb) => {
    cb.addEventListener("change", () => {
      if (!checkboxes.some((c) => c.checked)) {
        cb.checked = true;
        return;
      }
      onChange();
    });
  });
  wrap.appendChild(fieldset);

  const qtySelect = h("select", { id: uid("vs-qty"), name: uid("vs-qty") });
  VECTOR_SUM_QUANTITIES.forEach((q) => qtySelect.appendChild(h("option", { value: q.name, text: q.label })));
  qtySelect.addEventListener("change", onChange);
  wrap.appendChild(h("label", { for: uid("vs-qty"), text: "Quantity" }));
  wrap.appendChild(qtySelect);

  return {
    el: wrap,
    getConfig: () => {
      const objects = checkboxes.filter((c) => c.checked).map((c) => c.value);
      return vectorSumConfig(objects, qtySelect.value);
    },
    getRange: () => VECTOR_SUM_QUANTITIES.find((q) => q.name === qtySelect.value).range,
  };
}

// Custom: one free-text field (plan table row 4) -- the one mode whose
// expression the student types rather than builds from controls.
function buildCustomPanel(uid, onChange) {
  const wrap = h("div", { class: "obs-panel" });
  const input = h("input", { type: "text", id: uid("custom-expr"), name: uid("custom-expr") });
  input.value = objectConfig("l1", "pt").expr;
  input.addEventListener("input", onChange);
  wrap.appendChild(h("label", { for: uid("custom-expr"), text: "Custom expression" }));
  wrap.appendChild(input);
  // No known preset for free text -- C3 only re-presets for the three
  // vocabulary-backed modes.
  return { el: wrap, getConfig: () => customConfig(input.value), getRange: () => null };
}

// One `Observable` node, one in-node mode toggle -- the 2026-09-02 ruling
// (docs/design-brief.md §4): ObsGlobal/ObsObject/ObsVectorSum/ObsCustom are
// not four palette kinds, they are one node's `config.mode`. A native
// <details> is the grow-in-place affordance (C2 -- no flyout), and a native
// radio <fieldset> is the toggle (C1) -- both keyboard-operable and
// self-naming for free, which is what C5 checks.
//
// F-011 wires each mode's own native controls (docs/plan-m4-recipe-builder.md
// table) into `config` through expr.js -- the panel builders above. Every
// control lives inside this one <details>; the inactive panels are `hidden`
// (native, so a screen reader skips them) rather than removed, so switching
// modes never rebuilds DOM.
function buildObservableInterior(id) {
  const uid = (s) => `obs-${s}-${id}`;

  const details = h("details", { class: "node__interior" });
  const summary = h("summary", { class: "node__interior-summary", text: "Configure observable" });
  details.appendChild(summary);

  const fieldset = h("fieldset", { class: "mode-toggle" });
  fieldset.appendChild(h("legend", { class: "mode-toggle__legend", text: "Mode — what number am I plotting?" }));
  const radios = MODES.map((m) => {
    const radioId = uid(`mode-${m.value}`);
    const input = h("input", { type: "radio", name: uid("mode"), id: radioId, value: m.value });
    if (m.value === DEFAULT_MODE) input.checked = true;
    fieldset.appendChild(h("span", { class: "mode-toggle__opt" }, [input, h("label", { for: radioId, text: m.label })]));
    return input;
  });
  details.appendChild(fieldset);

  function update() {
    const mode = radios.find((r) => r.checked).value;
    const cfg = panels[mode].getConfig();
    const range = panels[mode].getRange();
    const n = graphState.nodes.get(id);
    if (n) {
      n.config = { mode, ...cfg };
      // Not sent to the server -- persistUI only reads id/kind/x/y/config --
      // just this node's own memory of its current preset, for C3's
      // connect-time push and for attemptConnect below.
      n.rangePreset = range;
      persistUI();
    }
    const sub = els.wrap.querySelector(`.node[data-node-id="${id}"] .node__subtitle`);
    if (sub) sub.textContent = MODES.find((m) => m.value === mode).label;
    Object.entries(panels).forEach(([m, p]) => {
      p.el.hidden = m !== mode;
    });
    growNode(id);
    // C3/F1: an already-connected Histogram re-presets to this quantity's
    // range/label. Custom mode has no range (`getRange()` returns `null`),
    // but its label still reaches the Histogram's axis -- applyPreset only
    // skips min/max when `range` is falsy, never the label.
    graphState.edges
      .filter(([from, to]) => from === id && histogramInteriors.has(to))
      .forEach(([, to]) => histogramInteriors.get(to)(range, cfg.label));
  }

  const panels = {
    ObsGlobal: buildGlobalPanel(uid, update),
    ObsObject: buildObjectPanel(uid, update),
    ObsVectorSum: buildVectorSumPanel(uid, update),
    ObsCustom: buildCustomPanel(uid, update),
  };
  Object.values(panels).forEach((p) => details.appendChild(p.el));

  radios.forEach((r) => r.addEventListener("change", update));
  // C9: the default mode's config is already what `config` exports, so the
  // subtitle says so from the start too -- buildNodeEl sets the same
  // DEFAULT_MODE label before this node is even appended to the page. This
  // first call's DOM lookups (subtitle, foreignObject) are guarded no-ops,
  // since the node is not attached to the page yet -- only node.config and
  // panel visibility land at this point.
  update();

  wireInteriorToggle(details, summary, id);

  return details;
}

// One `Selection` node's interior: rows of object · property · comparison ·
// number, ANDed server-side (`fce_web.graph._selection_exprs`). Plan table
// row 2 -- default one row, "1st lepton pt > 5"; zero rows is legal (an
// empty `exprs` list is an unconditional pass, confirmed by scout Q1).
function buildSelectionInterior(id) {
  const uid = (s) => `sel-${s}-${id}`;
  let rowSeq = 0;
  const rows = []; // { el, getExpr() }

  const details = h("details", { class: "node__interior" });
  const summary = h("summary", { class: "node__interior-summary", text: "Configure selection" });
  details.appendChild(summary);

  const list = h("div", { class: "selection-rows" });
  details.appendChild(list);

  function update() {
    const n = graphState.nodes.get(id);
    if (n) {
      n.config = { exprs: rows.map((r) => r.getExpr()) };
      persistUI();
    }
    growNode(id);
  }

  function addRow(defaults) {
    rowSeq += 1;
    const rid = uid(`row-${rowSeq}`);
    const row = h("div", { class: "selection-row" });

    const objSelect = h("select", { id: `${rid}-object`, name: `${rid}-object` });
    OBJECTS.forEach((o) => objSelect.appendChild(h("option", { value: o.name, text: o.label })));
    const propSelect = h("select", { id: `${rid}-property`, name: `${rid}-property` });
    propertyOptions(propSelect, objSelect.value);
    const cmpSelect = h("select", { id: `${rid}-comparison`, name: `${rid}-comparison` });
    COMPARISONS.forEach((c) => cmpSelect.appendChild(h("option", { value: c.op, text: c.label })));
    const valInput = h("input", { type: "number", id: `${rid}-value`, name: `${rid}-value`, step: "any" });

    if (defaults) {
      objSelect.value = defaults.object;
      propertyOptions(propSelect, objSelect.value);
      propSelect.value = defaults.property;
      cmpSelect.value = defaults.comparison;
      valInput.value = defaults.value;
    }

    objSelect.addEventListener("change", () => {
      propertyOptions(propSelect, objSelect.value);
      update();
    });
    propSelect.addEventListener("change", update);
    cmpSelect.addEventListener("change", update);
    valInput.addEventListener("input", update);

    const removeBtn = h("button", {
      type: "button",
      class: "selection-remove",
      text: "Remove condition",
      "aria-label": `Remove condition ${rowSeq}`,
    });
    removeBtn.addEventListener("click", () => {
      list.removeChild(row);
      const idx = rows.findIndex((r) => r.el === row);
      if (idx >= 0) rows.splice(idx, 1);
      update();
    });

    row.appendChild(h("label", { for: `${rid}-object`, text: "Object" }));
    row.appendChild(objSelect);
    row.appendChild(h("label", { for: `${rid}-property`, text: "Property" }));
    row.appendChild(propSelect);
    row.appendChild(h("label", { for: `${rid}-comparison`, text: "Comparison" }));
    row.appendChild(cmpSelect);
    row.appendChild(h("label", { for: `${rid}-value`, text: "Value" }));
    row.appendChild(valInput);
    row.appendChild(removeBtn);

    list.appendChild(row);
    rows.push({
      el: row,
      getExpr: () => buildSelectionExpr(objSelect.value, propSelect.value, cmpSelect.value, valInput.value),
    });
  }

  const addBtn = h("button", { type: "button", class: "selection-add", text: "Add condition" });
  addBtn.addEventListener("click", () => {
    addRow();
    update();
  });
  details.appendChild(addBtn);

  addRow({ object: "l1", property: "pt", comparison: ">", value: "5" });
  update();

  wireInteriorToggle(details, summary, id);

  return details;
}

// ---- Multiplicity node interior (F-012) --------------------------------
//
// One fieldset per object kind (leptons, jets, photons): a comparison and a
// count. Leptons also carry the lepton-type radio the plan's Answers block
// enumerates. Default, plan "The design": exactly 2 leptons, jets and
// photons unconstrained (">=" 0), lepton type Any -- a freshly placed node
// already runs (F-011's Decisions #3).
function buildMultCountGroup(uid, kind, legendText, defaultCount, defaultOp, onChange) {
  const wrap = h("fieldset", { class: "mult-group" });
  wrap.appendChild(h("legend", { text: legendText }));

  const opSelect = h("select", { id: uid(`${kind}-op`), name: uid(`${kind}-op`) });
  MULT_COMPARISONS.forEach((c) => opSelect.appendChild(h("option", { value: c.op, text: c.label })));
  opSelect.value = defaultOp;
  opSelect.addEventListener("change", onChange);

  const countInput = h("input", { type: "number", min: "0", id: uid(`${kind}-count`), name: uid(`${kind}-count`) });
  countInput.value = String(defaultCount);
  countInput.addEventListener("input", onChange);

  wrap.appendChild(h("label", { for: uid(`${kind}-op`), text: "Comparison" }));
  wrap.appendChild(opSelect);
  wrap.appendChild(h("label", { for: uid(`${kind}-count`), text: "Count" }));
  wrap.appendChild(countInput);

  // Cycle 2 F3: no `|| 0` fallback -- a blank/non-numeric count must reach
  // the server as something it rejects (NaN serialises to `null` in JSON,
  // which graph.py's int check refuses), the same way a blank Histogram
  // bins field is left to the server's own validation rather than silently
  // becoming "exactly 0".
  return { el: wrap, getOp: () => opSelect.value, getCount: () => parseInt(countInput.value, 10) };
}

function buildMultiplicityInterior(id) {
  const uid = (s) => `mult-${s}-${id}`;

  const details = h("details", { class: "node__interior" });
  const summary = h("summary", { class: "node__interior-summary", text: "Configure multiplicity" });
  details.appendChild(summary);

  function update() {
    const n = graphState.nodes.get(id);
    if (n) {
      n.config = {
        nlep: lepGroup.getCount(),
        op_lep: lepGroup.getOp(),
        njets: jetGroup.getCount(),
        op_jet: jetGroup.getOp(),
        ltype: ltypeSelect.value,
        nphot: photGroup.getCount(),
        op_phot: photGroup.getOp(),
      };
      persistUI();
    }
    growNode(id);
  }

  const lepGroup = buildMultCountGroup(uid, "lep", "Leptons", 2, "==", update);
  const ltypeSelect = h("select", { id: uid("ltype"), name: uid("ltype") });
  LEPTON_TYPES.forEach((t) => ltypeSelect.appendChild(h("option", { value: t.value, text: t.label })));
  ltypeSelect.addEventListener("change", update);
  lepGroup.el.appendChild(h("label", { for: uid("ltype"), text: "Lepton type" }));
  lepGroup.el.appendChild(ltypeSelect);

  const jetGroup = buildMultCountGroup(uid, "jet", "Jets", 0, ">=", update);
  const photGroup = buildMultCountGroup(uid, "phot", "Photons", 0, ">=", update);

  details.appendChild(lepGroup.el);
  details.appendChild(jetGroup.el);
  details.appendChild(photGroup.el);

  update();

  wireInteriorToggle(details, summary, id);

  return details;
}

// ---- Histogram node interior (F-012) -----------------------------------
//
// bins/min/max as number inputs; x_label is not its own control -- it
// mirrors whatever the connected Observable's quantity is called (C3),
// blank when nothing is connected. Default 50 bins, 0-150 (plan table's
// "with no Observable connected" case).
function buildHistogramInterior(id) {
  const uid = (s) => `hist-${s}-${id}`;
  let xLabel = "";

  const details = h("details", { class: "node__interior" });
  const summary = h("summary", { class: "node__interior-summary", text: "Configure histogram" });
  details.appendChild(summary);

  const binsInput = h("input", { type: "number", min: "1", id: uid("bins"), name: uid("bins") });
  binsInput.value = "50";
  const minInput = h("input", { type: "number", id: uid("min"), name: uid("min") });
  minInput.value = "0";
  const maxInput = h("input", { type: "number", id: uid("max"), name: uid("max") });
  maxInput.value = "150";

  function update() {
    const n = graphState.nodes.get(id);
    if (n) {
      n.config = { bins: binsInput.value, min: minInput.value, max: maxInput.value, x_label: xLabel };
      persistUI();
    }
    growNode(id);
  }

  [binsInput, minInput, maxInput].forEach((inp) => inp.addEventListener("input", update));

  details.appendChild(h("label", { for: uid("bins"), text: "Bins" }));
  details.appendChild(binsInput);
  details.appendChild(h("label", { for: uid("min"), text: "Minimum" }));
  details.appendChild(minInput);
  details.appendChild(h("label", { for: uid("max"), text: "Maximum" }));
  details.appendChild(maxInput);

  // C3: exposed so a connected Observable's update() (and attemptConnect,
  // on first connect) can push its quantity's preset here -- looked up by
  // node id through graphState.edges, not a second graph model. Cycle 2 F1:
  // a `range` of `null` (Custom mode has none) still updates the axis label
  // -- only min/max are skipped -- so switching to Custom does not leave a
  // stale label from whatever the previous mode was showing.
  histogramInteriors.set(id, (range, label) => {
    if (range) {
      minInput.value = String(range[0]);
      maxInput.value = String(range[1]);
    }
    xLabel = label;
    update();
  });

  update();

  wireInteriorToggle(details, summary, id);

  return details;
}

function buildNodeEl(id, kind) {
  const meta = KIND_BY_NAME[kind];
  const { x, y } = graphState.nodes.get(id);

  const fo = document.createElementNS(SVG_NS, "foreignObject");
  fo.setAttribute("x", x);
  fo.setAttribute("y", y);
  fo.setAttribute("width", NODE_W);
  fo.setAttribute("height", NODE_H);
  fo.setAttribute("data-node-id", id);

  const div = document.createElement("div");
  div.className = `node node--${meta.cls}`;
  div.dataset.nodeId = id;
  div.dataset.nodeKind = kind;

  const handle = document.createElement("button");
  handle.type = "button";
  handle.className = "node__handle";
  handle.setAttribute("aria-label", `Move ${meta.label} (${id}). Drag, or use arrow keys.`);
  const title = document.createElement("span");
  title.className = "node__title";
  title.textContent = meta.label;
  handle.appendChild(title);
  div.appendChild(handle);

  const sub = document.createElement("p");
  sub.className = "node__subtitle";
  sub.textContent = kind === "Observable" ? MODES.find((m) => m.value === DEFAULT_MODE).label : "not configured yet";
  div.appendChild(sub);

  const ports = document.createElement("div");
  ports.className = "node__ports";

  if (meta.hasIn) {
    const inPort = document.createElement("button");
    inPort.type = "button";
    inPort.className = "port port--in";
    inPort.dataset.role = "in";
    inPort.setAttribute("aria-label", `Connect in to ${meta.label} (${id})`);
    inPort.addEventListener("keydown", (ev) => handleInKey(id, ev));
    ports.appendChild(inPort);
  }

  if (meta.hasOut) {
    const outPort = document.createElement("button");
    outPort.type = "button";
    outPort.className = "port port--out";
    outPort.dataset.role = "out";
    outPort.setAttribute("aria-label", `Connect out from ${meta.label} (${id})`);
    outPort.setAttribute("aria-pressed", "false");
    outPort.addEventListener("pointerdown", (ev) => startConnectDrag(id, outPort, ev));
    outPort.addEventListener("keydown", (ev) => handleOutKey(id, ev));
    ports.appendChild(outPort);
  }

  div.appendChild(ports);

  if (kind === "Observable") {
    div.appendChild(buildObservableInterior(id));
  } else if (kind === "Selection") {
    div.appendChild(buildSelectionInterior(id));
  } else if (kind === "Multiplicity") {
    div.appendChild(buildMultiplicityInterior(id));
  } else if (kind === "Histogram") {
    div.appendChild(buildHistogramInterior(id));
  }

  fo.appendChild(div);

  handle.addEventListener("pointerdown", (ev) => startNodeDrag(id, handle, ev));
  handle.addEventListener("keydown", (ev) => handleHandleKey(id, ev));

  return fo;
}

function addNode(kind) {
  const id = `n${graphState.nextId}`;
  graphState.nextId += 1;
  const { x, y } = nextSpawnPoint();
  graphState.nodes.set(id, { kind, x, y });
  const fo = buildNodeEl(id, kind);
  els.nodesLayer.appendChild(fo);
  persistUI();
  return id;
}

// ---- pointer drag: repositioning a node ------------------------------
function startNodeDrag(id, handleEl, ev) {
  if (ev.button !== undefined && ev.button !== 0) return;
  ev.preventDefault();
  handleEl.setPointerCapture(ev.pointerId);
  const startPt = clientToSvgPoint(ev.clientX, ev.clientY);
  const node = graphState.nodes.get(id);
  const originX = node.x;
  const originY = node.y;

  function onMove(moveEv) {
    const cur = clientToSvgPoint(moveEv.clientX, moveEv.clientY);
    moveNodeTo(id, originX + (cur.x - startPt.x), originY + (cur.y - startPt.y));
  }
  function onUp() {
    handleEl.removeEventListener("pointermove", onMove);
    handleEl.removeEventListener("pointerup", onUp);
    handleEl.removeEventListener("pointercancel", onUp);
    persistUI();
  }
  handleEl.addEventListener("pointermove", onMove);
  handleEl.addEventListener("pointerup", onUp);
  handleEl.addEventListener("pointercancel", onUp);
}

function handleHandleKey(id, ev) {
  const step = ev.shiftKey ? NUDGE_BIG : NUDGE;
  const node = graphState.nodes.get(id);
  let dx = 0;
  let dy = 0;
  if (ev.key === "ArrowLeft") dx = -step;
  else if (ev.key === "ArrowRight") dx = step;
  else if (ev.key === "ArrowUp") dy = -step;
  else if (ev.key === "ArrowDown") dy = step;
  else return;
  ev.preventDefault();
  moveNodeTo(id, node.x + dx, node.y + dy);
  persistUI();
  setStatus(`${nodeLabel(id)} moved to (${Math.round(node.x)}, ${Math.round(node.y)}).`);
}

// ---- pointer drag: connecting two nodes -------------------------------
function startConnectDrag(id, portEl, ev) {
  if (ev.button !== undefined && ev.button !== 0) return;
  ev.preventDefault();
  clearKeyboardArm();
  const kind = graphState.nodes.get(id).kind;
  portEl.setPointerCapture(ev.pointerId);

  const start = portCenterSvg(id, "out");
  const dragLine = document.createElementNS(SVG_NS, "line");
  dragLine.setAttribute("class", "edge edge--drag");
  dragLine.setAttribute("x1", start.x);
  dragLine.setAttribute("y1", start.y);
  dragLine.setAttribute("x2", start.x);
  dragLine.setAttribute("y2", start.y);
  els.edgesLayer.appendChild(dragLine);
  setStatus(`Dragging from ${nodeLabel(id)} -- drop on an input port to connect.`);

  let lastTargetPort = null;

  function clearTargetHighlight() {
    if (lastTargetPort) {
      lastTargetPort.classList.remove("port--drag-target");
      lastTargetPort = null;
    }
  }

  function onMove(moveEv) {
    const cur = clientToSvgPoint(moveEv.clientX, moveEv.clientY);
    dragLine.setAttribute("x2", cur.x);
    dragLine.setAttribute("y2", cur.y);
    const under = document.elementFromPoint(moveEv.clientX, moveEv.clientY);
    const targetPort = under ? under.closest(".port--in") : null;
    if (targetPort !== lastTargetPort) {
      clearTargetHighlight();
      if (targetPort) {
        targetPort.classList.add("port--drag-target");
        lastTargetPort = targetPort;
      }
    }
  }

  function cleanup() {
    portEl.removeEventListener("pointermove", onMove);
    portEl.removeEventListener("pointerup", onUp);
    portEl.removeEventListener("pointercancel", onCancel);
    clearTargetHighlight();
    dragLine.remove();
  }

  function onUp(upEv) {
    cleanup();
    const under = document.elementFromPoint(upEv.clientX, upEv.clientY);
    const targetPort = under ? under.closest(".port--in") : null;
    if (!targetPort) {
      setStatus("Connection cancelled -- you did not drop on an input port.");
      return;
    }
    const targetNodeEl = targetPort.closest(".node");
    const toId = targetNodeEl ? targetNodeEl.dataset.nodeId : null;
    attemptConnect(id, kind, toId);
  }
  function onCancel() {
    cleanup();
  }

  portEl.addEventListener("pointermove", onMove);
  portEl.addEventListener("pointerup", onUp);
  portEl.addEventListener("pointercancel", onCancel);
}

function attemptConnect(fromId, fromKind, toId) {
  if (!toId || toId === fromId) {
    setStatus("A node cannot connect to itself.");
    return;
  }
  if (graphState.edges.some(([f, t]) => f === fromId && t === toId)) {
    setStatus(`Already connected: ${nodeLabel(fromId)} → ${nodeLabel(toId)}.`);
    return;
  }
  const toKind = graphState.nodes.get(toId).kind;
  if (isLegal(fromKind, toKind)) {
    graphState.edges.push([fromId, toId]);
    persistUI();
    renderEdges();
    // C3/F1: a Histogram connected to an already-configured Observable
    // starts at that quantity's preset (or, in Custom mode, at least its
    // label), not whatever it defaulted to alone.
    if (fromKind === "Observable" && histogramInteriors.has(toId)) {
      const fromNode = graphState.nodes.get(fromId);
      histogramInteriors.get(toId)(fromNode.rangePreset, fromNode.config.label);
    }
    setStatus(`Connected: ${nodeLabel(fromId)} → ${nodeLabel(toId)}.`);
  } else {
    setStatus(`Refused: ${KIND_BY_NAME[fromKind].label} cannot connect to ${KIND_BY_NAME[toKind].label}.`);
  }
}

// ---- keyboard path: arm an out-port with Enter/Space, complete on an
// in-port the same way. Routed through `keydown`, never `click` -- a native
// <button> also fires a synthetic `click` on Enter/Space, and this file has
// no `click` listener on any port, so a plain mouse click triggers nothing.
// That is what makes click-to-connect refused by construction, ported
// unchanged from bench.html's own reasoning (handleOutKey/handleInKey).
function handleOutKey(id, ev) {
  if (ev.key !== "Enter" && ev.key !== " ") return;
  ev.preventDefault();
  const outPort = els.wrap.querySelector(`.node[data-node-id="${id}"] .port--out`);
  if (graphState.keyboardArmed && graphState.keyboardArmed.id === id) {
    clearKeyboardArm();
    setStatus("Connection cancelled.");
    return;
  }
  clearKeyboardArm();
  graphState.keyboardArmed = { id, kind: graphState.nodes.get(id).kind };
  outPort.classList.add("port--armed");
  outPort.setAttribute("aria-pressed", "true");
  setStatus(
    `Armed from ${nodeLabel(id)} -- Tab to an input port and press Enter to finish, or press Enter here again to cancel.`
  );
}

function handleInKey(id, ev) {
  if (ev.key !== "Enter" && ev.key !== " ") return;
  ev.preventDefault();
  if (!graphState.keyboardArmed) {
    setStatus("Press Enter on an output port first, then Enter on an input port, to connect two nodes.");
    return;
  }
  const { id: fromId, kind: fromKind } = graphState.keyboardArmed;
  clearKeyboardArm();
  attemptConnect(fromId, fromKind, id);
}

function clearKeyboardArm() {
  if (!graphState.keyboardArmed) return;
  const prev = els.wrap.querySelector(`.node[data-node-id="${graphState.keyboardArmed.id}"] .port--out`);
  if (prev) {
    prev.classList.remove("port--armed");
    prev.setAttribute("aria-pressed", "false");
  }
  graphState.keyboardArmed = null;
}

function wirePalette() {
  els.paletteButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const kind = btn.dataset.addKind;
      addNode(kind);
      setStatus(`Added a new ${KIND_BY_NAME[kind].label} node.`);
    });
  });
}

function init() {
  els = {
    wrap: document.getElementById("canvas-wrap"),
    svg: document.getElementById("canvas-svg"),
    canvasBg: document.getElementById("canvas-bg"),
    nodesLayer: document.getElementById("nodes-layer"),
    edgesLayer: document.getElementById("edges-layer"),
    status: document.getElementById("canvas-status"),
    paletteButtons: Array.from(document.querySelectorAll(".palette__add")),
    zoomIn: document.getElementById("zoom-in"),
    zoomOut: document.getElementById("zoom-out"),
    zoomFit: document.getElementById("zoom-fit"),
    zoomReadout: document.getElementById("zoom-readout"),
  };
  wirePalette();
  wirePan();
  els.zoomIn.addEventListener("click", () => setZoom(zoom + ZOOM_STEP));
  els.zoomOut.addEventListener("click", () => setZoom(zoom - ZOOM_STEP));
  els.zoomFit.addEventListener("click", fit);
  // A window resize changes how much sheet the viewport needs; same one call
  // applyZoom already uses for a zoom change.
  window.addEventListener("resize", applyZoom);
  applyZoom();
  persistUI();
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && graphState.keyboardArmed) {
      clearKeyboardArm();
      setStatus("Connection cancelled.");
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
