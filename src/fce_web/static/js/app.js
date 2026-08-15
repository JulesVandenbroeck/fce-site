// Front-end entry point for FCE-site.
//
// Loaded by every page as `<script type="module" src="/static/js/app.js" defer>`.
// Deliberately empty for now: the page shell needs no browser behaviour, and this
// file exists so that the tag in base.html resolves instead of 404-ing.
//
// Later work wires the real modules in from here — the SVG chart renderer, the run
// progress (SSE) stream, and the recipe-card builder — each as its own small module.
// Keep this file free of side effects at import time.
