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

import ast
import dataclasses
import math
import os
import subprocess
import sys
import time

import pytest
import vector

from fce_web.safe_eval import (
    MAX_AST_NODES,
    MAX_EXPR_LENGTH,
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
        # A long numeric literal: over MAX_EXPR_LENGTH in characters but only
        # 3 AST nodes (Expression, Compare, Constant -- well, Compare's two
        # operands add a couple more, but nowhere near MAX_AST_NODES), so
        # this trips the length cap and only the length cap. The old payload
        # ("l1.pt > 0" + " and l1.pt > 0" * 200) was ~2900 characters *and*
        # several hundred AST nodes, so it would still have raised with
        # MAX_EXPR_LENGTH disabled entirely -- it was accidentally testing
        # the node-count cap, not the one it was named for.
        expr = "l1.pt > " + "0" * 501
        assert len(expr) > MAX_EXPR_LENGTH
        node_count = len(list(ast.walk(ast.parse(expr, mode="eval"))))
        assert node_count < MAX_AST_NODES // 2  # comfortably under, isolates the caps
        with pytest.raises(UnsafeExpression):
            compile_expr(expr)

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
        # B-006 re-specification, criterion 12: the old
        # `"l1.pt * l1.pt" in message or "*" in message` clause was vacuous
        # -- the next line's `"**" in message` already guarantees "*" in
        # message, so the first clause could never be the reason this
        # assertion passed or failed. This asserts the concrete replacement
        # text is present, not merely some substring containing "*".
        assert "l1.pt * l1.pt" in message
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


#: The exact string the child process prints, on its own line, if and only
#: if the escape reached the real `__import__`. Checked against stdout, not
#: inferred from exit code alone -- see `_run_reference_escape_proof`.
_ESCAPE_PROOF_SENTINEL = "ESCAPE-PROOF-REACHED-REAL-IMPORT"

#: Environment variables that change whether a bare `assert` compiles into
#: *a subprocess's* bytecode at all -- stripped from the grandchild's `env`
#: in `_run_reference_escape_proof` (see criterion 11) so that a
#: `PYTHONOPTIMIZE` inherited from this test process cannot silently
#: de-assert a future version of that child script the way it de-asserted
#: the pre-criterion-11 one, which used a bare `assert` and would then have
#: exited 0 having checked nothing. The script that ships today does not
#: use `assert` -- it branches explicitly on the escape result and only
#: prints `_ESCAPE_PROOF_SENTINEL` on success -- so removing this tuple does
#: not currently change the child's behaviour; verified by mutating the
#: filter to a no-op and re-running `_run_reference_escape_proof` directly
#: with `PYTHONOPTIMIZE=1` set, which still returns 0 and still prints the
#: sentinel. This tuple is defence-in-depth against the child script
#: regaining a bare `assert` later, not a guard this test currently
#: exercises. It does **not** protect the assertions in *this* test module:
#: running `pytest` itself under `PYTHONOPTIMIZE=1` strips the bare
#: `assert`s in these test functions regardless of anything this tuple
#: filters, because that stripping happens in this process's own bytecode
#: compilation, before any subprocess `env` dict is ever built. Do not read
#: a passing suite under `PYTHONOPTIMIZE=1` as evidence of anything.
_ASSERT_STRIPPING_ENV_VARS = ("PYTHONOPTIMIZE", "PYTHONDONTWRITEBYTECODE")


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

    B-006 re-specification, criterion 11: the child no longer proves success
    with a bare ``assert`` (compiled out entirely under ``PYTHONOPTIMIZE``,
    letting the script exit 0 having checked nothing) and no longer inherits
    the parent's environment (so an inherited ``PYTHONOPTIMIZE`` cannot
    strip that assert without the test knowing). The child instead branches
    explicitly: on success it prints a fixed sentinel string and exits 0; on
    failure -- whether the escape didn't reach ``__import__``, or raised --
    it prints nothing and exits nonzero. The caller checks both the exit
    code and the sentinel in stdout, so a child that exits 0 without having
    printed the sentinel (e.g. because the whole check was compiled away)
    is still caught.
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
        "try:\n"
        "    escape = eval(expr, {'__builtins__': pf._SAFE_BUILTINS}, {'l1': l1})\n"
        "except Exception as exc:\n"
        "    print(f'ESCAPE-PROOF-RAISED: {exc!r}', file=sys.stderr)\n"
        "    raise SystemExit(1)\n"
        "if escape is __import__:\n"
        f"    print({_ESCAPE_PROOF_SENTINEL!r})\n"
        "    raise SystemExit(0)\n"
        "print('ESCAPE-PROOF-FAILED: did not hand back the real __import__', "
        "file=sys.stderr)\n"
        "raise SystemExit(1)\n"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in _ASSERT_STRIPPING_ENV_VARS
    }
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
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

    Checks both the exit code *and* the positive sentinel in stdout -- see
    criterion 11 in the B-006 re-specification -- so this cannot pass
    because a stripped assertion let an empty script exit 0.
    """
    reference_root = _reference_root()
    if not os.path.isdir(reference_root):
        pytest.skip(f"reference checkout not available at {reference_root!r}")

    result = _run_reference_escape_proof(reference_root)
    assert result.returncode == 0, (
        "reference escape proof failed in its subprocess "
        f"(exit {result.returncode}):\n{result.stderr}"
    )
    assert _ESCAPE_PROOF_SENTINEL in result.stdout, (
        "subprocess exited 0 but never printed the success sentinel -- "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_reference_escape_proof_still_proves_the_escape_under_pythonoptimize():
    # B-006 re-specification, criterion 11: this is the literal repro
    # command from the cycle-3 review
    # ("$ PYTHONOPTIMIZE=1 pytest tests/test_safe_eval.py -q -k reference"
    # -> "2 passed", proving nothing), run one call closer to the metal --
    # directly against `_run_reference_escape_proof` with `PYTHONOPTIMIZE=1`
    # forced into this *test* process's environment for the duration of the
    # call, restored after. If `_run_reference_escape_proof` still inherited
    # the caller's environment (the cycle-3 defect), the grandchild would
    # run de-asserted and this would still pass having proved nothing --
    # exactly why the assertion below checks the positive sentinel, not
    # just the exit code.
    reference_root = _reference_root()
    if not os.path.isdir(reference_root):
        pytest.skip(f"reference checkout not available at {reference_root!r}")

    old_value = os.environ.get("PYTHONOPTIMIZE")
    os.environ["PYTHONOPTIMIZE"] = "1"
    try:
        result = _run_reference_escape_proof(reference_root)
    finally:
        if old_value is None:
            os.environ.pop("PYTHONOPTIMIZE", None)
        else:
            os.environ["PYTHONOPTIMIZE"] = old_value

    assert result.returncode == 0, (
        "reference escape proof failed in its subprocess even with the "
        f"env stripped (exit {result.returncode}):\n{result.stderr}"
    )
    assert _ESCAPE_PROOF_SENTINEL in result.stdout, (
        "subprocess exited 0 but never printed the success sentinel while "
        f"the caller's PYTHONOPTIMIZE=1 -- stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )


def test_reference_checkout_does_not_leak_into_this_process():
    """Nothing from the reference checkout is reachable from this process,
    by any mechanism, after the escape proof above has run.

    B-006 re-specification, suggested-minor: this docstring used to say the
    check ran "after the exploit proof above has run", true when cycle 2's
    proof executed the reference module in-process. Since cycle 3 the proof
    (``test_reference_eval_is_exploitable``) runs the reference module in a
    *subprocess* -- see ``_run_reference_escape_proof`` -- so there is no
    ordering dependency left to describe: this test's assertions would hold
    identically whether that test ran first, ran at all, or is skipped.
    What is actually being checked is unconditional: this process has never
    imported anything from the reference checkout, and its ``sys.path`` was
    never mutated to point at it, regardless of what other tests in this
    session did.

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

