"""
Sugarscape-flame adapter — registers the ``flamegpu`` facade kernel.

This is the integration seam that proves the engine is not tied to its Python
ABM class layer: a workflow declaring ``kernel: flamegpu`` is handed, whole, to
this adapter's backend, which builds and runs a **pyflamegpu** (FLAME GPU 2)
model on the GPU — bypassing the Python stage executor entirely. It is exactly
the mechanism PhysiCell/PhysiBoSS uses (``KernelDefinition.backend``); the engine
stays agnostic of FLAME GPU.

Importing this module only *registers* the kernel — it must not import
``pyflamegpu`` (heavy, GPU/CUDA-bound, optional). The backend imports it lazily,
so the plugin loads on any machine; only *running* a ``flamegpu`` workflow needs
a CUDA GPU + a pyflamegpu wheel for the active Python.
"""
from typing import Any, Dict

from src.workflow.kernel_registry import KernelDefinition, register_kernel


def _initialize_flamegpu(context: Dict[str, Any], params: Dict[str, Any]) -> bool:
    context["kernel_type"] = "flamegpu"
    print("[KERNEL] FLAME GPU facade kernel selected — simulation will run on the GPU via pyflamegpu")
    return True


def _run_flamegpu_backend(workflow: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch hook for ``kernel: flamegpu`` workflows. Lazily imports the
    backend (and, through it, pyflamegpu) so the CUDA machinery is only pulled in
    when a FLAME GPU workflow actually runs — not on every registry build."""
    from opencellcomms_adapters.Sugarscape_flame.backend import flamegpu_backend
    return flamegpu_backend.run(workflow, context)


register_kernel(KernelDefinition(
    name="flamegpu",
    description=(
        "FLAME GPU 2 black-box facade. A workflow declares grid / population / "
        "growback parameters; the adapter builds a pyflamegpu Sugarscape model "
        "(agent functions + spatial messaging) and runs it on the GPU, returning "
        "population and sugar-field time series."
    ),
    core_keys={},
    required_interfaces={},
    initializer=_initialize_flamegpu,
    backend=_run_flamegpu_backend,
    compatible_categories=["INITIALIZATION"],
    kernel_id="flamegpu",
    version="0.1",
))
