"""Task B-015: ``analytical_loop.py:290`` used to call ``compile(preprocess_hep_expr(e), ...)``
on student selection expressions with no length or node-count bound, so the caps enforced by
``fce_web.safe_eval.compile_expr`` (``MAX_EXPR_LENGTH``, ``MAX_AST_NODES``) did not protect it.

Investigation established that the list built there, ``compiled_sel_exprs``, reached exactly
one place -- ``branch_cfg["compiled_sel_exprs"] = compiled_sel_exprs`` at
``analytical_loop.py:132`` -- and had zero readers: ``fce_web.engine.path_filter.
filter_raw_event_data`` (the only function ``branch_cfg`` is passed into) explicitly no longer
reads ``cfg["compiled_sel_exprs"]`` (see that function's docstring, ``path_filter.py:596-600``)
and always recompiles ``cfg["sel_exprs"]`` itself through ``safe_eval.compile_expr``, which does
enforce the caps. So the primary outcome applies: the dead compile loop and the dead write are
removed rather than bounded.

This mirrors ``tests/test_path_filter.py``'s B-008 AST checker and its perturbation twin
(``test_no_eval_or_compile_call_sites`` / ``..._catches_a_reintroduced_call``), reused in shape
here for ``analytical_loop.py``.
"""
import ast
import inspect

import pytest

import fce_web.engine.analytical_loop as analytical_loop
from fce_web.runs import RunContext
from fce_web.safe_eval import MAX_AST_NODES, MAX_EXPR_LENGTH, UnsafeExpression


def _eval_or_compile_call_sites(source: str):
    """Return sorted line numbers of ``ast.Call`` nodes whose ``func`` resolves to the
    builtins named ``eval`` or ``compile`` (an ``ast.Name``, not e.g. an attribute access).
    """
    tree = ast.parse(source)
    sites = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in ("eval", "compile")):
            sites.append(node.lineno)
    return sorted(sites)


# ---------------------------------------------------------------------------
# C1: zero eval()/compile() call sites in analytical_loop.py, checked via ast.
# ---------------------------------------------------------------------------

def test_no_eval_or_compile_call_sites_in_analytical_loop():
    source = inspect.getsource(analytical_loop)
    sites = _eval_or_compile_call_sites(source)
    assert sites == [], (
        f"found eval()/compile() call site(s) at line(s) {sites} in analytical_loop.py; "
        "the dead compile-selection-expressions loop (formerly line 290) must be removed, "
        "not merely bounded"
    )


def _compiled_sel_exprs_reference_sites(source: str):
    """Return sorted line numbers of *real* uses of the ``compiled_sel_exprs`` key/name:
    a ``Name`` node with that id (a plain assignment or read), or a ``Subscript`` node
    whose slice is the string constant ``"compiled_sel_exprs"`` (a dict key access, e.g.
    ``branch_cfg["compiled_sel_exprs"] = ...``).

    Deliberately AST-based rather than a substring search over the source text (closes
    B-015 cycle-1 review m1): a comment merely *mentioning* the string must not trip this,
    because a comment is not a node the parser ever produces.
    """
    tree = ast.parse(source)
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "compiled_sel_exprs":
            sites.append(node.lineno)
        elif isinstance(node, ast.Subscript):
            slice_node = node.slice
            if isinstance(slice_node, ast.Constant) and slice_node.value == "compiled_sel_exprs":
                sites.append(node.lineno)
    return sorted(sites)


# ---------------------------------------------------------------------------
# C1 continued / C9: the dead write this compile loop fed is also gone, checked
# via an ast walk (not a raw substring search) so a comment naming the removed
# key does not trip this test.
# ---------------------------------------------------------------------------

def test_compiled_sel_exprs_key_is_gone():
    source = inspect.getsource(analytical_loop)
    sites = _compiled_sel_exprs_reference_sites(source)
    assert sites == [], (
        f"found real reference(s) to compiled_sel_exprs at line(s) {sites}; "
        "compiled_sel_exprs had zero readers (path_filter.filter_raw_event_data always "
        "recompiles cfg['sel_exprs'] itself -- path_filter.py:596-600) and should have been "
        "removed entirely, not just bounded"
    )


def test_compiled_sel_exprs_key_is_gone_ignores_a_comment():
    """C9 perturbation twin, half 1: a comment mentioning the removed key must not fail
    the checker -- it is not a real reference."""
    source = inspect.getsource(analytical_loop) + "\n# compiled_sel_exprs was removed here\n"
    assert _compiled_sel_exprs_reference_sites(source) == []


