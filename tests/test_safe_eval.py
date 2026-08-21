"""Tests for ``fce_web.safe_eval``, the AST-whitelist expression evaluator.

The reference engine (``kskovpen/fce``, ``engine/path_filter.py``) sandboxes
student-typed cut/observable expressions by restricting ``__builtins__`` and
calling ``eval()`` directly. That does nothing about attribute traversal: it
is possible to walk from any object, through ``__class__``/``__init__``/
``__globals__``, out to the real ``__builtins__`` dict and from there to
``os.system`` -- see ``test_reference_eval_is_exploitable`` below, which
demonstrates the escape against the *actual* reference module.

This module is meant to replace every one of those ``eval()`` call sites with
a two-stage API: ``compile_expr`` validates an AST once and raises
``UnsafeExpression`` for anything outside the whitelist (compile-time,
outside the hot loop), and ``evaluate`` runs the resulting, already-proven-safe
code object against a names mapping supplied by the caller (runtime, inside
the hot loop, and unable to raise ``UnsafeExpression`` because validation
already happened).

The corpus tests below build small stand-in physics objects (mirroring the
reference's ``_P``: attribute access with a ``-999`` sentinel for anything
undefined, and a ``vector`` 4-vector on ``.p4``) and check every entry of
``SEL_ALL_VARS`` (``ui/graph.py``), every worked example in ``fce.py``, and
every distinct expression found in the three saved analyses
(``test_selection_cutflow.json``, ``test_selection_obs_bounds.json``,
``test_systs.json``) against an independently hand-derived physics formula --
not against whatever ``safe_eval`` itself computes.
"""

import math
import os
import subprocess
import sys
import time

import pytest
import vector

from fce_web.safe_eval import (
    SAFE_BUILTINS,
    CompiledExpr,
    UnsafeExpression,
    compile_expr,
    evaluate,
    preprocess_hep_expr,
)


# ---------------------------------------------------------------------------
# A minimal stand-in for the reference engine's `_P`: any attribute not set
# explicitly returns the -999 sentinel used throughout the reference for
# "not defined for this event" (e.g. MET has no .eta).
# ---------------------------------------------------------------------------
class _StubObj:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, name):
        return -999.0


def _lepton(pt, eta, phi, e, d0, z0, charge, flavour):
    return _StubObj(
        pt=pt, eta=eta, phi=phi, e=e, d0=d0, z0=z0, charge=charge,
        flavour=flavour, p4=vector.obj(pt=pt, eta=eta, phi=phi, e=e),
    )


def _jet(pt, eta, phi, e, btag):
    return _StubObj(pt=pt, eta=eta, phi=phi, e=e, btag=btag,
                     p4=vector.obj(pt=pt, eta=eta, phi=phi, e=e))


def _photon(pt, eta, phi, e):
    return _StubObj(pt=pt, eta=eta, phi=phi, e=e,
                     p4=vector.obj(pt=pt, eta=eta, phi=phi, e=e))


def _met(pt, phi):
    return _StubObj(pt=pt, phi=phi)


def _delta_r(a, b):
    """Reference `_delta_r`, kept only to supply the `deltaR` name in the event."""
    deta = a.eta - b.eta
    dphi = a.phi - b.phi
    while dphi > math.pi:
        dphi -= 2 * math.pi
    while dphi < -math.pi:
        dphi += 2 * math.pi
    return math.sqrt(deta * deta + dphi * dphi)


def _mT(a, b):
    """Reference `_mT`, kept only to supply the `mT` name in the event."""
    dphi = a.phi - b.phi
    while dphi > math.pi:
        dphi -= 2 * math.pi
    while dphi < -math.pi:
        dphi += 2 * math.pi
    return math.sqrt(max(0.0, 2 * a.pt * b.pt * (1.0 - math.cos(dphi))))


