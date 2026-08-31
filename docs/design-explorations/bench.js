/* bench.js — D-005 exploration: style B, "Bench".
 *
 * Not part of the shipping app. Demonstrates the second of the three
 * persistence/interaction models the user asked to compare (Beamline,
 * D-004; Board, D-006 next): a FREE CANVAS that persists an {x, y} pair per
 * node, and connects two nodes by DRAGGING from an output port to an input
 * port, never by clicking one.
 *
 * Persistence lives in one attribute, `data-ui`, on `#graph`:
 *   { "nodes": [ { "id": "n1", "x": 40, "y": 24 }, ... ],
 *     "edges": [ ["n1", "n2"], ... ] }
 * This is deliberately the shape design-brief.md §4 calls the "ui object" —
 * coordinates and the edge list, nothing the engine itself would need to
 * understand. Node *kind* is not in it; that lives on each node's own
 * element (`data-node-kind`), the same place Beamline puts it, because kind
 * is analysis content the run payload carries, not a layout fact.
 *
 * No inline `style=` attribute is used anywhere for positioning. Each node
 * is drawn as an SVG `<foreignObject>` whose `x`/`y`/`width`/`height` are
 * plain geometry attributes — not CSS, not `style=` — so a continuous,
 * freely-dragged position is expressible without ever writing to an
 * element's `style` property. `bench.css` styles the HTML content inside
 * each foreignObject (the node card, its ports) entirely by class.
 *
 * The 8 addable node kinds and the legal source -> destination pairs are
 * the same facts Beamline sources from the vendored reference's own
 * allowlist (`ui/graph.py:_VALID_CONNECTIONS`) — see beamline.js's own
 * comment for how that was checked. Bare "Observable" stays excluded for
 * the same reason.
 */

const SVG_NS = "http://www.w3.org/2000/svg";

const NODE_KINDS = [
  { kind: "DataSource", label: "Data", cls: "data", hasIn: false, hasOut: true },
  { kind: "Multiplicity", label: "Multiplicity", cls: "multiplicity", hasIn: true, hasOut: true },
  { kind: "Selection", label: "Selection", cls: "selection", hasIn: true, hasOut: true },
  { kind: "ObsGlobal", label: "Obs: Global", cls: "obs-global", hasIn: true, hasOut: true },
  { kind: "ObsObject", label: "Obs: Object", cls: "obs-object", hasIn: true, hasOut: true },
  { kind: "ObsVectorSum", label: "Obs: Vec Sum", cls: "obs-vecsum", hasIn: true, hasOut: true },
  { kind: "ObsCustom", label: "Obs: Custom", cls: "obs-custom", hasIn: true, hasOut: true },
  { kind: "Histogram", label: "Histogram", cls: "histogram", hasIn: true, hasOut: false },
];

const KIND_BY_NAME = Object.fromEntries(NODE_KINDS.map((k) => [k.kind, k]));

const VALID_CONNECTIONS = {
  DataSource: ["Multiplicity", "Selection"],
  Multiplicity: ["Multiplicity", "Selection"],
  Selection: ["Selection", "ObsGlobal", "ObsObject", "ObsVectorSum", "ObsCustom"],
  ObsGlobal: ["Histogram"],
  ObsObject: ["Histogram"],
  ObsVectorSum: ["Histogram"],
  ObsCustom: ["Histogram"],
  Histogram: [],
};

function isLegal(srcKind, dstKind) {
  return (VALID_CONNECTIONS[srcKind] || []).includes(dstKind);
}

const NODE_W = 176;
const NODE_H = 96;
const CANVAS_W = 980;
const CANVAS_H = 460;
const NUDGE = 12;
const NUDGE_BIG = 40;

// The only state this file keeps. `nodes` carries kind AND position because
// position is what this style exists to hold — contrast with Beamline,
// whose equivalent map carries kind alone. `edges` is the same ordered
// [from, to] list shape Beamline persists.
const graphState = {
  nodes: new Map(), // id -> { kind, x, y }
  edges: [], // [fromId, toId][]
  nextId: 1,
  spawnIndex: 0,
  connectDrag: null, // { fromId, fromKind } while a pointer drags from an out-port
  keyboardArmed: null, // { id, kind } while an out-port is armed via Enter/Space
};

let els = {};

function nodeLabel(id) {
  const n = graphState.nodes.get(id);
  return n ? `${KIND_BY_NAME[n.kind].label} (${id})` : id;
}

