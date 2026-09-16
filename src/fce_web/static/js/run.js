// Submits the canvas graph (graph.js's #canvas-wrap[data-graph]) to
// POST /api/run, then drives GET /api/run/{id}/events (native EventSource --
// no hand-rolled streaming layer) to render phase and progress live into
// #results, per task F-007. See docs/api.md for both wire formats.
//
// Markup contract for D-016 (styling) and F-008 (the chart), written out in
// full in the F-007 PR body:
//   #run-button          -- the Run control
//   #results-status       -- aria-live status line (phase + progress text)
//   #results-progress     -- native <progress>, visual only
//   #results-note         -- aria-live margin note: cache-hit or error text,
//                             never styled as a banner (design-brief.md §2)
//   #results-chart        -- F-008 renders the finished histogram here. On a
//                             finished run this module sets a `data-result`
//                             attribute (the raw JSON result payload, same
//                             shape as GET /api/run/{id}/result) and
//                             dispatches a `fce:result` CustomEvent on it,
//                             `detail` set to the parsed payload.

// The mission-1 recipe (docs/design-brief.md, tests/test_api_run.py:24-38),
// verbatim. Editable node fields are M4 (2026-09-11 ruling) -- until then
// the client fills whatever config a node is missing with this recipe, so a
// student can place, connect and run a mission-1 graph without configuring
// anything by hand.
function defaultConfigFor(kind, id) {
  switch (kind) {
    case "Multiplicity":
      return { nlep: 2, op_lep: ">=", njets: 0, op_jet: ">=", ltype: "Any", nphot: 0, op_phot: ">=" };
    case "Selection":
      return { name: id, exprs: ["l1.pt > 20"] };
    case "Observable":
      return { mode: "ObsCustom", expr: "(l1.p4 + l2.p4).mass", label: "m(l1,l2)" };
    case "Histogram":
      return { bins: "50", min: "60", max: "120" };
    default:
      return {};
  }
}

// docs/api.md:34-50 -- {missionId, graph: {nodes: [{id, kind, config}], edges}}
// only. `x`/`y` are canvas layout, not part of this shape (graph.py never
// reads them either), so they are dropped here rather than carried along.
function buildSubmission() {
  const wrap = document.getElementById("canvas-wrap");
  const graph = JSON.parse(wrap.getAttribute("data-graph"));
  const nodes = graph.nodes.map((n) => ({
    id: n.id,
    kind: n.kind,
    config: { ...defaultConfigFor(n.kind, n.id), ...(n.config || {}) },
  }));
  const missionId = document.getElementById("mission-label").dataset.missionId;
  return { missionId, graph: { nodes, edges: graph.edges } };
}

let els = {};

function resetResults() {
  els.status.textContent = "Submitting…";
  els.progress.hidden = true;
  els.progress.value = 0;
  els.note.hidden = true;
  els.note.textContent = "";
}

function setNote(text) {
  els.note.textContent = text;
  els.note.hidden = !text;
}

function setPhaseProgress(phase, value) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  els.progress.hidden = false;
  els.progress.value = pct;
  els.status.textContent = phase ? `${phase} — ${pct}%` : `${pct}%`;
}

function finishRun(runId, status) {
  els.runButton.disabled = false;
  if (status === "error" || status === "cancelled") {
    fetchResult(runId, true);
    return;
  }
  els.status.textContent = "Run complete.";
  fetchResult(runId, false);
}

function fetchResult(runId, expectError) {
  fetch(`/api/run/${runId}/result`)
    .then((resp) => resp.json())
    .then((body) => {
      if (body.status === "done") {
        els.chart.setAttribute("data-result", JSON.stringify(body));
        els.chart.dispatchEvent(new CustomEvent("fce:result", { detail: body, bubbles: true }));
      } else if (expectError || body.status === "error" || body.status === "cancelled") {
        setNote(body.error || "The run did not finish.");
      }
    })
    .catch(() => setNote("Could not load the result. Check your connection and try again."));
}

function streamRun(runId) {
  const lastPhase = { value: "" };
  let source;
  try {
    source = new EventSource(`/api/run/${runId}/events`);
  } catch {
    setNote("Could not reach the server. Check your connection and try again.");
    els.runButton.disabled = false;
    return;
  }
  source.onmessage = (ev) => {
    let frame;
    try {
      frame = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (frame.type === "progress") {
      setPhaseProgress(lastPhase.value, frame.value);
    } else if (frame.type === "phase") {
      lastPhase.value = frame.phase;
      els.status.textContent = frame.phase;
    } else if (frame.type === "done") {
      source.close();
      finishRun(runId, frame.status);
    }
  };
  source.onerror = () => {
    source.close();
    setNote("Lost connection to the run. Try again.");
    els.runButton.disabled = false;
  };
}

function runAnalysis() {
  let payload;
  try {
    payload = buildSubmission();
  } catch {
    setNote("The graph could not be read. Try rebuilding it.");
    return;
  }

  els.runButton.disabled = true;
  resetResults();

  fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((resp) => resp.json().then((body) => ({ ok: resp.ok, body })))
    .then(({ ok, body }) => {
      if (!ok) {
        els.runButton.disabled = false;
        els.status.textContent = "Not run yet.";
        setNote(body.error || "The run could not be submitted.");
        return;
      }
      if (body.cacheHit) {
        setNote("Recognised these cuts — reusing your earlier run.");
      }
      streamRun(body.runId);
    })
    .catch(() => {
      els.runButton.disabled = false;
      els.status.textContent = "Not run yet.";
      setNote("Could not reach the server. Check your connection and try again.");
    });
}

function init() {
  els = {
    runButton: document.getElementById("run-button"),
    status: document.getElementById("results-status"),
    progress: document.getElementById("results-progress"),
    note: document.getElementById("results-note"),
    chart: document.getElementById("results-chart"),
  };
  els.runButton.addEventListener("click", runAnalysis);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