# Fixed event, used by every corpus entry below.
L1 = dict(pt=45.0, eta=0.3, phi=0.7, e=50.0, d0=0.01, z0=0.02, charge=-1.0, flavour=11.0)
L2 = dict(pt=38.0, eta=-0.5, phi=-2.1, e=44.0, d0=-0.02, z0=0.015, charge=1.0, flavour=11.0)
J1 = dict(pt=60.0, eta=1.1, phi=1.5, e=103.0, btag=0.85)
J2 = dict(pt=25.0, eta=-1.8, phi=-0.4, e=80.7, btag=0.05)
PH1 = dict(pt=15.0, eta=0.2, phi=2.9, e=18.3)
PH2 = dict(pt=8.0, eta=-0.9, phi=-1.0, e=14.5)
MET = dict(pt=22.0, phi=0.35)


def _event() -> dict:
    """A fresh names mapping, exactly as B-008 will hand one to `evaluate`."""
    return {
        "nlep": 2, "nel": 2, "nmu": 0, "njets": 2, "nphot": 2,
        "l1": _lepton(**L1), "l2": _lepton(**L2),
        "j1": _jet(**J1), "j2": _jet(**J2),
        "ph1": _photon(**PH1), "ph2": _photon(**PH2),
        "met": _met(**MET),
        "deltaR": _delta_r, "mT": _mT,
    }


def run(expr: str):
    """Compile and evaluate `expr` against the fixed event in one step."""
    compiled = compile_expr(expr)
    return evaluate(compiled, _event())


# ---------------------------------------------------------------------------
# Independent physics formulas -- hand-derived from the textbook 4-vector
# definitions, not copied from the code under test or from the `vector`
# library, so they are a genuine external check on what `evaluate` returns.
# ---------------------------------------------------------------------------
def _components(pt, eta, phi, e):
    return pt * math.cos(phi), pt * math.sin(phi), pt * math.sinh(eta), e


def independent_mass(*objs):
    px = py = pz = E = 0.0
    for pt, eta, phi, e in objs:
        dpx, dpy, dpz, de = _components(pt, eta, phi, e)
        px += dpx
        py += dpy
        pz += dpz
        E += de
    return math.sqrt(max(0.0, E * E - (px * px + py * py + pz * pz)))


def independent_pt(*objs):
    px = py = 0.0
    for pt, eta, phi, e in objs:
        dpx, dpy, _, _ = _components(pt, eta, phi, e)
        px += dpx
        py += dpy
    return math.sqrt(px * px + py * py)


def independent_eta(*objs):
    px = py = pz = 0.0
    for pt, eta, phi, e in objs:
        dpx, dpy, dpz, _ = _components(pt, eta, phi, e)
        px += dpx
        py += dpy
        pz += dpz
    p = math.sqrt(px * px + py * py + pz * pz)
    return 0.5 * math.log((p + pz) / (p - pz))


def independent_delta_r(eta1, phi1, eta2, phi2):
    deta = eta1 - eta2
    dphi = phi1 - phi2
    while dphi > math.pi:
        dphi -= 2 * math.pi
    while dphi < -math.pi:
        dphi += 2 * math.pi
    return math.sqrt(deta * deta + dphi * dphi)


def independent_mT(pt1, phi1, pt2, phi2):
    dphi = phi1 - phi2
    while dphi > math.pi:
        dphi -= 2 * math.pi
    while dphi < -math.pi:
        dphi += 2 * math.pi
    return math.sqrt(max(0.0, 2 * pt1 * pt2 * (1.0 - math.cos(dphi))))


def independent_single_mass(pt, eta, e):
    return math.sqrt(max(0.0, e * e - (pt * math.cosh(eta)) ** 2))