#: B-013 cycle 4, C8 (R3/M2 of PR #17's cycle-3 review, retired C6/C7): the
#: prose-parsing meta-test above was defeated in both directions -- a false
#: docstring ("at no point invokes __init__", "elides the constructor
#: entirely") could be worded around the cue list (R3), and a *true*
#: rewording of the very same paragraph ("does call __init__ again and
#: __post_init__ does run; the identity check simply does not fire")
#: tripped the negation cues and went red for stating the correct fact
#: (M2). No cue list closes both directions at once, because "is this
#: wording a negation" is not decidable from a fixed vocabulary. What is
#: decidable is whether the paragraph is *the one already reviewed* --
#: hence an exact-string pin instead of a polarity classifier. These are
#: the two route clauses of CompiledExpr.__doc__, held here as golden
#: literals and compared after whitespace normalisation only.
_REPLACE_ROUTE_START = "``dataclasses.replace(good, code=evil)``"
_REPLACE_ROUTE_END = "is substituted;"
_REPLACE_ROUTE_GOLDEN = (
    "``dataclasses.replace(good, code=evil)`` **does** call ``__init__`` "
    "again, and ``__post_init__`` **does** run, but its identity check has "
    "nothing to catch because the legitimately-earned ``proof`` field is "
    "reused verbatim and only ``code`` is substituted;"
)