def test_compiled_sel_exprs_key_is_gone_catches_a_real_assignment():
    """C9 perturbation twin, half 2: a real subscript assignment reintroducing the key
    must fail the checker."""
    source = inspect.getsource(analytical_loop) + '\nbranch_cfg["compiled_sel_exprs"] = []\n'
    sites = _compiled_sel_exprs_reference_sites(source)
    assert sites != [], (
        "perturbation twin: checker did not detect a deliberately reintroduced "
        'branch_cfg["compiled_sel_exprs"] = [] assignment'
    )


# ---------------------------------------------------------------------------
# C2: perturbation twin -- the identical checker function, applied to a source
# string that DOES contain a compile(...) call, must report that site.
# ---------------------------------------------------------------------------

def test_no_eval_or_compile_call_sites_in_analytical_loop_perturb():
    source = inspect.getsource(analytical_loop)
    mutated_source = source.replace(
        "    selections = cfg.get(\"selections\")\n",
        "    compile('1', '<x>', 'eval')\n    selections = cfg.get(\"selections\")\n",
        1,
    )
    assert mutated_source != source, "mutation did not change the source -- fix the splice"

    sites = _eval_or_compile_call_sites(mutated_source)
    assert sites != [], (
        "perturbation twin: checker did not detect a deliberately reintroduced compile() "
        "call -- the checker function itself would not catch a regression"
    )


# ---------------------------------------------------------------------------
# Cycle 2 (re-specification): M1 -- restore the early syntax/validation gate
# that the removed compile() loop used to provide, bounded this time through
# fce_web.safe_eval.compile_expr rather than a bare compile().
# ---------------------------------------------------------------------------

def _cfg_with_sel_exprs(sel_exprs):
    """A minimal analysis config carrying the given selection expressions, otherwise
    identical in shape to ``tests/test_run_context.py``'s ``_cfg`` -- one selection
    branch, no histograms, no data on disk (irrelevant here: validation must reject
    before any data file is touched)."""
    return {
        "detector": "IDEA",
        "energy": "91 GeV",
        "selections": [{
            "h5_sel": "deadbeef",
            "sel_exprs": sel_exprs,
            "node_name": "test-selection",
            "nid": 1,
            "histograms": [],
        }],
    }


def test_run_physics_loop_rejects_a_malformed_sel_expr_before_returning():
    """C6: a malformed selection expression is rejected before ``run_physics_loop``
    returns a RunResult that looks like a completed run. On ``main`` this was a bare
    ``SyntaxError``; the assertion here is on the raised/surfaced error, never on
    ``processed_any``."""
    cfg = _cfg_with_sel_exprs(["l1.pt >>> 20"])
    ctx = RunContext()

    with pytest.raises(UnsafeExpression) as excinfo:
        analytical_loop.run_physics_loop(cfg, ["X1"], ctx)

    assert "l1.pt >>> 20" in str(excinfo.value), (
        "rejection message must name the offending expression"
    )


def test_run_physics_loop_rejects_sel_expr_over_max_expr_length_bound():
    """C8, cap 1: an expression longer than MAX_EXPR_LENGTH is rejected at this layer
    with UnsafeExpression -- the bound the removed bare compile() never had."""
    too_long = "l1.pt > 0 and " + " and ".join(["l1.pt > 0"] * MAX_EXPR_LENGTH)
    assert len(too_long) > MAX_EXPR_LENGTH
    cfg = _cfg_with_sel_exprs([too_long])
    ctx = RunContext()

    with pytest.raises(UnsafeExpression) as excinfo:
        analytical_loop.run_physics_loop(cfg, ["X1"], ctx)

    assert "too long" in str(excinfo.value)


def test_run_physics_loop_rejects_sel_expr_over_max_ast_nodes_bound():
    """C8, cap 2: an expression under MAX_EXPR_LENGTH in characters but over
    MAX_AST_NODES in parsed complexity is rejected at this layer with
    UnsafeExpression."""
    too_complex = "1" + "+1" * (MAX_AST_NODES + 5)
    assert len(too_complex) <= MAX_EXPR_LENGTH
    cfg = _cfg_with_sel_exprs([too_complex])
    ctx = RunContext()

    with pytest.raises(UnsafeExpression) as excinfo:
        analytical_loop.run_physics_loop(cfg, ["X1"], ctx)

    assert "too complex" in str(excinfo.value)