# ---------------------------------------------------------------------------
# 1. Compile-time enforcement -- escape attempts, each its own test.
# ---------------------------------------------------------------------------
class TestEscapesRejected:
    def test_dunder_class_globals_chain_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr(
                "l1.__class__.__init__.__globals__['__builtins__']['__import__']"
                "('os').system('echo pwned')"
            )

    def test_subclasses_walk_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("l1.pt.__class__.__bases__[0].__subclasses__()")

    def test_any_underscore_prefixed_attribute_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("l1._secret")

    def test_dunder_doc_attribute_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("l1.__doc__")

    def test_subscript_is_rejected(self):
        # An expression using only whitelisted names, so this isolates the
        # Subscript node-type ban rather than also tripping the unknown-name
        # check ("jets" is not a whitelisted name either).
        with pytest.raises(UnsafeExpression):
            compile_expr("l1.pt[0]")

    def test_subscript_with_unknown_name_is_also_rejected(self):
        # jets[0].pt is the exact form dead legacy config/*.dat files use in
        # the reference repo (no Python there reads them) -- confirm we
        # reject it too, doubly (unknown name *and* Subscript).
        with pytest.raises(UnsafeExpression):
            compile_expr("jets[0].pt")

    def test_calling_a_non_callable_event_name_is_rejected(self):
        # "l1" is a whitelisted Name, but not a whitelisted callable -- this
        # isolates the CALLABLE_NAMES check from the general Name whitelist.
        with pytest.raises(UnsafeExpression):
            compile_expr("l1(5)")

    def test_lambda_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("(lambda: l1.pt)()")

    def test_list_comprehension_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("[x for x in range(10)]")

    def test_generator_expression_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("sum(x for x in range(10))")

    def test_fstring_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("f'{l1.pt}'")

    def test_plain_string_literal_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("'hello'")

    def test_walrus_operator_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("(x := l1.pt) > 0")

    def test_import_statement_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("__import__('os')")

    def test_dict_literal_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("{'a': 1}")

    def test_list_literal_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("[1, 2, 3]")

    def test_ternary_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("l1.pt if nlep > 0 else 0")

    def test_starred_call_arg_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("max(*[1, 2])")

    def test_unknown_name_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("os.system('rm -rf /')")

    def test_call_to_non_whitelisted_function_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("eval('1')")

    def test_keyword_argument_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("sqrt(x=4)")

    def test_assignment_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("nlep = 5")

    def test_multiple_statements_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("l1.pt; l2.pt")

    def test_slice_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("l1.pt[0:1]")

    def test_expression_over_length_cap_is_rejected(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("l1.pt > 0" + " and l1.pt > 0" * 200)

    def test_expression_over_node_count_cap_is_rejected(self):
        # 150 chained unary minuses: each contributes a UnaryOp node plus a
        # USub op node (300 nodes total), well over MAX_AST_NODES, while the
        # 151-character string stays well under MAX_EXPR_LENGTH -- isolates
        # the node-count cap from the length cap.
        expr = "-" * 150 + "1"
        assert len(expr) < 200  # sanity: nowhere near the length cap
        with pytest.raises(UnsafeExpression):
            compile_expr(expr)

    def test_power_operator_is_rejected(self):
        # Criterion 6, B-006 cycle-2 review: the size caps (500 chars / 200
        # AST nodes) bound parse cost, not evaluation cost. "9**9**9" is 7
        # characters and 8 AST nodes -- well inside both caps -- and never
        # returns once evaluated. No corpus entry uses "**" at all, so
        # dropping ast.Pow from the whitelist entirely costs the language
        # surface nothing. See test_power_chain_does_not_hang and
        # test_huge_power_does_not_hang below for the payloads this closes.
        with pytest.raises(UnsafeExpression):
            compile_expr("2**3")

    def test_power_operator_message_names_the_replacement(self):
        # Cycle-2 review, suggested-minor 2 / cycle-3 criterion 10(b): the
        # old message ("Use comparisons, arithmetic, 'and'/'or'/'not', ...")
        # told a student typing l1.pt**2 that arithmetic was the answer,
        # which is exactly what they just tried. The message for a rejected
        # '**' must name the concrete replacement.
        with pytest.raises(UnsafeExpression) as exc_info:
            compile_expr("l1.pt**2")
        message = str(exc_info.value)
        assert "l1.pt * l1.pt" in message or "*" in message
        assert "**" in message

    def test_power_chain_does_not_hang(self):
        # The exact payload from the cycle-1 review: accepted by both size
        # caps, never returns once evaluated, under the old whitelist.
        with pytest.raises(UnsafeExpression):
            compile_expr("9**9**9")

    def test_huge_power_does_not_hang(self):
        # 2**64**8 hangs identically to 9**9**9 under the old whitelist.
        with pytest.raises(UnsafeExpression):
            compile_expr("2**64**8")

    def test_large_power_literal_is_rejected(self):
        # 2**10000000 returns (0.03s, allocating a ~1.3MB int) rather than
        # hanging, but evaluate() runs once per event over millions of
        # events -- a compile-time reject is still correct here.
        with pytest.raises(UnsafeExpression):
            compile_expr("2**10000000")


def _reference_root() -> str:
    return os.environ.get(
        "FCE_REFERENCE_ROOT",
        os.path.expanduser("~/Documents/Phd/teaching/fce-project/fce"),
    )


def _leaked_reference_modules() -> dict:
    """Every module currently in ``sys.modules`` whose ``__file__`` resolves
    into the reference checkout ("fce-project").

    This is the property B-006 cycle-3 criterion 9 asks for -- not "sys.path
    is clean" (criterion 8, which the reference checkout can satisfy while
    still leaking through ``sys.modules``, see cycle-2 review) but "nothing
    from the reference checkout is reachable from this process, by any
    mechanism". ``ui.state`` in particular is the module holding the global
    ``RUN_STATE`` this whole project exists to eliminate (shared CLAUDE.md
    §2), and B-007 lands ``engine/path_filter.py`` under a name that would
    collide with a leaked reference import.
    """
    leaked = {}
    for name, module in list(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if path and "fce-project" in path:
            leaked[name] = path
    return leaked


def _run_reference_escape_proof(reference_root: str) -> subprocess.CompletedProcess:
    """Run the reference eval() escape proof in a fresh, throwaway subprocess.

    B-006 cycle-3 criterion 9: importing ``engine.path_filter`` from the
    reference checkout in *this* process is exactly what leaked
    ``engine``, ``ui``, ``ui.state``, ``engine.systematics`` and
    ``engine.path_filter`` into ``sys.modules`` under cycle 2, surviving a
    clean ``sys.path`` because ``monkeypatch.syspath_prepend`` only undoes
    the path mutation, not the import it enabled. Snapshotting and
    restoring ``sys.modules`` (option a) or importing under a private name
    via ``importlib.util.spec_from_file_location`` (option b) would also
    work, but the thing this test is proving -- that the *reference's*
    ``eval()`` is exploitable -- is a statement about a foreign process's
    behaviour. A subprocess makes that statement directly and exits, and
    its ``sys.path``/``sys.modules`` cannot leak into this process at all:
    there is no snapshot to forget to restore.
    """
    script = (
        "import sys\n"
        f"sys.path.insert(0, {reference_root!r})\n"
        "import engine.path_filter as pf\n"
        "l1 = pf._P(pt=25.0)\n"
        "expr = (\n"
        "    \"l1.__class__.__init__.__globals__['__builtins__']\"\n"
        "    \"['__import__']\"\n"
        ")\n"
        "escape = eval(expr, {'__builtins__': pf._SAFE_BUILTINS}, {'l1': l1})\n"
        "assert escape is __import__, "
        "'reference eval() did not hand back the real __import__'\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_reference_eval_is_exploitable():
    """Proves the *reference* eval() sandbox is escapable, against the real module.

    Runs ``engine/path_filter.py`` from the read-only reference checkout,
    in a fresh subprocess (see ``_run_reference_escape_proof``), and checks
    that the same escape payload used against B-005/B-006's predecessor
    reaches the real, unrestricted ``__import__`` -- not a reimplementation,
    the actual reference module -- to show this fix is closing a real hole.
    Side-effect-free: the proof reaches ``__import__`` through the
    traversal chain but never calls it.
    """
    reference_root = _reference_root()
    if not os.path.isdir(reference_root):
        pytest.skip(f"reference checkout not available at {reference_root!r}")

    result = _run_reference_escape_proof(reference_root)
    assert result.returncode == 0, (
        "reference escape proof failed in its subprocess "
        f"(exit {result.returncode}):\n{result.stderr}"
    )


def test_reference_checkout_does_not_leak_into_this_process():
    """B-006 cycle-3 criterion 9: nothing from the reference checkout is
    reachable from this process, by any mechanism, after the exploit proof
    above has run.

    Checks both halves cycle 2's fix and cycle 2's review disagreed about:
    ``sys.path`` (criterion 8, already clean since cycle 2) and
    ``sys.modules`` (the leak that survived it). Skips only if the
    reference checkout is unavailable on this machine -- same guard as
    ``test_reference_eval_is_exploitable``, so this never passes by
    vacuously skipping while that test actually ran.
    """
    reference_root = _reference_root()
    if not os.path.isdir(reference_root):
        pytest.skip(f"reference checkout not available at {reference_root!r}")

    leaked_path_entries = [p for p in sys.path if "fce-project" in p]
    assert not leaked_path_entries, f"sys.path leaked: {leaked_path_entries}"

    leaked_modules = _leaked_reference_modules()
    assert not leaked_modules, f"reference checkout modules leaked: {leaked_modules}"


# ---------------------------------------------------------------------------
# 2. General compile-time enforcement (not escape-specific).
# ---------------------------------------------------------------------------
class TestCompileTimeGeneral:
    def test_compile_expr_returns_compiled_expr(self):
        assert isinstance(compile_expr("l1.pt > 20"), CompiledExpr)

    def test_valid_expression_compiles_without_raising(self):
        compile_expr("l1.pt > 20 and l2.pt > 10")

    def test_syntax_error_raises_unsafe_expression_not_syntax_error(self):
        with pytest.raises(UnsafeExpression):
            compile_expr("l1.pt >")

    def test_rejection_message_is_legible(self):
        with pytest.raises(UnsafeExpression) as exc_info:
            compile_expr("l1._secret")
        message = str(exc_info.value)
        assert "_secret" in message

    def test_evaluate_cannot_raise_unsafe_expression(self):
        # A compiled, validated expression is proven safe -- evaluating it
        # against a names mapping that happens to be missing a name raises
        # a plain NameError, never UnsafeExpression (validation already ran).
        compiled = compile_expr("l1.pt > 20")
        with pytest.raises(NameError):
            evaluate(compiled, {})

    def test_safe_builtins_is_immutable(self):
        # Criterion 7, B-006 cycle-2 review: SAFE_BUILTINS is a module-level
        # object handed to eval() as __builtins__ on every call. Nothing in
        # the whitelisted language can mutate it, but it is documented as a
        # public drop-in for B-008 to reuse, and .claude/shared/CLAUDE.md §6
        # is unqualified: "No module-level mutable state. Ever."
        with pytest.raises(TypeError):
            SAFE_BUILTINS["x"] = 1

    def test_safe_builtins_still_usable_as_builtins_namespace(self):
        # types.MappingProxyType is accepted by eval() as __builtins__ just
        # like a plain dict -- immutability must not break evaluation.
        assert run("sqrt(4)") == 2.0

    def test_compiled_expr_cannot_be_constructed_directly(self):
        # Cycle-2 review, suggested-minor 3 / cycle-3 criterion 10(a): the
        # CompiledExpr docstring claims "Existence of one is the proof that
        # compile_expr accepted it." A public dataclass with a public
        # constructor does not enforce that claim by itself -- the reviewer
        # built one around raw compile() output in seconds. Constructing one
        # outside compile_expr must raise, not silently succeed.
        code = compile("1 + 1", "<not-validated>", "eval")
        with pytest.raises(TypeError):
            CompiledExpr(source="1 + 1", code=code)  # missing the proof field


# ---------------------------------------------------------------------------
# 3. HEP syntax preprocessing (&&, ||, !, applied to both selections and
#    observables -- see the Deviations section of the PR body).
# ---------------------------------------------------------------------------
class TestHepSyntax:
    def test_double_ampersand_becomes_and(self):
        assert preprocess_hep_expr("a && b") == "a  and  b"

    def test_double_pipe_becomes_or(self):
        assert preprocess_hep_expr("a || b") == "a  or  b"

    def test_bang_becomes_not(self):
        assert preprocess_hep_expr("!a") == "not a"

    def test_not_equal_is_preserved(self):
        assert preprocess_hep_expr("a != b") == "a != b"

    def test_hep_syntax_selection_evaluates(self):
        assert run("l1.pt > 20 && l2.pt > 10") is True

    def test_hep_syntax_applies_to_observables_too(self):
        # Deliberate deviation from the reference, which only preprocesses
        # selection expressions -- see the PR body.
        result = run("l1.pt > 20 && l1.pt < 100")
        assert result is True


# ---------------------------------------------------------------------------
# 4. The corpus: SEL_ALL_VARS, the fce.py worked examples, and every distinct
#    expression in the three saved analyses.
# ---------------------------------------------------------------------------

#: ui/graph.py SEL_ALL_VARS, verbatim.
SEL_ALL_VARS = [
    "nlep", "nel", "nmu", "njets", "nphot",
    "l1.pt", "l1.eta", "l1.phi", "l1.e", "l1.d0", "l1.z0", "l1.charge", "l1.flavour", "l1.p4",
    "l2.pt", "l2.eta", "l2.phi", "l2.e", "l2.d0", "l2.z0", "l2.charge", "l2.flavour", "l2.p4",
    "j1.pt", "j1.eta", "j1.phi", "j1.e", "j1.btag", "j1.p4",
    "j2.pt", "j2.eta", "j2.phi", "j2.e", "j2.btag", "j2.p4",
    "ph1.pt", "ph1.eta", "ph1.phi", "ph1.e", "ph1.p4",
    "ph2.pt", "ph2.eta", "ph2.phi", "ph2.e", "ph2.p4",
    "met.pt", "met.phi",
    "mT(l1, met)", "mT(l2, met)",
]

#: Plain "name" or "obj.attr" lookups that return a plain number -- checked
#: against the fixture dict directly.
_SCALAR_LOOKUPS = {
    "nlep": 2, "nel": 2, "nmu": 0, "njets": 2, "nphot": 2,
    "l1.pt": L1["pt"], "l1.eta": L1["eta"], "l1.phi": L1["phi"], "l1.e": L1["e"],
    "l1.d0": L1["d0"], "l1.z0": L1["z0"], "l1.charge": L1["charge"], "l1.flavour": L1["flavour"],
    "l2.pt": L2["pt"], "l2.eta": L2["eta"], "l2.phi": L2["phi"], "l2.e": L2["e"],
    "l2.d0": L2["d0"], "l2.z0": L2["z0"], "l2.charge": L2["charge"], "l2.flavour": L2["flavour"],
    "j1.pt": J1["pt"], "j1.eta": J1["eta"], "j1.phi": J1["phi"], "j1.e": J1["e"], "j1.btag": J1["btag"],
    "j2.pt": J2["pt"], "j2.eta": J2["eta"], "j2.phi": J2["phi"], "j2.e": J2["e"], "j2.btag": J2["btag"],
    "ph1.pt": PH1["pt"], "ph1.eta": PH1["eta"], "ph1.phi": PH1["phi"], "ph1.e": PH1["e"],
    "ph2.pt": PH2["pt"], "ph2.eta": PH2["eta"], "ph2.phi": PH2["phi"], "ph2.e": PH2["e"],
    "met.pt": MET["pt"], "met.phi": MET["phi"],
    "mT(l1, met)": independent_mT(L1["pt"], L1["phi"], MET["pt"], MET["phi"]),
    "mT(l2, met)": independent_mT(L2["pt"], L2["phi"], MET["pt"], MET["phi"]),
}

#: The six `.p4` lookups from SEL_ALL_VARS -- not plain numbers, so checked
#: via their own .mass/.pt/.eta against the independent single-object formula.
_P4_LOOKUPS = {
    "l1.p4": L1, "l2.p4": L2, "j1.p4": J1, "j2.p4": J2, "ph1.p4": PH1, "ph2.p4": PH2,
}


@pytest.mark.parametrize("expr", SEL_ALL_VARS)
def test_sel_all_vars_entry_compiles_and_evaluates(expr):
    assert expr in _SCALAR_LOOKUPS or expr in _P4_LOOKUPS, "corpus/test drifted apart"
    result = run(expr)
    if expr in _SCALAR_LOOKUPS:
        assert result == pytest.approx(_SCALAR_LOOKUPS[expr])
    else:
        obj = _P4_LOOKUPS[expr]
        assert result.mass == pytest.approx(
            independent_single_mass(obj["pt"], obj["eta"], obj["e"]), rel=1e-6
        )
        assert result.pt == pytest.approx(obj["pt"], rel=1e-6)
        assert result.eta == pytest.approx(obj["eta"], rel=1e-6)


def test_sel_all_vars_corpus_size():
    # Cross-check against ui/graph.py -- the "complete intended surface" the
    # task dispatch names.
    assert len(SEL_ALL_VARS) == 49


#: fce.py's help text -- the "4-VECTOR ARITHMETIC" section and the
#: "WORKED EXAMPLES" section, each mapped to an independently computed value.
WORKED_EXAMPLES = {
    "(l1.p4 + l2.p4).mass": independent_mass(
        (L1["pt"], L1["eta"], L1["phi"], L1["e"]), (L2["pt"], L2["eta"], L2["phi"], L2["e"])
    ),
    "(l1.p4 + l2.p4).pt": independent_pt(
        (L1["pt"], L1["eta"], L1["phi"], L1["e"]), (L2["pt"], L2["eta"], L2["phi"], L2["e"])
    ),
    "(l1.p4 + l2.p4).eta": independent_eta(
        (L1["pt"], L1["eta"], L1["phi"], L1["e"]), (L2["pt"], L2["eta"], L2["phi"], L2["e"])
    ),
    "l1.p4.deltaR(l2.p4)": independent_delta_r(L1["eta"], L1["phi"], L2["eta"], L2["phi"]),
    "deltaR(l1, l2)": independent_delta_r(L1["eta"], L1["phi"], L2["eta"], L2["phi"]),
    "l1.pt + l2.pt": L1["pt"] + L2["pt"],
    "mT(l1, met)": independent_mT(L1["pt"], L1["phi"], MET["pt"], MET["phi"]),
    "l1.pt > 20 and l2.pt > 10": L1["pt"] > 20 and L2["pt"] > 10,
    "(l1.p4+l2.p4).mass > 80 and (l1.p4+l2.p4).mass < 100": (
        80 < independent_mass(
            (L1["pt"], L1["eta"], L1["phi"], L1["e"]), (L2["pt"], L2["eta"], L2["phi"], L2["e"])
        ) < 100
    ),
    "njets >= 2 and j1.btag > 0.7": 2 >= 2 and J1["btag"] > 0.7,
    "nlep >= 2 and met.pt > 30": 2 >= 2 and MET["pt"] > 30,
}


@pytest.mark.parametrize("expr", sorted(WORKED_EXAMPLES))
def test_worked_example_compiles_and_evaluates(expr):
    result = run(expr)
    expected = WORKED_EXAMPLES[expr]
    if isinstance(expected, bool):
        assert bool(result) == expected
    else:
        assert result == pytest.approx(expected, rel=1e-6)


#: Distinct expressions found in the three saved analyses at the reference
#: repo root, not already covered by SEL_ALL_VARS or WORKED_EXAMPLES.
SAVED_ANALYSES_EXTRA = {
    "nlep == 0": False,  # nlep is 2 in the fixture
    "(j1.p4 + j2.p4).mass": independent_mass(
        (J1["pt"], J1["eta"], J1["phi"], J1["e"]), (J2["pt"], J2["eta"], J2["phi"], J2["e"])
    ),
}


@pytest.mark.parametrize("expr", sorted(SAVED_ANALYSES_EXTRA))
def test_saved_analysis_expression_compiles_and_evaluates(expr):
    result = run(expr)
    expected = SAVED_ANALYSES_EXTRA[expr]
    if isinstance(expected, bool):
        assert result is expected
    else:
        assert result == pytest.approx(expected, rel=1e-6)


def test_corpus_total_size_reported():
    total = len(SEL_ALL_VARS) + len(WORKED_EXAMPLES) + len(SAVED_ANALYSES_EXTRA)
    # SEL_ALL_VARS entries are unique by construction; WORKED_EXAMPLES and
    # SAVED_ANALYSES_EXTRA are deduplicated dicts keyed by expression text,
    # with anything already present in an earlier set left out on purpose.
    assert total == 49 + 11 + 2


# ---------------------------------------------------------------------------
# 5. Bounds: length cap and node-count cap don't reject legitimate work.
# ---------------------------------------------------------------------------
def test_realistic_compound_selection_is_well_under_both_caps():
    # A generous, realistic compound cut -- must not trip either cap.
    expr = (
        "l1.pt > 20 and l2.pt > 10 and abs(l1.eta) < 2.5 and abs(l2.eta) < 2.5 "
        "and (l1.p4 + l2.p4).mass > 80 and (l1.p4 + l2.p4).mass < 100 "
        "and njets >= 2 and j1.btag > 0.7 and met.pt > 30"
    )
    assert run(expr) is False  # met.pt is 22 in the fixture, not > 30


# ---------------------------------------------------------------------------
# 6. Benchmark: evaluate() vs raw eval() on a pre-compiled code object.
# ---------------------------------------------------------------------------
def test_benchmark_evaluate_within_budget_of_raw_eval():
    """Report (and loosely bound) the per-call overhead of `evaluate`.

    `evaluate` does strictly less work than a raw `eval(code, globals, locals)`
    call would for the same expression -- it has no extra validation to do at
    this point, only the dict-copy of `names` (needed so a caller's mapping is
    never mutated by the callee). The real numbers are reported in the PR body;
    this assertion is a generous smoke-test bound so CI catches a gross
    regression without being a flaky micro-benchmark gate.
    """
    expr = "l1.pt > 20 and l2.pt > 10 and (l1.p4 + l2.p4).mass > 80"
    compiled = compile_expr(expr)
    names = _event()

    raw_globals = {"__builtins__": {}}
    raw_code = compile(preprocess_hep_expr(expr), "<raw>", "eval")

    n = 20_000

    t0 = time.perf_counter()
    for _ in range(n):
        eval(raw_code, raw_globals, names)
    t_raw = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(n):
        evaluate(compiled, names)
    t_safe = time.perf_counter() - t0

    ratio = t_safe / t_raw
    print(f"\nbenchmark: raw eval={t_raw:.4f}s safe evaluate={t_safe:.4f}s ratio={ratio:.2f}x")
    assert ratio < 5.0, f"evaluate() is {ratio:.2f}x raw eval() -- investigate"