_NEW_ROUTE_START = "``object.__new__(CompiledExpr)``"
_NEW_ROUTE_END = "entirely."
_NEW_ROUTE_GOLDEN = (
    "``object.__new__(CompiledExpr)`` followed by ``object.__setattr__`` on "
    "each field is the route that actually **skips** ``__init__`` (and "
    "therefore ``__post_init__``) entirely."
)

#: B-016, C1: the two clause golden above are pinned by finding a start and
#: end marker *inside* the docstring, so a contradicting statement placed
#: outside both -- before the first marker, after the last, or spliced
#: between the two clauses -- moves neither marker and changes nothing the
#: extraction looks at. It is caught here instead, by pinning the *entire*
#: docstring (whitespace normalised, same as the clause goldens) rather
#: than any substring of it. Anything that changes anywhere in the
#: docstring is a mismatch against this golden, by construction.
_FULL_DOCSTRING_GOLDEN = (
    'An expression that has been parsed, validated, and compiled. '
    'Immutable and holds no reference to any per-run or per-event state '
    '-- the same :class:`CompiledExpr` can be reused, from any number of '
    'threads, across every event in a run and across runs. The '
    'constructor is enforced-private: it requires ``proof`` to be the '
    'module-private :data:`_PROOF` sentinel, which only '
    ':func:`compile_expr` can supply. Calling ``CompiledExpr(source, '
    'code, proof)`` from outside this module -- the ordinary way a caller '
    'would try to build one, with an unvalidated ``code`` object and any '
    '``proof`` value it can name -- raises :class:`UnsafeExpression`. '
    'That is the property this guard was built for and the only one it '
    'enforces. **What this does not defend against**, stated explicitly '
    'because B-008 is expected to treat this type as a safety '
    'certificate: a caller already executing arbitrary Python *in this '
    'process* can still produce a ``CompiledExpr`` wrapping an arbitrary '
    'code object, by two routes with *different* relationships to '
    '``__init__``/``__post_init__`` -- ``dataclasses.replace(good, '
    'code=evil)`` **does** call ``__init__`` again, and ``__post_init__`` '
    '**does** run, but its identity check has nothing to catch because '
    'the legitimately-earned ``proof`` field is reused verbatim and only '
    '``code`` is substituted; ``object.__new__(CompiledExpr)`` followed '
    'by ``object.__setattr__`` on each field is the route that actually '
    '**skips** ``__init__`` (and therefore ``__post_init__``) entirely. '
    'Both were demonstrated in the B-006 re-specification review. Neither '
    "is reachable from a student's typed expression, or from anything "
    'that only calls :func:`compile_expr` and :func:`evaluate` -- '
    'reaching them requires the caller to already be running arbitrary '
    'code in this interpreter, at which point it has no need of '
    '``CompiledExpr`` to do so. So: **a ``CompiledExpr`` obtained from '
    ':func:`compile_expr` is proof its ``source`` passed validation.** It '
    'is *not* a capability-secure token that resists forgery by '
    'co-located Python code -- do not use it as a boundary against '
    'anything already running inside this process, only as a boundary '
    'against unvalidated *input* reaching :func:`evaluate`.'
)

