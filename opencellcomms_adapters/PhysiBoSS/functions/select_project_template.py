"""Select a PhysiBoSS sample-project custom_modules/ as the C++ base.

When this node is present in the CustomModules composer, the scaffold copies
the chosen project's custom.cpp and custom.h verbatim (instead of rendering
the generic stub template) and injects a thin ``occ_glue.cpp`` that wraps
the project's ``phenotype_function`` with OCC observability.

Leave ``project_name`` empty to use the default stub (rules-only behaviour).

Writes ``context['physicell_spec']['custom_modules_source']``.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from src.workflow.decorators import register_function


def _discover_physiboss_root() -> Path | None:
    explicit = os.environ.get("PHYSIBOSS_ROOT")
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if (p / "core").is_dir():
            return p
        return None
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "PhysiBoSS-master"
        if (candidate / "core").is_dir():
            return candidate
    return None


@register_function(
    typed_env_exempt=True,
    display_name="Select Project Template",
    description=(
        "Choose which PhysiBoSS sample_project's custom_modules/ backs the "
        "C++ simulation. The project's custom.cpp (create_cell_types, "
        "setup_tissue, phenotype_function, …) is copied verbatim into the "
        "generated project and wrapped by the OCC observability glue. "
        "Hill rules from define_hill_rule nodes still layer on top via "
        "cell_rules.csv. Leave project_name empty to use the default stub."
    ),
    category="INITIALIZATION",
    parameters=[
        {
            "name": "project_name",
            "type": "STRING",
            "description": (
                "Name of a PhysiBoSS sample_projects/ subdirectory, e.g. "
                "'heterogeneity', 'rules_sample', 'immune_function'. "
                "Empty = use the generic stub template."
            ),
            "default": "",
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics", "physicell"],
)
def select_project_template(
    context: Dict[str, Any] = None,
    project_name: str = "",
    **kwargs,
) -> bool:
    if context is None:
        print("[ERROR] [select_project_template] no context")
        return False

    if not project_name or not project_name.strip():
        print("[TEMPLATE] No project_name set — using default stub template")
        return True

    physiboss_root = _discover_physiboss_root()
    if physiboss_root is None:
        print(
            "[ERROR] [select_project_template] Cannot locate PhysiBoSS-master/. "
            "Set the PHYSIBOSS_ROOT environment variable."
        )
        return False

    sample_projects = physiboss_root / "sample_projects"
    custom_modules_dir = sample_projects / project_name.strip() / "custom_modules"

    if not custom_modules_dir.is_dir():
        available = sorted(p.name for p in sample_projects.iterdir() if p.is_dir())
        print(
            f"[ERROR] [select_project_template] Project '{project_name}' not found "
            f"under {sample_projects}."
        )
        print(f"  Available: {', '.join(available)}")
        return False

    if "physicell_spec" not in context:
        context["physicell_spec"] = {}

    context["physicell_spec"]["custom_modules_source"] = {
        "type": "sample_project",
        "project_name": project_name.strip(),
        "source_dir": str(custom_modules_dir),
    }
    print(f"[TEMPLATE] '{project_name}' custom modules: {custom_modules_dir}")
    return True
