"""
Guard: every typed-env function's parameters are GUI-visible.

A typed-env function (first arg ``env``) reaches the simulation context via
``env.x``, so every OTHER signature argument is a USER parameter and MUST be
declared in ``@register_function(parameters=[...])`` (or given a default).
Otherwise it is silently dropped at registration and the node has no editable
socket in the GUI — a "bad node" whose parameter can be neither shown nor wired.
This test fails if any typed-env function in the engine or the adapters violates
that, so such code cannot be merged. It is the merge-time half of the
registration check in ``decorators.py`` (``OCC_ENFORCE_PARAM_DECLARATIONS``).

Pure AST analysis: it imports nothing from the engine, so it runs without the
engine's heavy dependencies and with no import side effects.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = [
    REPO_ROOT / "opencellcomms_engine" / "src" / "workflow" / "functions",
    REPO_ROOT / "opencellcomms_adapters",
]


def _function_files():
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            if "__pycache__" in f.parts or f.name == "__init__.py":
                continue
            yield f


def _undeclared_params(tree):
    """Yield (func_name, param_name) for typed-env funcs with an undeclared,
    non-default argument."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        decos = [
            d for d in node.decorator_list
            if isinstance(d, ast.Call) and getattr(d.func, "id", None) == "register_function"
        ]
        if not decos:
            continue
        kw = {k.arg: k.value for k in decos[0].keywords}
        declared = set()
        if "parameters" in kw:
            try:
                val = ast.literal_eval(kw["parameters"])
            except (ValueError, SyntaxError):
                continue  # parameters built dynamically — can't statically verify
            declared = {p.get("name") for p in val if isinstance(p, dict)}
        a = node.args
        posargs = a.posonlyargs + a.args
        if not posargs or posargs[0].arg != "env":
            continue  # only the typed-env convention is enforced; legacy is grandfathered
        defaulted = {p.arg for p in posargs[len(posargs) - len(a.defaults):]}
        defaulted |= {p.arg for p, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None}
        for p in posargs[1:] + a.kwonlyargs:
            if p.arg in ("context", "self"):
                continue
            if p.arg not in declared and p.arg not in defaulted:
                yield node.name, p.arg


def test_typed_env_functions_declare_their_parameters():
    offenders = []
    for f in _function_files():
        try:
            tree = ast.parse(f.read_text())
        except SyntaxError:
            continue
        for fn, param in _undeclared_params(tree):
            offenders.append(
                f"{fn} ({f.relative_to(REPO_ROOT)}): undeclared parameter '{param}'"
            )
    assert not offenders, (
        "Typed-env functions with an undeclared parameter (no GUI socket). Add each "
        "to @register_function(parameters=[...]) or give it a default:\n  "
        + "\n  ".join(offenders)
    )