function persistUI() {
  const nodes = Array.from(graphState.nodes, ([id, n]) => ({ id, x: n.x, y: n.y }));
  els.graph.setAttribute("data-ui", JSON.stringify({ nodes, edges: graphState.edges }));
}

function setStatus(text) {
  els.status.textContent = text;
}

function clampToCanvas(x, y) {
  return {
    x: Math.max(0, Math.min(CANVAS_W - NODE_W, x)),
    y: Math.max(0, Math.min(CANVAS_H - NODE_H, y)),
  };
}

function nextSpawnPoint() {
  const perRow = 4;
  const i = graphState.spawnIndex++;
  const col = i % perRow;
  const row = Math.floor(i / perRow);
  const x = 16 + col * 232 + (row % 2) * 36;
  const y = 16 + row * 168;
  return clampToCanvas(x, y);
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

function portCenterSvg(id, role) {
  const sel = `.node[data-node-id="${id}"] .port--${role}`;
  const portEl = els.graph.querySelector(sel);
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
    path.setAttribute(
      "d",
      `M ${p1.x} ${p1.y} C ${midX} ${p1.y}, ${midX} ${p2.y}, ${p2.x} ${p2.y}`
    );
    path.setAttribute("marker-end", "url(#bench-arrow)");
    els.edgesLayer.appendChild(path);
  });
}

function renderLinksFor(id) {
  const node = els.graph.querySelector(`.node[data-node-id="${id}"]`);
  if (!node) return;
  const links = node.querySelector(".node__links");
  links.textContent = "";
  graphState.edges
    .filter(([from]) => from === id)
    .forEach(([, to]) => {
      const li = document.createElement("li");
      li.textContent = `→ ${nodeLabel(to)}`;
      links.appendChild(li);
    });
}

function moveNodeTo(id, x, y) {
  const n = graphState.nodes.get(id);
  if (!n) return;
  const clamped = clampToCanvas(x, y);
  n.x = clamped.x;
  n.y = clamped.y;
  const fo = foreignObjectFor(id);
  if (fo) {
    fo.setAttribute("x", clamped.x);
    fo.setAttribute("y", clamped.y);
  }
  renderEdges();
}

function buildNodeEl(id, kind, x, y, subtitle) {
  const meta = KIND_BY_NAME[kind];

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
  handle.setAttribute(
    "aria-label",
    `Move ${meta.label} (${id}). Drag, or use arrow keys.`
  );
  const title = document.createElement("span");
  title.className = "node__title";
  title.textContent = meta.label;
  handle.appendChild(title);
  div.appendChild(handle);

  const sub = document.createElement("p");
  sub.className = "node__subtitle";
  sub.textContent = subtitle || "not configured yet";
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
  } else {
    const spacer = document.createElement("span");
    spacer.className = "port port--absent";
    spacer.setAttribute("aria-hidden", "true");
    ports.appendChild(spacer);
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
  } else {
    const spacer = document.createElement("span");
    spacer.className = "port port--absent";
    spacer.setAttribute("aria-hidden", "true");
    ports.appendChild(spacer);
  }

  div.appendChild(ports);

  const links = document.createElement("ul");
  links.className = "node__links";
  div.appendChild(links);

  fo.appendChild(div);

  handle.addEventListener("pointerdown", (ev) => startNodeDrag(id, handle, ev));
  handle.addEventListener("keydown", (ev) => handleHandleKey(id, ev));

  return fo;
}

