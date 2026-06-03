"""Tests for kernel <-> function capability validation.

A function declares the capability tokens it `requires`; the active kernel
declares what it `provides()`. A workflow is only runnable when every enabled
function's requirements are satisfied by the kernel, and the executor must fail
loudly otherwise — before any step runs.
"""

import json

import pytest

from src.workflow.schema import WorkflowDefinition, WorkflowFunction
from src.workflow.registry import get_default_registry
from src.workflow.executor import WorkflowExecutor
from src.workflow.kernel_registry import (
    get_kernel,
    list_kernels,
    load_kernel_files,
)
from src.workflow.kernel_validation import validate_kernel_compatibility


def _v1_workflow(kernel: str) -> WorkflowDefinition:
    """A minimal legacy (v1.0) workflow whose diffusion stage runs the solver.

    `run_diffusion_solver` is annotated `requires=["simulator", "population"]`,
    so it is compatible with biophysics but not with physicell (which provides
    nothing).
    """
    wf = WorkflowDefinition(version="1.0", name="capability-test", kernel=kernel)
    wf.stages["diffusion"].functions.append(
        WorkflowFunction(id="d1", function_name="run_diffusion_solver")
    )
    return wf


def test_provides_derived_from_core_keys():
    bio = get_kernel("biophysics")
    assert bio.provides() == {
        "population", "simulator", "gene_network", "mesh_manager", "gene_networks"
    }
    assert get_kernel("physicell").provides() == set()


def test_compatible_workflow_has_no_violations():
    registry = get_default_registry()
    assert validate_kernel_compatibility(_v1_workflow("biophysics"), registry) == []


def test_incompatible_workflow_reports_missing_capability():
    registry = get_default_registry()
    violations = validate_kernel_compatibility(_v1_workflow("physicell"), registry)
    assert len(violations) == 1
    msg = violations[0]
    assert "run_diffusion_solver" in msg
    assert "simulator" in msg and "population" in msg


def test_unknown_kernel_is_a_violation():
    registry = get_default_registry()
    wf = _v1_workflow("does-not-exist")
    violations = validate_kernel_compatibility(wf, registry)
    assert len(violations) == 1
    assert "not registered" in violations[0]


def test_disabled_functions_are_ignored():
    registry = get_default_registry()
    wf = _v1_workflow("physicell")
    wf.stages["diffusion"].functions[0].enabled = False
    assert validate_kernel_compatibility(wf, registry) == []


def test_executor_fails_loudly_on_incompatible_kernel():
    with pytest.raises(ValueError, match="KERNEL COMPATIBILITY"):
        WorkflowExecutor(_v1_workflow("physicell"), custom_functions_module=None, config=None)


def test_executor_constructs_on_compatible_kernel():
    # Should not raise on the kernel check (biophysics provides what the solver needs).
    WorkflowExecutor(_v1_workflow("biophysics"), custom_functions_module=None, config=None)


def test_data_file_kernel_is_loaded_and_provides(tmp_path):
    (tmp_path / "demo_kernel.json").write_text(json.dumps({
        "kernel_id": "demo",
        "name": "demo",
        "description": "data-file kernel for tests",
        "provides": ["population", "substance:oxygen"],
        "compatible_categories": ["INTRACELLULAR"],
    }))

    loaded = load_kernel_files(tmp_path)
    assert loaded == 1
    assert "demo" in list_kernels()
    assert get_kernel("demo").provides() == {"population", "substance:oxygen"}
