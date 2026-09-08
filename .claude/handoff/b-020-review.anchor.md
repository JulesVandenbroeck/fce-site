# B-020 review, cycle 2 — anchor (written at 75%; review COMPLETE, nothing to resume)

Worktree: ~/fce-gate-b020 @ 1ab1bf3. PLAYWRIGHT_BROWSERS_PATH exported.

Ran and passed: pytest tests/ -q -> 621 passed; flake8 src/ tests/ scripts/ -> clean;
test_graph.py -> 16 passed; C2 both ways (1 passed / 1 skipped); test_api_contract.py -> 286 passed.

Independently derived the two pinned digests from runconfig's formula (not from graph.py):
one-expr fixture -> h5_sel 1d1f518b0dd7f037a7c12a160838e42d, h5 2b8e282692cbdaaff65efec8c786b5ad.
Both match the literals in tests/test_graph.py:196-197. F1's fix is genuine.

Mutations: _MULT_CUT_FIELDS swap -> red at test_graph.py:209. _check_no_cycle no-op -> red.
_MULT_CUT_TYPES widened -> red (C12). _histogram_dict type checks removed -> red (C12).
_selection_exprs reversed -> GREEN (fixture has one expr; multi-selection path uncovered).

Prior findings: F1-F6, F8 fixed and verified; F7 correctly backlogged (out of scope).
New: N1 stale/false C7 evidence in PR body (claims fbb913../c9873a70.. and two sel_exprs;
fixture yields 2b8e28../1d1f51.. with one). N2 multi-path grouping branch untested (or YAGNI).
N3 the shared-Multiplicity 400 is undocumented in docs/api.md.

Verdict issued: pr=33 cycle=2 findings=3 scope=pass verdict=rework.
