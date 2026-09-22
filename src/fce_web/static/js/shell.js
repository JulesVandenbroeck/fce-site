// Wires the three-region app shell (templates/shell.html), ported from
// docs/design-explorations/shell.html per F-004. See that file's own header
// comment for the design history (D-010, D-014).
//
// UI toggles only -- palette/panel collapsed-or-expanded, the pager index.
// Carried only in each region's own `data-state` attribute (plus `hidden`
// on the controlled body, per F7) and never read by a run payload. The
// graph itself (nodes/edges, buildRunPayload) is F-005's; #nodes-layer
// stays empty until then.

// ---- region collapse: palette (left) and mission panel (right) -----------
// Same shape both sides, only ids/glyphs/copy differ -- one wireToggle
// call per region.
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
  btn.addEventListener("click", () => {
    const collapsed = region.dataset.state === "collapsed";
    region.dataset.state = collapsed ? "expanded" : "collapsed";
    body.hidden = !collapsed;
    btn.setAttribute("aria-expanded", String(collapsed));
    glyph.textContent = collapsed ? expandGlyph : collapseGlyph;
    sr.textContent = collapsed ? `Collapse the ${noun}` : `Expand the ${noun}`;
  });
}

function init() {
  wireToggle("palette", "palette-toggle", "palette-toggle-glyph", "palette-toggle-sr", "palette-list", "‹›", "node palette");
  wireToggle("mission-panel", "panel-toggle", "panel-toggle-glyph", "panel-toggle-sr", "mission-panel-body", "›‹", "mission panel");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
