"""Inject custom PhysiCell C++ behaviour into the generated custom.cpp.

PhysiCell defines cell behaviour two ways: declaratively via cell_rules.csv
(our ``define_hill_rule`` node) and imperatively via C++ custom functions in
``custom_modules/custom.cpp``. This node is the imperative path: it lets you
write the bodies of PhysiCell's custom hooks directly, instead of copying a
whole sample project verbatim (``select_project_template``).

The ``code`` DICT maps hook name -> C++ snippet. Supported hooks:

- ``globals``         — file-scope C++ injected after the includes (helpers,
                        static state, extra #includes).
- ``setup_tissue``    — appended at the end of setup_tissue(), after the
                        default cell placement (custom initial conditions).
- ``custom_function`` — body of custom_function(), wired to each cell's
                        custom_cell_rule (runs every mechanics tick, per cell).
                        Vars in scope: ``pCell``, ``phenotype``, ``dt``.
- ``contact_function``— body of contact_function() (pairwise cell contact).
                        Vars in scope: ``pMe``, ``phenoMe``, ``pOther``,
                        ``phenoOther``, ``dt``.

Writes ``context['physicell_spec']['custom_code']``. Only effective in stub
mode — if a ``select_project_template`` node is also present, the template's
custom.cpp is copied verbatim and this code is ignored (the build warns).
"""
from __future__ import annotations

from typing import Any, Dict

from src.workflow.decorators import register_function

_SUPPORTED_HOOKS = ("globals", "setup_tissue", "custom_function", "contact_function")


def _ensure_spec(context: Dict[str, Any]) -> Dict[str, Any]:
    spec = context.setdefault("physicell_spec", {})
    spec.setdefault("substrates", [])
    spec.setdefault("cell_types", [])
    spec.setdefault("hill_rules", [])
    return spec


@register_function(
    typed_env_exempt=True,
    display_name="Define Custom Code (PhysiCell)",
    description=(
        "Write custom C++ for PhysiCell's custom functions (the imperative "
        "alternative to Hill rules). The 'code' dict maps hook name to a C++ "
        "snippet; supported hooks: globals, setup_tissue, custom_function, "
        "contact_function. Injected into the generated custom.cpp. Ignored if "
        "a select_project_template node is present (template wins)."
    ),
    category="INITIALIZATION",
    parameters=[
        {
            "name": "code",
            "type": "DICT",
            "description": (
                "Hook -> C++ snippet. Keys: globals, setup_tissue, "
                "custom_function (pCell/phenotype/dt in scope), "
                "contact_function (pMe/phenoMe/pOther/phenoOther/dt in scope)."
            ),
            "default": {
                "globals": "",
                "setup_tissue": "",
                "custom_function": "",
                "contact_function": "",
            },
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics", "physicell"],
)
def define_custom_code(
    context: Dict[str, Any] = None,
    code: Dict[str, Any] = None,
    **kwargs,
) -> bool:
    if context is None:
        print("[ERROR] [define_custom_code] no context")
        return False
    if not code:
        print("[CUSTOMCODE] no code given — nothing injected")
        return True

    unknown = [k for k in code if k not in _SUPPORTED_HOOKS]
    if unknown:
        print(f"[WARN] [define_custom_code] ignoring unknown hooks {unknown}; "
              f"supported: {list(_SUPPORTED_HOOKS)}")

    # Keep only non-empty, supported hooks.
    custom_code = {
        k: v for k, v in code.items()
        if k in _SUPPORTED_HOOKS and isinstance(v, str) and v.strip()
    }

    spec = _ensure_spec(context)
    spec["custom_code"] = custom_code
    print(f"[CUSTOMCODE] hooks set: {', '.join(custom_code) or '(none)'}")
    return True


__all__ = ["define_custom_code"]
