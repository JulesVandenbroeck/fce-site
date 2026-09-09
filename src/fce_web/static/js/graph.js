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
// dataset (`src/fce_web/graph.py`, C4/C5 there). A fifth, locked tile is
// appended here (not in the template) to keep this file's edit to shell.html
// scoped to the canvas container, per the F-005 dispatch's file scope.
//
// Exported model (the contract F-007 serialises): the canvas container
// (#canvas-wrap) carries one `data-graph` attribute, a JSON object
//   { nodes: { <id>: { kind, x, y }, ... }, edges: [ [from, to], ... ] }
// `nodes` is keyed by id and carries kind alongside position -- unlike
// bench.html, which kept kind off the persisted object. Edges are an
// ordered [from, to] pair list, same shape bench.html and graph.py both use.
//
// VALID_CONNECTIONS below is a courtesy check only, trimmed to the four
// palette kinds. `src/fce_web/graph.py`'s `VALID_CONNECTIONS` is the
// authority (B-020); a client that disagrees with the server is a bug in
// the client, not a second source of truth.

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
const CANVAS_W = 704;
const CANVAS_H = 512;
const NUDGE = 12;
const NUDGE_BIG = 40;

// The only state this module keeps.
const graphState = {
  nodes: new Map(), // id -> { kind, x, y }
  edges: [], // [fromId, toId][]
  nextId: 1,
  spawnIndex: 0,
  keyboardArmed: null, // { id, kind } while an out-port is armed via Enter/Space
};

let els = {};

function nodeLabel(id) {
  const n = graphState.nodes.get(id);
  return n ? `${KIND_BY_NAME[n.kind].label} (${id})` : id;
}

function persistUI() {
  const nodes = {};
  graphState.nodes.forEach((n, id) => {
    nodes[id] = { kind: n.kind, x: n.x, y: n.y };
  });
  els.wrap.setAttribute("data-graph", JSON.stringify({ nodes, edges: graphState.edges }));
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
  const x = 16 + col * 172 + (row % 2) * 28;
  const y = 16 + row * 132;
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

function renderLinksFor(id) {
  const node = els.wrap.querySelector(`.node[data-node-id="${id}"]`);
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
  sub.textContent = "not configured yet";
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

function addNode(kind) {
  const id = `n${graphState.nextId}`;
  graphState.nextId += 1;
  const { x, y } = nextSpawnPoint();
  graphState.nodes.set(id, { kind, x, y });
  const fo = buildNodeEl(id, kind);
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

  function onUp(upEv) {
    portEl.removeEventListener("pointermove", onMove);
    portEl.removeEventListener("pointerup", onUp);
    portEl.removeEventListener("pointercancel", onCancel);
    clearTargetHighlight();
    dragLine.remove();
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
    portEl.removeEventListener("pointermove", onMove);
    portEl.removeEventListener("pointerup", onUp);
    portEl.removeEventListener("pointercancel", onCancel);
    clearTargetHighlight();
    dragLine.remove();
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
    const node = els.wrap.querySelector(`.node[data-node-id="${toId}"]`);
    node.classList.remove("node--flash");
    void node.offsetWidth; // restart the flash animation on repeat connections
    node.classList.add("node--flash");
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

// The palette's fifth tile: a locked node kind for a later mission, shown
// but inert (brief §4, "complexity ramps"). Appended here rather than in
// shell.html so this task's template edit stays inside the canvas
// container, per the F-005 dispatch's file scope.
function addLockedPaletteEntry() {
  const li = document.createElement("li");
  li.className = "palette__locked";
  li.setAttribute("aria-disabled", "true");
  const lock = document.createElement("span");
  lock.className = "lock-tag";
  lock.textContent = "locked";
  li.appendChild(lock);
  li.appendChild(document.createTextNode(" Node kind — opens in a later mission"));
  els.paletteList.appendChild(li);
}

function init() {
  els = {
    wrap: document.getElementById("canvas-wrap"),
    svg: document.getElementById("canvas-svg"),
    nodesLayer: document.getElementById("nodes-layer"),
    edgesLayer: document.getElementById("edges-layer"),
    status: document.getElementById("canvas-status"),
    paletteButtons: Array.from(document.querySelectorAll(".palette__add")),
    paletteList: document.getElementById("palette-list"),
  };
  addLockedPaletteEntry();
  wirePalette();
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
