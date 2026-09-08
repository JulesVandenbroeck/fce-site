// Wires the three-region app shell (templates/shell.html), ported from
// docs/design-explorations/shell.html per F-004. See that file's own header
// comment for the design history (D-010, D-014).
//
// UI toggles only -- palette/panel collapsed-or-expanded, the pager index.
// Carried only in each region's own `data-state` attribute (plus `hidden`
// on the controlled body, per F7) and never read by a run payload. The
// graph itself (nodes/edges, buildRunPayload) is F-005's; #nodes-layer
// stays empty until then.

// ---- palette collapse ----------------------------------------------------
function wirePaletteToggle() {
  const palette = document.getElementById("palette");
  const btn = document.getElementById("palette-toggle");
  const glyph = document.getElementById("palette-toggle-glyph");
  const sr = document.getElementById("palette-toggle-sr");
  const list = document.getElementById("palette-list");
  btn.addEventListener("click", () => {
    const collapsed = palette.dataset.state === "collapsed";
    palette.dataset.state = collapsed ? "expanded" : "collapsed";
    list.hidden = !collapsed;
    btn.setAttribute("aria-expanded", String(collapsed));
    glyph.textContent = collapsed ? "‹" : "›";
    sr.textContent = collapsed ? "Collapse the node palette" : "Expand the node palette";
  });
}

// ---- mission panel: collapse ----------------------------------------------
// The pager buttons (#pager-back/#pager-forward) are real, keyboard-reachable
// <button>s in shell.html but stay unwired here: paging needs real mission
// data from content/missions/*.yaml, which is F-005/backend's to supply. No
// client-side mission array to duplicate the server-rendered title/brief.

function wirePanelToggle() {
  const panel = document.getElementById("mission-panel");
  const btn = document.getElementById("panel-toggle");
  const glyph = document.getElementById("panel-toggle-glyph");
  const sr = document.getElementById("panel-toggle-sr");
  const body = document.getElementById("mission-panel-body");
  btn.addEventListener("click", () => {
    const collapsed = panel.dataset.state === "collapsed";
    panel.dataset.state = collapsed ? "expanded" : "collapsed";
    body.hidden = !collapsed;
    btn.setAttribute("aria-expanded", String(collapsed));
    glyph.textContent = collapsed ? "›" : "‹";
    sr.textContent = collapsed ? "Collapse the mission panel" : "Expand the mission panel";
  });
}

function init() {
  wirePaletteToggle();
  wirePanelToggle();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
