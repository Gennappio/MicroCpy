"""
FLAME GPU backend runner.

``run(workflow, context)`` is the dispatch hook the engine calls for
``kernel: flamegpu`` workflows. It reads the model parameters, builds a
pyflamegpu Sugarscape model (see ``sugarscape_model.py``), runs it on the GPU,
and returns the context with a population/sugar time series in ``results``.

pyflamegpu is an **optional** dependency: not on PyPI, distributed as prebuilt
CUDA wheels (https://whl.flamegpu.com) for specific CUDA + Python versions, and
it needs a CUDA-capable GPU at run time. If it is missing we raise a clear,
actionable error rather than a bare ImportError.
"""
from typing import Any, Dict


# Defaults mirror the CPU Sugarscape workflow
# (opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json) so the two are
# comparable: 50x50 toroidal grid, 60 steps, 120 foragers, growback rate 1.
_DEFAULTS = {
    "grid_size": 50,
    "steps": 60,
    "n_foragers": 120,
    "growback_rate": 1.0,
    "sugar_peak": 4.0,
    "radius_frac": 0.45,
    "sugar_min": 5.0, "sugar_max": 25.0,
    "metabolism_min": 1.0, "metabolism_max": 4.0,
    "vision_min": 1, "vision_max": 6,
    "seed": 42,
}


def _coerce_to_dict(workflow: Any) -> Dict[str, Any]:
    if isinstance(workflow, dict):
        return workflow
    if hasattr(workflow, "to_dict"):
        return workflow.to_dict()
    return {}


def _params(workflow: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Model params: defaults, overlaid with the workflow's
    ``metadata.flamegpu`` block, overlaid with the run seed."""
    wf = _coerce_to_dict(workflow)
    params = dict(_DEFAULTS)
    params.update((wf.get("metadata") or {}).get("flamegpu") or {})
    if context.get("seed") is not None:
        params["seed"] = int(context["seed"])
    return params


def _require_pyflamegpu():
    try:
        import pyflamegpu  # noqa: F401
        return pyflamegpu
    except ImportError as e:
        import sys
        raise RuntimeError(
            "The 'flamegpu' kernel needs pyflamegpu (FLAME GPU 2), which is not "
            "installed.\n"
            "  - pyflamegpu is NOT on PyPI. Install a prebuilt CUDA wheel from the "
            "FLAME GPU index, matching your CUDA and Python version, e.g.:\n"
            "      pip install pyflamegpu -f https://whl.flamegpu.com/whl/cuda122/\n"
            "  - It requires a CUDA-capable GPU at run time.\n"
            f"  - Current interpreter: Python {sys.version.split()[0]} — FLAME GPU "
            "only ships wheels for supported Python versions (3.14 is likely "
            "unsupported; use a 3.9–3.13 environment).\n"
            f"(original import error: {e})"
        ) from e


def run(workflow: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    params = _params(workflow, context)
    print(f"[FLAMEGPU] Sugarscape params: {params}")

    _require_pyflamegpu()  # raises with guidance if unavailable

    # Imported lazily (pulls in pyflamegpu) only once we know it's present.
    from opencellcomms_adapters.Sugarscape_flame.backend import sugarscape_model

    history = sugarscape_model.run_model(params)

    context.setdefault("results", {})
    context["results"]["flamegpu_population"] = history["population"]
    context["results"]["flamegpu_total_sugar"] = history["total_sugar"]
    print(f"[FLAMEGPU] done: {len(history['population'])} steps, "
          f"final population = {history['population'][-1] if history['population'] else 0}")
    return context