#: One sentence, repeated in every failure message below, so a red here is
#: never mistaken for a finding: a golden pin cannot tell a truer wording
#: from a false one, so any edit to this paragraph -- including a correction
#: -- fails until the golden is updated deliberately to match it.
_DRIFT_GUARD_NOTE = (
    "this is an exact-string pin, not a truth check: a red here means the "
    "docstring paragraph changed, not that it is wrong -- if the new wording "
    "is accurate, update the golden constant in this test to match it"
)


def _normalise_whitespace(text: str) -> str:
    """Collapse all whitespace runs (including newlines) to single spaces
    and strip the ends, so a golden literal need not reproduce the
    docstring's line-wrapping column."""
    return " ".join(text.split())


def _extract_route_clause(doc: str, start_marker: str, end_marker: str, label: str) -> str:
    """The whitespace-normalised text of one route clause in `doc`, bounded
    by two fixed markers. Fails via `pytest.fail` (carrying the drift-guard
    note) rather than letting `ValueError` from a missing marker propagate,
    so every red -- marker gone or golden mismatch -- explains itself."""
    if start_marker not in doc:
        pytest.fail(
            f"{label}: docstring no longer contains {start_marker!r} -- "
            f"{_DRIFT_GUARD_NOTE}"
        )
    start = doc.index(start_marker)
    if end_marker not in doc[start:]:
        pytest.fail(
            f"{label}: docstring contains {start_marker!r} but not a "
            f"following {end_marker!r} -- {_DRIFT_GUARD_NOTE}"
        )
    end = doc.index(end_marker, start) + len(end_marker)
    return _normalise_whitespace(doc[start:end])


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

    def test_compiled_expr_missing_proof_field_is_a_typeerror(self):
        # A plain arity check, not a test of the guard: dataclasses raises
        # TypeError for a missing positional argument whether or not
        # __post_init__ enforces anything at all. Kept because it documents
        # that `proof` really is a required field, but
        # test_compiled_expr_rejects_a_forged_proof below is the one that
        # actually exercises the guard -- see B-006 cycle-3 review, required
        # finding: this test alone passes identically under
        # `CompiledExpr.__post_init__ = lambda self: None`.
        code = compile("1 + 1", "<not-validated>", "eval")
        with pytest.raises(TypeError):
            CompiledExpr(source="1 + 1", code=code)  # missing the proof field

    def test_compiled_expr_rejects_a_forged_proof(self):
        # B-006 re-specification, criterion 9: the cycle-3 test above calls
        # CompiledExpr with the wrong arity, so it raises dataclasses' own
        # "missing positional argument" TypeError whether or not
        # __post_init__'s identity check exists at all -- it cannot
        # distinguish "the guard fired" from "the guard was never called".
        # This call supplies all three fields, so the *only* way it can
        # raise is the identity check in __post_init__ rejecting a proof
        # object that is not the module-private _PROOF sentinel.
        code = compile("1 + 1", "<not-validated>", "eval")
        with pytest.raises(UnsafeExpression):
            CompiledExpr(source="1 + 1", code=code, proof=object())

    def test_dataclasses_replace_is_a_known_limitation_not_a_guarantee(self):
        # B-006 re-specification, criterion 10: the class docstring used to
        # claim outright that a caller "cannot construct a CompiledExpr
        # around an unvalidated code object". dataclasses.replace() calls
        # __init__ again, but with a legitimately-earned `proof` reused
        # verbatim and only `code` substituted -- the identity check in
        # __post_init__ has nothing to catch, because `proof` really is
        # `_PROOF`. This test names and pins the *limitation* the corrected
        # docstring now documents explicitly under "what this does not
        # defend against" -- it is not a specification of desired behaviour,
        # and a future change that started rejecting this forgery would not
        # be a regression against this test's intent. Only a change that
        # *silently* stopped raising here without anyone noticing would be:
        # the test exists so that if this ever becomes fixable cheaply, the
        # person doing it sees this comment rather than reading a green test
        # as "this is fine, leave it".
        good = compile_expr("1 + 1")
        evil_code = compile(
            "().__class__.__bases__[0].__subclasses__()[0]", "<evil>", "eval"
        )
        forged = dataclasses.replace(good, code=evil_code)
        # The forged object exists and evaluate() runs the substituted
        # code -- this pins the limitation, it does not bless it as safe.
        assert evaluate(forged, {}) is type

    def test_object_new_is_a_known_limitation_not_a_guarantee(self):
        # B-006 re-specification, criterion 10, second route: object.__new__
        # plus object.__setattr__ never calls __init__ at all, so
        # __post_init__ never runs. Same conclusion as the replace() case
        # above, and the same caveat: this pins a known limitation for
        # visibility, it is not a specification that this must keep working.
        evil_code = compile(
            "().__class__.__bases__[0].__subclasses__()[0]", "<evil>", "eval"
        )
        forged = object.__new__(CompiledExpr)
        object.__setattr__(forged, "source", "x")
        object.__setattr__(forged, "code", evil_code)
        object.__setattr__(forged, "proof", object())
        assert evaluate(forged, {}) is type

    def test_compiled_expr_guard_is_caught_by_mutation(self, monkeypatch):
        # Mutation test for the assertion above, by monkeypatch per
        # .claude/backend/CLAUDE.md §2 -- never by editing a tracked file.
        # Named mutation: replace __post_init__ with a no-op, exactly the
        # cycle-3 review's `se.CompiledExpr.__post_init__ = lambda self:
        # None`, which produced "113 passed" against the old test. Against
        # this test it must fail: with the guard gone, constructing a
        # CompiledExpr around a forged proof no longer raises anything, so
        # pytest.raises(UnsafeExpression) itself fails with
        # "DID NOT RAISE".
        monkeypatch.setattr(CompiledExpr, "__post_init__", lambda self: None)
        code = compile("1 + 1", "<not-validated>", "eval")
        with pytest.raises(pytest.fail.Exception):
            with pytest.raises(UnsafeExpression):
                CompiledExpr(source="1 + 1", code=code, proof=object())

    def test_forgery_routes_differ_in_post_init_call_mechanism(self, monkeypatch):
        # B-013 cycle 2, C5: pins the *mechanism* of the two forgery routes
        # above by observation, not by prose -- the cycle-1 review
        # established that dataclasses.replace() DOES call __init__ (and
        # therefore __post_init__), and that the identity check inside it
        # runs and simply has nothing to catch because the legitimately-
        # earned `proof` field is carried over unchanged; object.__new__()
        # is the route that skips __init__/__post_init__ entirely. A
        # counter wrapped around the real __post_init__ (monkeypatch, not a
        # tracked-file edit) makes that difference observable rather than
        # asserted.
        calls = []
        real_post_init = CompiledExpr.__post_init__

        def counting_post_init(self):
            calls.append(self)
            real_post_init(self)

        monkeypatch.setattr(CompiledExpr, "__post_init__", counting_post_init)

        good = compile_expr("1 + 1")
        evil_code = compile("1 + 1", "<evil>", "eval")

        calls.clear()  # compile_expr("1 + 1") above already called it once
        forged_by_replace = dataclasses.replace(good, code=evil_code)
        assert len(calls) == 1, (
            "dataclasses.replace() must call __init__/__post_init__ exactly "
            "once -- it did not, contradicting the cycle-1 review's finding"
        )
        # The identity check passed silently: it has nothing to catch,
        # because the legitimate proof was carried over verbatim.
        assert forged_by_replace.proof is good.proof

        calls.clear()
        forged_by_new = object.__new__(CompiledExpr)
        object.__setattr__(forged_by_new, "source", "x")
        object.__setattr__(forged_by_new, "code", evil_code)
        object.__setattr__(forged_by_new, "proof", object())
        # This assertion pins a CPython invariant -- object.__new__() never
        # calls __init__ (and therefore never __post_init__) for *any*
        # class, by language definition, not by anything safe_eval.py does.
        # It cannot fail from a change to this module; it is the control
        # arm against which the replace-route assertion above (which *can*
        # fail, and did, in the cycle-1 review) is contrasted. Only that
        # assertion is falsifiable from a change to safe_eval.py.
        assert len(calls) == 0, (
            "object.__new__() must never call __init__/__post_init__ -- it "
            "did, contradicting the cycle-1 review's finding"
        )

    def test_compiled_expr_docstring_pin_catches_mutation_anywhere(self, monkeypatch):
        # B-016, C1: B-013's route-clause markers only see the two pinned
        # clauses -- a contradicting statement placed *outside* both of them
        # (before the first, after the last, or between them) changed
        # nothing that the marker-based extraction above looks at, so it
        # passed silently. Proven here by monkeypatch (never a tracked-file
        # edit) at exactly the three positions the drift can appear: at the
        # very start of the docstring, at its very end, and spliced into its
        # middle -- and asserted against the *whole* pinned docstring, not a
        # substring of it, precisely because a partial pin is the hole.
        original = CompiledExpr.__doc__
        claim = "\n    Neither route ever executes __init__.\n"
        half = len(original) // 2
        mutations = {
            "prepend": claim + original,
            "append": original + claim,
            "middle": original[:half] + claim + original[half:],
        }
        for label, mutated in mutations.items():
            monkeypatch.setattr(CompiledExpr, "__doc__", mutated, raising=False)
            with pytest.raises(AssertionError):
                whole_doc = _normalise_whitespace(CompiledExpr.__doc__)
                assert whole_doc == _FULL_DOCSTRING_GOLDEN, label
            monkeypatch.setattr(CompiledExpr, "__doc__", original, raising=False)

    def test_compiled_expr_docstring_route_clauses_are_pinned_exactly(self):
        # B-013 cycle 4, C8 (retires C6/C7): cycles 2 and 3 both tried to
        # *classify* the docstring's wording (keyword presence, then
        # negation polarity) and both were defeated -- R3 found a false
        # docstring that passed by dodging the cue list, M2 found a *true*
        # rewording of the same fact that failed by tripping it. Classifying
        # prose for truth is not decidable from a fixed vocabulary in either
        # direction. Comparing it to a known-good literal is: this pins the
        # two route clauses of CompiledExpr.__doc__ exactly (whitespace
        # normalised only) against the mechanism pinned by observation in
        # test_forgery_routes_differ_in_post_init_call_mechanism above. A
        # red here is a drift guard, not a truth check -- see
        # _DRIFT_GUARD_NOTE and each assertion's message.
        doc = CompiledExpr.__doc__

        replace_clause = _extract_route_clause(
            doc, _REPLACE_ROUTE_START, _REPLACE_ROUTE_END, "dataclasses.replace route"
        )
        assert replace_clause == _REPLACE_ROUTE_GOLDEN, (
            "CompiledExpr's docstring wording for the dataclasses.replace "
            f"route no longer matches the pinned golden -- {_DRIFT_GUARD_NOTE}"
            f"\n  actual: {replace_clause!r}"
            f"\n  golden: {_REPLACE_ROUTE_GOLDEN!r}"
        )

        new_clause = _extract_route_clause(
            doc, _NEW_ROUTE_START, _NEW_ROUTE_END, "object.__new__ route"
        )
        assert new_clause == _NEW_ROUTE_GOLDEN, (
            "CompiledExpr's docstring wording for the object.__new__ route "
            f"no longer matches the pinned golden -- {_DRIFT_GUARD_NOTE}"
            f"\n  actual: {new_clause!r}"
            f"\n  golden: {_NEW_ROUTE_GOLDEN!r}"
        )

        # B-016, C1: the two marker-bounded checks above see only the text
        # between their own start and end markers -- a contradicting
        # statement placed before the first marker, after the last, or
        # spliced between the two clauses moves neither marker and passes
        # both assertions above untouched. Closed by additionally pinning
        # the docstring in its entirety, so a mutation anywhere in it is a
        # mismatch against this golden by construction, not by classifying
        # where a marker happens to sit.
        whole_doc = _normalise_whitespace(doc)
        assert whole_doc == _FULL_DOCSTRING_GOLDEN, (
            "CompiledExpr's docstring no longer matches the pinned golden in "
            f"its entirety -- {_DRIFT_GUARD_NOTE}"
            f"\n  actual: {whole_doc!r}"
            f"\n  golden: {_FULL_DOCSTRING_GOLDEN!r}"
        )


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