function addNode(kind, subtitle) {
  const id = `n${graphState.nextId}`;
  graphState.nextId += 1;
  const { x, y } = nextSpawnPoint();
  graphState.nodes.set(id, { kind, x, y });
  const fo = buildNodeEl(id, kind, x, y, subtitle);
  els.nodesLayer.appendChild(fo);
  renderLinksFor(id);
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
  graphState.connectDrag = { fromId: id, fromKind: kind };
  portEl.setPointerCapture(ev.pointerId);

  const start = portCenterSvg(id, "out");
  const dragLine = document.createElementNS(SVG_NS, "line");
  dragLine.setAttribute("class", "edge edge--drag");
  dragLine.setAttribute("x1", start.x);
  dragLine.setAttribute("y1", start.y);
  dragLine.setAttribute("x2", start.x);
  dragLine.setAttribute("y2", start.y);
  els.edgesLayer.appendChild(dragLine);
  setStatus(`Dragging from ${nodeLabel(id)} — drop on an input port to connect.`);

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

  function onUp(upEv) {
    portEl.removeEventListener("pointermove", onMove);
    portEl.removeEventListener("pointerup", onUp);
    portEl.removeEventListener("pointercancel", onCancel);
    clearTargetHighlight();
    dragLine.remove();
    graphState.connectDrag = null;
    const under = document.elementFromPoint(upEv.clientX, upEv.clientY);
    const targetPort = under ? under.closest(".port--in") : null;
    if (!targetPort) {
      setStatus("Connection cancelled — you did not drop on an input port.");
      return;
    }
    const targetNodeEl = targetPort.closest(".node");
    const toId = targetNodeEl ? targetNodeEl.dataset.nodeId : null;
    attemptConnect(id, kind, toId);
  }
  function onCancel() {
    portEl.removeEventListener("pointermove", onMove);
    portEl.removeEventListener("pointerup", onUp);
    portEl.removeEventListener("pointercancel", onCancel);
    clearTargetHighlight();
    dragLine.remove();
    graphState.connectDrag = null;
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
  const toKind = graphState.nodes.get(toId).kind;
  if (isLegal(fromKind, toKind)) {
    graphState.edges.push([fromId, toId]);
    persistUI();
    renderLinksFor(fromId);
    renderEdges();
    const node = els.graph.querySelector(`.node[data-node-id="${toId}"]`);
    node.classList.remove("node--flash");
    // eslint-disable-next-line no-unused-expressions
    node.offsetWidth; // restart the flash animation on repeat connections
    node.classList.add("node--flash");
    setStatus(`Connected: ${nodeLabel(fromId)} → ${nodeLabel(toId)}.`);
  } else {
    setStatus(
      `Refused: ${KIND_BY_NAME[fromKind].label} cannot connect to ${KIND_BY_NAME[toKind].label}.`
    );
  }
}

// ---- keyboard path: arm an out-port with Enter/Space, complete on an
// in-port the same way. Deliberately routed through `keydown`, never
// `click` — a native <button> also fires a synthetic `click` on Enter/Space,
// and this file has no `click` listener on any port, so a real mouse click
// (Playwright's `.click()` included) triggers nothing. That is what makes
// click-to-connect refused by construction, the same reasoning Beamline's
// own comment gives for why a plain 'click' listener is enough to make
// dragging inert there — the mirror image of this style's own refusal.
function handleOutKey(id, ev) {
  if (ev.key !== "Enter" && ev.key !== " ") return;
  ev.preventDefault();
  const outPort = els.graph.querySelector(`.node[data-node-id="${id}"] .port--out`);
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
    `Armed from ${nodeLabel(id)} — Tab to an input port and press Enter to finish, or press Enter here again to cancel.`
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
  const prev = els.graph.querySelector(
    `.node[data-node-id="${graphState.keyboardArmed.id}"] .port--out`
  );
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
      addNode(kind, null);
      setStatus(`Added a new ${KIND_BY_NAME[kind].label} node.`);
    });
  });
}

function wireRun() {
  if (!els.runButton) return;
  els.runButton.addEventListener("click", () => {
    els.runPanel.classList.remove("run--pulse");
    // eslint-disable-next-line no-unused-expressions
    els.runPanel.offsetWidth;
    els.runPanel.classList.add("run--pulse");
    setStatus("Run started — reading events.");
  });
}

function buildDemoGraph() {
  const a = addNode("DataSource", "91 GeV · IDEA · all samples");
  const b = addNode("Multiplicity", "≥ 2 leptons");
  const c = addNode("Selection", "lepton pt > 20 GeV");
  const d = addNode("ObsVectorSum", "mass of lepton 1 + lepton 2");
  const e = addNode("Histogram", "40 bins, 0–120 GeV");
  [
    [a, b],
    [b, c],
    [c, d],
    [d, e],
  ].forEach(([from, to]) => {
    graphState.edges.push([from, to]);
    renderLinksFor(from);
  });
  persistUI();
  renderEdges();
}

function init() {
  els = {
    graph: document.getElementById("graph"),
    svg: document.getElementById("canvas-svg"),
    nodesLayer: document.getElementById("nodes-layer"),
    edgesLayer: document.getElementById("edges-layer"),
    status: document.getElementById("graph-status"),
    paletteButtons: Array.from(document.querySelectorAll(".palette__add")),
    runButton: document.getElementById("run-button"),
    runPanel: document.getElementById("run-panel"),
  };
  buildDemoGraph();
  wirePalette();
  wireRun();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
