// Wires the four-region app shell (templates/shell.html), ported from
// docs/design-explorations/shell.html per F-004, then restructured F-015
// per docs/design-explorations/canvas-frame.html (backlog N12/N14: a
// full-bleed canvas with the palette, mission panel and results drawer as
// overlays). See those files' own header comments for the design history
// (D-010, D-014, D-020/D-021).
//
// UI toggles only -- palette/panel/drawer collapsed-or-expanded, the pager
// index. Carried only in each region's own `data-state` attribute (plus
// `hidden` on the controlled body, per F7) and never read by a run payload.
// The graph itself (nodes/edges, buildRunPayload) is F-005's; #nodes-layer
// stays empty until then.

// ---- region collapse: palette (left), mission panel (right), drawer
// (bottom) --------------------------------------------------------------
// Same shape all three, only ids/glyphs/copy differ -- one wireToggle call
// per region. Returns the setter so a caller outside the toggle button
// itself (Run Analysis, below) can drive the same state machine instead of
// building a second one -- lifted unchanged from canvas-frame.html's own
// wireToggle.
//
// The mission panel's pager buttons (#pager-back/#pager-forward) are real,
// keyboard-reachable <button>s in shell.html but stay unwired here: paging
// needs real mission data from content/missions/*.yaml, which is
// F-005/backend's to supply. No client-side mission array to duplicate the
// server-rendered title/brief.
// `glyphs` is the two-character "expanded-glyph, collapsed-glyph" pair as one
// string (e.g. "‹›") -- one token per call site instead of two positional
// glyph args, so a transposition between the two calls can't silently flip
// which chevron means which state.
function wireToggle(regionId, btnId, glyphId, srId, bodyId, glyphs, noun) {
  const region = document.getElementById(regionId);
  const btn = document.getElementById(btnId);
  const glyph = document.getElementById(glyphId);
  const sr = document.getElementById(srId);
  const body = document.getElementById(bodyId);
  const [expandGlyph, collapseGlyph] = glyphs;
  const set = (expanded) => {
    region.dataset.state = expanded ? "expanded" : "collapsed";
    body.hidden = !expanded;
    btn.setAttribute("aria-expanded", String(expanded));
    glyph.textContent = expanded ? expandGlyph : collapseGlyph;
    sr.textContent = expanded ? `Collapse the ${noun}` : `Expand the ${noun}`;
  };
  btn.addEventListener("click", () => set(region.dataset.state === "collapsed"));
  return set;
}

function init() {
  wireToggle("palette", "palette-toggle", "palette-toggle-glyph", "palette-toggle-sr", "palette-list", "‹›", "node palette");
  wireToggle("mission-panel", "panel-toggle", "panel-toggle-glyph", "panel-toggle-sr", "mission-panel-body", "›‹", "mission panel");
  const setDrawer = wireToggle(
    "drawer", "drawer-toggle", "drawer-toggle-glyph", "drawer-toggle-sr", "drawer-body", "⌄⌃", "results drawer"
  );

  // N14: pressing Run Analysis auto-expands the drawer if it is collapsed,
  // through the same setter the chevron uses, so the two can never
  // disagree about state. run.js owns what happens to the run itself; this
  // listener only ever touches drawer UI state.
  document.getElementById("run-button").addEventListener("click", () => {
    if (document.getElementById("drawer").dataset.state === "collapsed") setDrawer(true);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
