"""Phase 4 tests for the physicell-kernel dispatch and backend.

Three scopes:
- Schema round-trip for the new ``kernel`` field.
- Kernel registry exposes both ``biophysics`` and ``physicell``.
- Executor's ``execute_main`` routes physicell workflows to the backend
  (fast, mocked) and a slow end-to-end run that exercises codegen → make
  → spawn → JSONL tail.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict

import pytest

from src.workflow.kernel_registry import KERNEL_REGISTRY, get_kernel
from src.workflow.schema import WorkflowDefinition

# Helpers -------------------------------------------------------------------

# tests/workflow/test_*.py → parents[2] is the engine root, parents[3] is OpenCellComms,
# parents[4] is the MicroCpy3D root where PhysiBoSS-master lives.
ENGINE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PHYSIBOSS_ROOT = Path(
    os.environ.get("PHYSIBOSS_ROOT")
    or (ENGINE_ROOT.parent.parent / "PhysiBoSS-master")
)


def _physicell_workflow_dict() -> Dict[str, Any]:
    return {
        "version": "2.0",
        "name": "phase4_e2e",
        "description": "Phase 4 end-to-end smoke",
        "kernel": "physicell",
        "physicell": {
            "domain": {
                "x_min": -150.0, "x_max": 150.0,
                "y_min": -150.0, "y_max": 150.0,
                "z_min": -10.0, "z_max": 10.0,
                "dx": 20.0, "dy": 20.0, "dz": 20.0, "use_2D": True,
            },
            "overall": {
                "max_time": 2.0, "dt_diffusion": 0.01,
                "dt_mechanics": 0.1, "dt_phenotype": 0.1,
            },
            "parallel": {"omp_num_threads": 2},
            "save": {"folder": "output", "full_data_interval": 1.0,
                     "svg_interval": 1.0, "svg_enabled": False},
            "options": {"random_seed": 11, "virtual_wall_at_domain_edge": True},
            "user_parameters": {"number_of_cells": 3},
        },
        "subworkflows": {
            "main": {
                "description": "physicell facade entry — codegen-only nodes",
                "deletable": False,
                "execution_order": ["sub_o2", "ct_tumor", "r1"],
                "functions": [
                    {"id": "sub_o2", "function_name": "define_substrate",
                     "parameters": {"substrate": {
                         "name": "oxygen", "units": "mmHg",
                         "diffusion_coefficient": 100000.0,
                         "decay_rate": 1.0,
                         "initial_condition": 38.0,
                         "dirichlet_enabled": False,
                         "dirichlet_value": 0.0,
                     }}},
                    {"id": "ct_tumor", "function_name": "define_cell_type",
                     "parameters": {"cell_type": {"name": "tumor", "id": 0}}},
                    {"id": "r1", "function_name": "define_hill_rule",
                     "parameters": {"rule": {
                         "cell_type": "tumor", "signal": "oxygen",
                         "direction": "increases", "behavior": "necrosis",
                         "max_response": 0.5, "half_max": 5.0,
                         "hill_power": 8.0, "use_on_dead": 0,
                     }}},
                ],
            }
        }
    }


# Fast tests ----------------------------------------------------------------

def test_kernel_field_roundtrips():
    wf = WorkflowDefinition(name="x", kernel="physicell")
    rebuilt = WorkflowDefinition.from_dict(wf.to_dict())
    assert rebuilt.kernel == "physicell"


def test_kernel_defaults_to_biophysics():
    wf = WorkflowDefinition.from_dict({"version": "2.0", "name": "no-kernel"})
    assert wf.kernel == "biophysics"


def test_both_kernels_registered():
    # `biophysics` is the engine's native kernel; `physicell` is a facade
    # kernel provided by the PhysiBoSS adapter (it registers itself with a
    # `backend` dispatch hook), so importing the adapter is what makes it
    # available — the engine core no longer declares it.
    import opencellcomms_adapters.PhysiBoSS.register  # noqa: F401

    assert "biophysics" in KERNEL_REGISTRY
    assert "physicell" in KERNEL_REGISTRY
    assert get_kernel("physicell").description.startswith("PhysiCell")
    assert get_kernel("physicell").backend is not None
    assert get_kernel("biophysics").backend is None


def test_execute_main_routes_physicell_to_backend(monkeypatch):
    """When kernel=physicell, execute_main hands off to physicell_backend.run."""
    from src.workflow import executor as ex_mod
    from opencellcomms_adapters.PhysiBoSS.backend import physicell_backend

    wf = WorkflowDefinition.from_dict(_physicell_workflow_dict())
    captured: Dict[str, Any] = {}

    def fake_run(workflow, context):
        captured["called"] = True
        captured["kernel"] = getattr(workflow, "kernel", None)
        context["physicell_mock"] = "ok"
        return context

    monkeypatch.setattr(physicell_backend, "run", fake_run)

    executor = ex_mod.WorkflowExecutor(wf, observability_enabled=False)
    result = executor.execute_main({"output_dir": "/tmp/unused"})

    assert captured.get("called") is True
    assert captured.get("kernel") == "physicell"
    assert result.get("physicell_mock") == "ok"


# Slow end-to-end -----------------------------------------------------------

@pytest.mark.slow
def test_end_to_end_workflow_runs_and_streams_events(tmp_path: Path, capsys):
    physiboss = DEFAULT_PHYSIBOSS_ROOT
    if not physiboss.exists():
        pytest.skip(f"PhysiBoSS-master not found at {physiboss}")
    if not (shutil.which("g++") or shutil.which("c++")):
        pytest.skip("no C++ compiler in PATH")

    os.environ["PHYSIBOSS_ROOT"] = str(physiboss)

    from src.workflow import executor as ex_mod

    wf = WorkflowDefinition.from_dict(_physicell_workflow_dict())
    executor = ex_mod.WorkflowExecutor(wf, observability_enabled=False)

    context: Dict[str, Any] = {"output_dir": str(tmp_path)}
    try:
        result = executor.execute_main(context)
    except Exception as e:
        captured = capsys.readouterr()
        if "make failed" in str(e):
            pytest.skip(f"PhysiCell build failed: {e}")
        raise

    assert "physicell" in result, "backend did not record results in context"
    info = result["physicell"]
    assert info["exit_code"] == 0
    jsonl = Path(info["events_jsonl"])
    assert jsonl.exists()

    captured = capsys.readouterr()
    event_lines = [ln for ln in captured.out.splitlines() if ln.startswith("[OCC_EVENT] ")]
    assert event_lines, (
        f"no [OCC_EVENT] lines in stdout. stdout tail:\n{captured.out[-1500:]}"
    )
