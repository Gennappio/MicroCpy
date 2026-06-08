"""
PhysiBoSS / PhysiCell adapter — registers the codegen-only node functions.

This adapter drives PhysiCell/PhysiBoSS as a black box: workflows declaring
``kernel: physicell`` carry substrate / cell-type / Hill-rule definitions as
codegen-only nodes (``define_substrate`` / ``define_cell_type`` /
``define_hill_rule`` / ``run_physicell_simulation`` / ``select_project_template``
/ ``summarize_physicell_events``). At run time the engine's executor hands the
workflow to ``opencellcomms_adapters.PhysiBoSS.backend.physicell_backend.run``,
which generates a PhysiCell project tree (via ``.codegen``), compiles it against
an unmodified ``PhysiBoSS-master/`` tree, and streams observability events back.

Importing this module registers all node functions via ``@register_function``
and the ``physicell`` facade kernel (with its dispatch backend) via
``register_kernel``. The engine itself knows nothing about PhysiCell — it only
dispatches generically to whatever kernel declares a ``backend`` hook.
"""
from typing import Any, Dict

from src.workflow.kernel_registry import KernelDefinition, register_kernel

# Importing the package triggers registration of all node functions
# (see functions/__init__.py).
import opencellcomms_adapters.PhysiBoSS.functions  # noqa: F401


def _initialize_physicell(context: Dict[str, Any], params: Dict[str, Any]) -> bool:
    context['kernel_type'] = 'physicell'
    print("[KERNEL] PhysiCell facade kernel selected — simulation will run via codegen + native binary")
    return True


def _run_physicell_backend(workflow: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch hook for ``kernel: physicell`` workflows.

    Imports the backend lazily so the codegen / jinja2 machinery is only pulled
    in when a PhysiCell workflow actually runs — not on every registry build.
    """
    from opencellcomms_adapters.PhysiBoSS.backend import physicell_backend
    return physicell_backend.run(workflow, context)


register_kernel(KernelDefinition(
    name="physicell",
    description=(
        "PhysiCell / PhysiBoSS black-box facade. Workflow nodes describe a "
        "domain spec (substrates, cell types, Hill rules); the adapter "
        "generates a project, builds it against unmodified PhysiBoSS-master, "
        "and runs the native binary while streaming occ_events.jsonl."
    ),
    core_keys={},
    required_interfaces={},
    initializer=_initialize_physicell,
    backend=_run_physicell_backend,
    compatible_categories=["INITIALIZATION"],
    kernel_id="physicell",
    version="1.0",
))
