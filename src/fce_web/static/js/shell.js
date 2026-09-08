// Wires the three-region app shell (templates/shell.html), ported from
// docs/design-explorations/shell.html per F-004. See that file's own header
// comment for the design history (D-010, D-014).
//
// Two independent pieces of state, kept deliberately apart:
//
//   graphState  — nodes + edges. What buildRunPayload() serialises. The
//                 engine's business, per docs/design-brief.md §4.
//   ui toggles  — palette/panel collapsed-or-expanded, the pager index,
//                 which node is open. Never read by buildRunPayload().
//                 The brief calls this the "ui object" the engine never
//                 reads; here it is not even the same object, so there is
//                 no field to forget to strip.

const SVG_NS = "http://www.w3.org/2000/svg";

// The opened-node footprint D-013 settled on (ObsVectorSum, the widest of
// the four Observable modes) and the collapsed footprint beside it. Used
// only to size and clamp the two exemplar canvas nodes below — never
// written into CSS, which sizes a grown node card at 100%/100% of whatever
// box these numbers give its foreignObject.
const NODE_OPEN_W = 328.0;
const NODE_OPEN_H = 300.0;
const NODE_COLLAPSED_W = 80.5;
const NODE_COLLAPSED_H = 68;

const CANVAS_W = 704;
const CANVAS_H = 512;

// ---- the run payload's own state — untouched by any ui toggle below -----
const graphState = {
  nodes: [
    { id: "n1", kind: "Observable" },
    { id: "n2", kind: "Histogram" },
  ],
  edges: [["n1", "n2"]],
};

function buildRunPayload() {
  return {
    nodes: graphState.nodes.map((n) => ({ id: n.id, kind: n.kind })),
    edges: graphState.edges.map(([a, b]) => [a, b]),
  };
}

// ---- exemplar canvas nodes -----------------------------------------------
// n1 sits near the canvas's own bottom-right corner: opening it to its full
// 328x300 footprint, unclamped, would run past both the right and the
// bottom visible edge. n2 sits where that unclamped footprint would land,
// so opening n1 is also the overlap case. F-005 replaces these with the
// real graph; they exist here only so the shell has something to show.
const nodePositions = {
  n1: {
    x: CANVAS_W - NODE_COLLAPSED_W - 20,
    y: CANVAS_H - NODE_COLLAPSED_H - 20,
    kind: "Observable",
    cls: "observable",
    title: "Observable — vector sum",
    body: "Add lepton 1 + lepton 2, then read off mass.",
  },
  n2: {
    x: 550,
    y: 300,
    kind: "Histogram",
    cls: "histogram",
    title: "Histogram",
    body: "40 bins, 0–120 GeV.",
  },
};

let nodesLayer = null;
const nodeEls = {};

function makeNodeCard(id, pos) {
  const fo = document.createElementNS(SVG_NS, "foreignObject");
  fo.setAttribute("data-node-id", id);
  fo.setAttribute("data-open", "false");
  fo.setAttribute("x", pos.x);
  fo.setAttribute("y", pos.y);
  fo.setAttribute("width", NODE_COLLAPSED_W);
  fo.setAttribute("height", NODE_COLLAPSED_H);

  const div = document.createElement("div");
  div.className = `node-card node-card--${pos.cls}`;
  div.dataset.nodeId = id;
  div.dataset.nodeKind = pos.kind;

  const title = document.createElement("p");
  title.className = "node-card__title";
  title.textContent = pos.title;

  const body = document.createElement("p");
  body.className = "node-card__body";
  body.textContent = pos.body;

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "node-card__toggle";
  toggle.setAttribute("aria-expanded", "false");
  toggle.setAttribute("aria-label", `Open ${pos.title}`);
  toggle.textContent = "open";
  toggle.addEventListener("click", () => toggleNode(id));

  div.append(title, body, toggle);
  fo.appendChild(div);
  return { fo, div, toggle };
}

