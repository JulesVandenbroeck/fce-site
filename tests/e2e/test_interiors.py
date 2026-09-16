"""One check for the expression module's contract (F-011,
docs/plan-m4-recipe-builder.md), and one check that a non-default graph
changes the run's result.

Frontend's own markup and browser behaviour, on frontend's side of the
2026-09-07 conftest seam (`.claude/shared/CLAUDE.md` §4): these tests use
the harness fixtures from `tests/e2e/conftest.py` without adding to it.
"""

from __future__ import annotations

import json
import re

from playwright.sync_api import expect

from fce_web import safe_eval
from tests.e2e.conftest import LoadedPage
from tests.e2e.test_run import _place_mission1_chain


def test_every_builder_output_compiles_under_safe_eval(index: LoadedPage) -> None:
    """C4: enumerate every expression `expr.js`'s builders can produce and
    compile each one with `fce_web.safe_eval` -- the server is the
    authority, this does not re-implement the allowlist in JS.

    Verified red (2026-09-16, review cycle 1 F2): changing `.p4` to `.p5` in
    `vectorSumConfig` (expr.js) turned this test red at `compile_expr`,
    `UnsafeExpression: Unknown attribute '.p5'` -- reaching the server's own
    check, not a JS-side failure -- then reverted. (Renaming `PROPERTIES`'
    "pt" entry fails earlier, inside the page's own `propertyLabel` lookup,
    before any expression is even built -- a real bug this test would also
    catch, but not the one this docstring claims.)
    """
    page = index.page
    exprs = page.evaluate(
        """async () => {
          const m = await import('/static/js/expr.js');
          const out = [];
          m.OBJECTS.forEach((o) => {
            m.OBJECT_PROPERTIES[o.name].forEach((prop) => {
              out.push(m.objectConfig(o.name, prop).expr);
              out.push(m.buildSelectionExpr(o.name, prop, '>', '5'));
            });
          });
          m.COUNTS.forEach((c) => out.push(m.globalConfig(c.name).expr));
          out.push(m.globalConfig('met_pt').expr);
          const vsObjects = m.VECTOR_SUM_OBJECTS.map((o) => o.name);
          m.VECTOR_SUM_QUANTITIES.forEach((q) => {
            out.push(m.vectorSumConfig(['l1', 'l2'], q.name).expr);
            out.push(m.vectorSumConfig(vsObjects, q.name).expr);
          });
          return out;
        }"""
    )
    # Sanity that the enumeration actually walked the vocabulary, not an
    # empty/undefined module -- a broken `import()` would otherwise pass
    # trivially with an empty list.
    assert len(exprs) > 20, exprs

    for expr in exprs:
        safe_eval.compile_expr(expr)  # raises UnsafeExpression on the first bad one


def test_changed_selection_changes_the_histogram(index: LoadedPage) -> None:
    """C5: the default mission-1 chain, then the same chain with its
    Selection row's cut tightened through the real interior (not a second
    hardcoded default), produce different histogram payloads.

    Verified red (2026-09-16, this task): with run.js's `defaultConfigFor`
    reverted to also mask Selection/Observable configs, this test failed
    because both submissions serialised to the same hardcoded recipe.
    """
    page = index.page
    _place_mission1_chain(page)

    page.locator("#run-button").click()
    expect(page.locator("#results-status")).to_have_text("Run complete.", timeout=60000)
    expect(page.locator("#results-chart")).to_have_attribute("data-result", re.compile(".+"), timeout=10000)
    default_result = json.loads(page.locator("#results-chart").get_attribute("data-result"))

    # n2 is the Selection node (CHAIN order in test_run.py). Open its
    # interior and tighten the default row's cut from "> 5" to "> 60" --
    # the one number a student would actually change.
    page.locator('.node[data-node-id="n2"] summary').click()
    page.locator("#sel-row-1-n2-value").fill("60")

    page.locator("#run-button").click()
    expect(page.locator("#results-status")).to_have_text("Run complete.", timeout=60000)
    expect(page.locator("#results-chart")).to_have_attribute("data-result", re.compile(".+"), timeout=10000)
    changed_result = json.loads(page.locator("#results-chart").get_attribute("data-result"))

    assert changed_result["samples"] != default_result["samples"] or changed_result["data"] != default_result["data"]
