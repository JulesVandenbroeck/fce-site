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

import fce_web.engine.analytical_loop as analytical_loop


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


# ---------------------------------------------------------------------------
# C1 continued: the dead write this compile loop fed is also gone.
# ---------------------------------------------------------------------------

def test_compiled_sel_exprs_key_is_gone():
    source = inspect.getsource(analytical_loop)
    assert "compiled_sel_exprs" not in source, (
        "compiled_sel_exprs had zero readers (path_filter.filter_raw_event_data always "
        "recompiles cfg['sel_exprs'] itself -- path_filter.py:596-600) and should have been "
        "removed entirely, not just bounded"
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
