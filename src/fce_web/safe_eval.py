"""AST-whitelist evaluator for student-typed cut and observable expressions.

The reference engine (``kskovpen/fce``, ``engine/path_filter.py``) evaluates
every cut and observable a student types with::

    eval(expr, {"__builtins__": _SAFE_BUILTINS}, local_vars)

Restricting ``__builtins__`` stops nothing but the most naive escapes: any
ordinary Python object reachable from the expression's namespace can be
walked through ``__class__``, ``__init__``, ``__globals__`` and back out to
the real ``__builtins__`` mapping, from which arbitrary code executes. On a
teacher's machine with a classroom of students connected, that is remote
code execution from a text field. ``tests/test_safe_eval.py`` demonstrates
the escape against the actual reference module.

This module replaces that pattern with two stages:

* :func:`compile_expr` -- parses the expression, walks the AST once, and
  rejects anything outside an explicit whitelist of node types, names, and
  attribute names. Rejection raises :class:`UnsafeExpression`, always here,
  never later. The vendored ``path_filter.py`` (wired up in a later task)
  calls this once, at mission-load or cut-submission time, outside any
  per-event loop.
* :func:`evaluate` -- runs the already-validated code object against a
  ``names`` mapping supplied by the caller (the per-event physics objects).
  It cannot raise :class:`UnsafeExpression`, because everything it runs was
  already proven safe by :func:`compile_expr`. It is called once per event,
  inside the loop that dominates the engine's runtime, so it does no
  validation work of its own -- only the ``eval()`` of a pre-compiled code
  object, the fast path the reference already uses opportunistically (see
  ``observable_code = compile(...)`` in ``path_filter.py``).

Deliberately not built: a tree-walking interpreter that never calls
``compile``/``eval``. It would be 10-50x slower per event, and the caller is
a Python loop over millions of events that already dominates the engine's
wall time. Validation is what makes this safe; compilation is what keeps it
fast enough to use.

The language surface (verified against ``engine/path_filter.py``, its seven
``eval()`` call sites' local-variable dicts plus the one ``compile()`` call
site, ``ui/graph.py``'s ``SEL_ALL_VARS``, and ``fce.py``'s worked examples):

* Names: the per-event scalars ``nlep nel nmu njets nphot``; the per-event
  objects ``l1 l2 j1 j2 ph1 ph2 met``; the two helper functions ``deltaR``
  and ``mT``; and the safe builtins below.
* Attribute access, one or two levels deep: ``.pt .eta .phi .e .d0 .z0
  .charge .flavour .btag`` (plain numbers), ``.p4`` (a 4-vector), and on a
  4-vector ``.mass`` and the method call ``.deltaR(other)``.
* Arithmetic (``+ - * / // %``; note ``**`` is not allowed -- see the
  ``_ALLOWED_NODE_TYPES`` comment on why), comparison (``< <= > >= == !=``),
  boolean (``and or not``, plus the HEP spellings ``&& || !`` translated by
  :func:`preprocess_hep_expr`), and numeric/``None`` literals.
* Calls to the whitelisted functions only, positional arguments only.

Explicitly out of scope, on the basis that no real analysis in the reference
repo uses any of it (see the corpus in ``tests/test_safe_eval.py``, drawn
from ``SEL_ALL_VARS``, the worked examples, and three saved analyses):
subscripting, comprehensions, lambdas, slicing, string/dict/list/set
literals, ``:=``, f-strings, ternaries, and anything with an underscore
prefix.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from types import CodeType, MappingProxyType
from typing import Any, Mapping

#: Raw source length cap, in characters. Generous for anything a student
#: would legitimately type (the longest worked example is well under 100
#: characters) while bounding parse cost for pathological input.
MAX_EXPR_LENGTH = 500

#: AST node-count cap. Bounds parse/validate/compile cost independently of
#: MAX_EXPR_LENGTH -- a short expression can still nest deeply (e.g.
#: "1+1+1+...+1") and blow up node count without approaching the length cap.
MAX_AST_NODES = 200

#: The per-event scalars and objects available at every one of the
#: reference's eval() call sites, plus the two helper functions. Carried
#: across verbatim from ``engine/path_filter.py``'s local_vars/vec_vars
#: dicts.
EVENT_NAMES = frozenset({
    "nlep", "nel", "nmu", "njets", "nphot",
    "l1", "l2", "j1", "j2", "ph1", "ph2", "met",
    "deltaR", "mT",
})

#: ``engine/path_filter.py:18-24``'s ``_SAFE_BUILTINS``, carried over
#: verbatim in content. Supplied as the ``__builtins__`` mapping at evaluation
#: time, so a bare name like ``sqrt`` resolves the same way the reference
#: resolves it. Wrapped in ``MappingProxyType`` so it is read-only: nothing in
#: the whitelisted language can mutate it, but it is a public module-level
#: object (documented as a drop-in for other callers, e.g. B-008), and
#: ``.claude/shared/CLAUDE.md`` §6 is unqualified -- "No module-level mutable
#: state. Ever." ``eval()`` accepts a ``MappingProxyType`` as ``__builtins__``
#: exactly as it accepts a plain ``dict``.
SAFE_BUILTINS: Mapping[str, Any] = MappingProxyType({
    "abs": abs, "max": max, "min": min, "len": len,
    "float": float, "int": int, "bool": bool,
    "sqrt": math.sqrt, "cos": math.cos, "sin": math.sin,
    "tan": math.tan, "pi": math.pi, "exp": math.exp, "log": math.log,
    "True": True, "False": False, "None": None,
})

#: Names that may appear as a bare ``Name`` node: the event names plus every
#: key in SAFE_BUILTINS (functions, constants, and ``pi``).
ALLOWED_NAMES = EVENT_NAMES | frozenset(SAFE_BUILTINS)

#: Names callable as ``name(...)`` -- the safe builtin functions plus the two
#: event-level helper functions ``deltaR`` and ``mT``. Excludes ``pi``,
#: ``True``, ``False``, ``None`` (not callable) and every event object
#: (not callable directly -- only their attributes/methods are).
CALLABLE_NAMES = frozenset({
    "abs", "max", "min", "len", "float", "int", "bool",
    "sqrt", "cos", "sin", "tan", "exp", "log",
    "deltaR", "mT",
})

#: Attribute names reachable on an event object or a 4-vector. One flat set
#: because the reference's own objects are only ever one or two levels deep
#: (e.g. ``l1.p4.mass``) and every attribute name in the language is unique
#: to its role (no name collides between the object level and the 4-vector
#: level), so a single whitelist is sufficient without tracking depth.
ALLOWED_ATTRS = frozenset({
    "pt", "eta", "phi", "e", "d0", "z0", "charge", "flavour",
    "btag", "p4", "mass", "deltaR",
})

#: Every AST node type a validated expression may contain. Anything not
#: listed here is rejected the moment it is seen -- default deny, per
#: ``.claude/backend/CLAUDE.md`` §3.2. This necessarily excludes Subscript,
#: Slice, Lambda, comprehensions (ListComp/SetComp/DictComp/GeneratorExp/
#: comprehension), Dict/List/Set/Tuple literals, JoinedStr/FormattedValue
#: (f-strings), NamedExpr (``:=``), IfExp (ternary), Starred, Import/
#: ImportFrom, and every statement node (Assign, etc. -- most of these can
#: never appear under ``ast.parse(..., mode="eval")`` in the first place,
#: but NamedExpr and IfExp can, so they must be excluded explicitly here).
#:
#: ``ast.Pow`` is deliberately excluded too, even though it can appear under
#: ``mode="eval"``. The size caps below (``MAX_EXPR_LENGTH``,
#: ``MAX_AST_NODES``) bound parse cost, not evaluation cost: ``9**9**9`` is 7
#: characters and 8 AST nodes -- comfortably inside both caps -- and never
#: returns once evaluated, because CPython's big-int exponentiation is
#: unbounded in the size of its result. ``evaluate()`` runs once per event
#: over millions of events, so an accepted expression that can hang is a
#: denial of service on a shared classroom host, exactly the "billion
#: laughs" case ``.claude/backend/CLAUDE.md`` §3.2 asks to be bounded. No
#: corpus entry in ``tests/test_safe_eval.py`` (SEL_ALL_VARS, the worked
#: examples, or the saved-analysis expressions) uses ``**`` at all, so
#: dropping it costs the language surface nothing; a bounded alternative
#: (reject ``Pow`` unless the right operand is a small constant) was
#: considered and rejected as more code for no expressiveness gained.
_ALLOWED_NODE_TYPES = (
    ast.Expression,
    ast.BoolOp, ast.And, ast.Or,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.UnaryOp, ast.UAdd, ast.USub, ast.Not,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Call, ast.Attribute, ast.Name, ast.Load, ast.Constant,
)


class UnsafeExpression(Exception):
    """A student expression was rejected by the AST whitelist.

    Always raised by :func:`compile_expr`, never by :func:`evaluate` -- by
    the time an expression is evaluated, it has already been proven safe.
    The message is written to be shown to the student who typed the
    expression, not just logged: it names the specific construct that was
    rejected and, where useful, what is allowed instead.
    """


@dataclass(frozen=True, slots=True)
class CompiledExpr:
    """An expression that has been parsed, validated, and compiled.

    Immutable and holds no reference to any per-run or per-event state --
    the same :class:`CompiledExpr` can be reused, from any number of
    threads, across every event in a run and across runs. Existence of one
    is the proof that :func:`compile_expr` accepted it.
    """

    source: str
    code: CodeType


def preprocess_hep_expr(expr: str) -> str:
    """Translate HEP-style boolean operators to Python syntax.

    Carried over verbatim from ``engine/path_filter.py``. One deliberate
    deviation from the reference: the reference applies this only to
    *selection* expressions, so ``&&`` in an *observable* is a
    ``SyntaxError`` there today. Here it is applied to every expression
    :func:`compile_expr` sees, selection or observable alike -- students are
    taught one syntax, and there is no reason an observable should reject
    the spelling a selection accepts.
    """
    expr = re.sub(r'&&', ' and ', expr)
    expr = re.sub(r'\|\|', ' or ', expr)
    # Replace ! only when not followed by = (to preserve !=)
    expr = re.sub(r'!(?!=)', 'not ', expr)
    return expr


def _describe(node: ast.AST) -> str:
    return type(node).__name__


def _validate(tree: ast.AST) -> None:
    """Walk the whole tree once and raise on the first disallowed thing.

    Node-type membership is checked for every node, unconditionally --
    default deny. Names, attribute names, and call targets get an extra,
    more specific check once their node type has already been accepted.
    """
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        raise UnsafeExpression(
            f"That expression is too complex ({len(nodes)} parts, the limit is "
            f"{MAX_AST_NODES}). Try splitting it into more than one cut."
        )

    for node in nodes:
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise UnsafeExpression(
                f"'{_describe(node)}' is not allowed in an expression here. "
                "Use comparisons, arithmetic, 'and'/'or'/'not', and "
                "object.attribute access, e.g. l1.pt > 20 and l2.pt > 10."
            )

        if isinstance(node, ast.Name):
            if node.id not in ALLOWED_NAMES:
                raise UnsafeExpression(
                    f"Unknown name '{node.id}'. Available objects: "
                    + ", ".join(sorted(EVENT_NAMES)) + "."
                )

        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise UnsafeExpression(
                    f"Cannot use '.{node.attr}' -- names starting with '_' are "
                    "never allowed here."
                )
            if node.attr not in ALLOWED_ATTRS:
                raise UnsafeExpression(
                    f"Unknown attribute '.{node.attr}'. Available: "
                    + ", ".join(sorted(ALLOWED_ATTRS)) + "."
                )

        elif isinstance(node, ast.Call):
            if node.keywords:
                raise UnsafeExpression(
                    "Keyword arguments are not allowed in a function call here."
                )
            func = node.func
            if isinstance(func, ast.Name):
                if func.id not in CALLABLE_NAMES:
                    raise UnsafeExpression(
                        f"Cannot call '{func.id}'. Callable functions: "
                        + ", ".join(sorted(CALLABLE_NAMES)) + "."
                    )
            elif isinstance(func, ast.Attribute):
                if func.attr not in ALLOWED_ATTRS:
                    raise UnsafeExpression(f"Cannot call '.{func.attr}'.")
            else:
                raise UnsafeExpression(
                    "Only calling a named function or a method by name is allowed."
                )

        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float, bool, type(None))):
                raise UnsafeExpression(
                    "Only numbers, True, False, and None are allowed as literals "
                    "-- no text."
                )


def compile_expr(source: str) -> CompiledExpr:
    """Validate `source` against the whitelist and compile it.

    Raises :class:`UnsafeExpression` for anything outside the whitelist --
    a bad node type, an unknown name, an underscore-prefixed attribute, a
    call to something not on the safe-function list, an expression over
    either size cap, or a plain :class:`SyntaxError` from :func:`ast.parse`.
    Every rejection happens here, at compile time; nothing is deferred to
    :func:`evaluate`.
    """
    if not isinstance(source, str):
        raise UnsafeExpression("An expression must be text.")
    if len(source) > MAX_EXPR_LENGTH:
        raise UnsafeExpression(
            f"That expression is too long ({len(source)} characters, the limit "
            f"is {MAX_EXPR_LENGTH})."
        )

    processed = preprocess_hep_expr(source)

    try:
        tree = ast.parse(processed, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpression(f"Could not read that expression: {exc.msg}.") from exc

    _validate(tree)

    code = compile(tree, "<student-expression>", "eval")
    return CompiledExpr(source=source, code=code)


def evaluate(compiled: CompiledExpr, names: Mapping[str, Any]) -> Any:
    """Run an already-validated expression against a per-event names mapping.

    `names` supplies the event objects (`l1`, `l2`, ... `met`) and the two
    helper functions (`deltaR`, `mT`); `compiled` was already proven safe by
    :func:`compile_expr`, so this cannot raise :class:`UnsafeExpression`. It
    can still raise ordinary runtime errors (e.g. `NameError` if `names` is
    missing something the expression uses, `ZeroDivisionError`, ...) -- the
    caller is expected to handle those exactly as it already handles any
    other per-event failure.

    `names` is copied into a fresh `dict` before use so `evaluate` can never
    mutate the caller's mapping, even though nothing in the whitelisted
    language can assign to a name.
    """
    return eval(compiled.code, {"__builtins__": SAFE_BUILTINS}, dict(names))
