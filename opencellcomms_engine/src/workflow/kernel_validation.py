"""
Capability validation between a workflow's kernel and its functions.

Each function declares the capability tokens it ``requires``; the active kernel
declares what it ``provides()``. A workflow is only runnable when every enabled
function's requirements are a subset of what the kernel provides. This check
runs once, before execution, so incompatibilities fail loudly up front instead
of deep inside a per-step loop.
"""

from typing import List, TYPE_CHECKING

from src.workflow.kernel_registry import get_kernel, list_kernels

if TYPE_CHECKING:
    from src.workflow.schema import WorkflowDefinition, WorkflowFunction
    from src.workflow.registry import FunctionRegistry


def _enabled_functions(workflow: "WorkflowDefinition") -> List["WorkflowFunction"]:
    """All enabled function nodes across legacy stages (v1.0) and subworkflows (v2.0)."""
    funcs: List["WorkflowFunction"] = []
    for stage in (workflow.stages or {}).values():
        funcs.extend(f for f in stage.functions if f.enabled)
    for sub in (workflow.subworkflows or {}).values():
        funcs.extend(f for f in sub.functions if f.enabled)
    return funcs


def validate_kernel_compatibility(
    workflow: "WorkflowDefinition",
    registry: "FunctionRegistry",
) -> List[str]:
    """Return human-readable violation messages (empty list = compatible).

    A violation is recorded when the workflow's kernel is unknown, or when an
    enabled function requires capability tokens the kernel does not provide. All
    offenders are collected so the caller can report everything wrong at once.
    """
    violations: List[str] = []

    kernel = get_kernel(workflow.kernel)
    if kernel is None:
        violations.append(
            f"Workflow kernel '{workflow.kernel}' is not registered. "
            f"Available kernels: {sorted(list_kernels())}."
        )
        return violations

    provided = kernel.provides()

    for func in _enabled_functions(workflow):
        metadata = registry.get(func.function_name)
        if metadata is None:
            # Unknown function names are reported by the existing workflow
            # validator; capability checking has nothing to compare against.
            continue
        needed = set(metadata.requires or [])
        missing = needed - provided
        if missing:
            label = func.custom_name or func.function_name
            violations.append(
                f"Function '{label}' requires {sorted(missing)} which kernel "
                f"'{kernel.kernel_id}' (v{kernel.version}) does not provide. "
                f"Kernel provides: {sorted(provided) or '(nothing)'}."
            )

    return violations