function toggleNode(id) {
  const pos = nodePositions[id];
  const { fo, div, toggle } = nodeEls[id];
  const isOpen = fo.getAttribute("data-open") === "true";

  if (isOpen) {
    fo.setAttribute("width", NODE_COLLAPSED_W);
    fo.setAttribute("height", NODE_COLLAPSED_H);
    fo.setAttribute("x", pos.x);
    fo.setAttribute("y", pos.y);
    fo.setAttribute("data-open", "false");
    div.classList.remove("node-card--open");
    toggle.setAttribute("aria-expanded", "false");
    toggle.textContent = "open";
  } else {
    // Grow to the opened footprint, then CLAMP so it stays inside the
    // canvas's own bounds — never past the right or bottom visible edge —
    // and RAISE it by moving it to the end of the sibling list: SVG has
    // no z-index, paint order is DOM order, so "last child" is "on top".
    const clampedX = Math.max(0, Math.min(pos.x, CANVAS_W - NODE_OPEN_W));
    const clampedY = Math.max(0, Math.min(pos.y, CANVAS_H - NODE_OPEN_H));
    fo.setAttribute("width", NODE_OPEN_W);
    fo.setAttribute("height", NODE_OPEN_H);
    fo.setAttribute("x", clampedX);
    fo.setAttribute("y", clampedY);
    fo.setAttribute("data-open", "true");
    div.classList.add("node-card--open");
    toggle.setAttribute("aria-expanded", "true");
    toggle.textContent = "close";
    nodesLayer.appendChild(fo);
  }
}

function buildExemplarNodes() {
  nodesLayer = document.getElementById("nodes-layer");
  Object.entries(nodePositions).forEach(([id, pos]) => {
    const built = makeNodeCard(id, pos);
    nodesLayer.appendChild(built.fo);
    nodeEls[id] = built;
  });
}

// ---- palette collapse ----------------------------------------------------
function wirePaletteToggle() {
  const palette = document.getElementById("palette");
  const btn = document.getElementById("palette-toggle");
  const glyph = document.getElementById("palette-toggle-glyph");
  const sr = document.getElementById("palette-toggle-sr");
  btn.addEventListener("click", () => {
    const collapsed = palette.dataset.state === "collapsed";
    palette.dataset.state = collapsed ? "expanded" : "collapsed";
    btn.setAttribute("aria-expanded", String(collapsed));
    glyph.textContent = collapsed ? "‹" : "›";
    sr.textContent = collapsed ? "Collapse the node palette" : "Expand the node palette";
  });
}

// ---- mission panel: collapse + pager -------------------------------------
const MISSIONS = [
  { id: "m1", title: "M-1 · First Light", brief: "Find the peak in the invariant mass of the two leading leptons." },
  { id: "m2", title: "M-2 · Cleaning the Signal", brief: "Cut the backgrounds without cutting too much signal." },
  { id: "m3", title: "M-3 · The Unknown", brief: "A signal sample is hiding in the data. Find cuts that expose it and run a fit." },
];
let missionIndex = 2;

function renderMission() {
  const m = MISSIONS[missionIndex];
  const label = document.getElementById("mission-label");
  label.textContent = m.title;
  label.dataset.missionId = m.id;
  document.getElementById("mission-brief").textContent = m.brief;
}

function wirePager() {
  document.getElementById("pager-back").addEventListener("click", () => {
    missionIndex = Math.max(0, missionIndex - 1);
    renderMission();
  });
  document.getElementById("pager-forward").addEventListener("click", () => {
    missionIndex = Math.min(MISSIONS.length - 1, missionIndex + 1);
    renderMission();
  });
}

function wirePanelToggle() {
  const panel = document.getElementById("mission-panel");
  const btn = document.getElementById("panel-toggle");
  const glyph = document.getElementById("panel-toggle-glyph");
  const sr = document.getElementById("panel-toggle-sr");
  btn.addEventListener("click", () => {
    const collapsed = panel.dataset.state === "collapsed";
    panel.dataset.state = collapsed ? "expanded" : "collapsed";
    btn.setAttribute("aria-expanded", String(collapsed));
    glyph.textContent = collapsed ? "›" : "‹";
    sr.textContent = collapsed ? "Collapse the mission panel" : "Expand the mission panel";
  });
}

function init() {
  buildExemplarNodes();
  wirePaletteToggle();
  wirePanelToggle();
  wirePager();
  renderMission();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
