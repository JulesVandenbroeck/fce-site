/* beamline.js — D-004 exploration: style A, "Beamline".
 *
 * Not part of the shipping app. Demonstrates one persistence/interaction
 * model so the user can compare it against Bench (D-005) and Board (D-006):
 * an auto-laid rail that persists an ORDERED EDGE LIST ONLY (no coordinate
 * of any kind, anywhere) and connects nodes by CLICKING two ports in turn,
 * never by dragging one onto another.
 *
 * Why a plain 'click' listener is sufficient to make dragging a no-op,
 * verified empirically before relying on it (see the PR body for the
 * transcript): a browser only dispatches 'click' when the pointer goes down
 * and up over the *same* element. A real drag — mouse down on a port, move
 * across the page, mouse up on a different port — puts mousedown and
 * mouseup on two different elements, so neither port's 'click' handler ever
 * runs and no connection is made. No extra code is needed to "detect and
 * block" a drag; refusing it is what a click-only listener already does.
 *
 * The 8 addable node kinds and the legal source -> destination pairs below
 * are read from the vendored reference's own allowlist
 * (`ui/graph.py:_VALID_CONNECTIONS`, `ui/state.py:NODE_LABELS`), with bare
 * "Observable" excluded because `fce.py` never calls
 * `create_node("Observable")` — see tokens.css's node-identity comment and
 * the PR body for how that was checked by running the reference's own
 * dict, not by re-typing it from a read of the source.
 */

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

// ---------------------------------------------------------------------
// Graph state. The only thing that persists is `edges` — an ordered list
// of [fromId, toId] pairs — serialised into a single DOM attribute
// (`data-edges` on the graph container) after every change. Node kind is
// carried on each node element (`data-node-kind`) because a node has to
// declare what it *is* to be drawn and validated; that is identity, not
// position, and no x/y/column/slot value is written anywhere in this file.
const graphState = {
  nodes: new Map(), // id -> { kind }
  edges: [], // [fromId, toId][]
  nextId: 1,
  armed: null, // { id, kind } | null
};

let els = {};

function nodeLabel(id) {
  const n = graphState.nodes.get(id);
  return n ? `${KIND_BY_NAME[n.kind].label} (${id})` : id;
}

function persistEdges() {
  els.graph.setAttribute("data-edges", JSON.stringify(graphState.edges));
}

function setStatus(text) {
  els.status.textContent = text;
}

function buildNodeEl(id, kind, subtitle) {
  const meta = KIND_BY_NAME[kind];
  const node = document.createElement("li");
  node.className = `node node--${meta.cls}`;
  node.dataset.nodeId = id;
  node.dataset.nodeKind = kind;

  const title = document.createElement("p");
  title.className = "node__title";
  title.textContent = meta.label;
  node.appendChild(title);

  const sub = document.createElement("p");
  sub.className = "node__subtitle";
  sub.textContent = subtitle || "not configured yet";
  node.appendChild(sub);

  const ports = document.createElement("div");
  ports.className = "node__ports";

  if (meta.hasIn) {
    const inPort = document.createElement("button");
    inPort.type = "button";
    inPort.className = "port port--in";
    inPort.dataset.role = "in";
    inPort.setAttribute("aria-label", `Connect in to ${meta.label} (${id})`);
    inPort.addEventListener("click", () => handleInClick(id));
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
    outPort.addEventListener("click", () => handleOutClick(id));
    ports.appendChild(outPort);
  } else {
    const spacer = document.createElement("span");
    spacer.className = "port port--absent";
    spacer.setAttribute("aria-hidden", "true");
    ports.appendChild(spacer);
  }

  node.appendChild(ports);

  const links = document.createElement("ul");
  links.className = "node__links";
  node.appendChild(links);

  return node;
}

function renderLinksFor(id) {
  const node = els.graph.querySelector(`.node[data-node-id="${id}"]`);
  if (!node) return;
  const links = node.querySelector(".node__links");
  links.textContent = "";
  const outgoing = graphState.edges.filter(([from]) => from === id);
  outgoing.forEach(([, to]) => {
    const li = document.createElement("li");
    li.textContent = `→ ${nodeLabel(to)}`;
    links.appendChild(li);
  });
}

function addNode(kind, subtitle) {
  const id = `n${graphState.nextId}`;
  graphState.nextId += 1;
  graphState.nodes.set(id, { kind });
  const el = buildNodeEl(id, kind, subtitle);
  els.rail.appendChild(el);
  renderLinksFor(id);
  return id;
}

function armPort(id, portEl) {
  clearArmed();
  graphState.armed = { id, kind: graphState.nodes.get(id).kind };
  portEl.classList.add("port--armed");
  setStatus(`Connecting from ${nodeLabel(id)} — click an input port to finish, or click this port again to cancel.`);
}

function clearArmed() {
  if (!graphState.armed) return;
  const prev = els.graph.querySelector(
    `.node[data-node-id="${graphState.armed.id}"] .port--out`
  );
  if (prev) prev.classList.remove("port--armed");
  graphState.armed = null;
}

function handleOutClick(id) {
  const outPort = els.graph.querySelector(`.node[data-node-id="${id}"] .port--out`);
  if (graphState.armed && graphState.armed.id === id) {
    clearArmed();
    setStatus("Connection cancelled. Click an output port to start a new connection.");
    return;
  }
  armPort(id, outPort);
}

function handleInClick(id) {
  if (!graphState.armed) {
    setStatus("Click an output port first, then an input port, to connect two nodes.");
    return;
  }
  if (graphState.armed.id === id) {
    setStatus("A node cannot connect to itself.");
    return;
  }
  const srcKind = graphState.armed.kind;
  const dstKind = graphState.nodes.get(id).kind;
  const srcId = graphState.armed.id;
  if (isLegal(srcKind, dstKind)) {
    graphState.edges.push([srcId, id]);
    persistEdges();
    renderLinksFor(srcId);
    const node = els.graph.querySelector(`.node[data-node-id="${id}"]`);
    node.classList.remove("node--flash");
    // eslint-disable-next-line no-unused-expressions
    node.offsetWidth; // restart the flash animation on repeat connections
    node.classList.add("node--flash");
    setStatus(`Connected: ${nodeLabel(srcId)} → ${nodeLabel(id)}.`);
    clearArmed();
  } else {
    setStatus(
      `Refused: ${KIND_BY_NAME[srcKind].label} cannot connect to ${KIND_BY_NAME[dstKind].label}.`
    );
    clearArmed();
  }
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
  persistEdges();
}

function init() {
  els = {
    graph: document.getElementById("graph"),
    rail: document.getElementById("graph-rail"),
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
