from pathlib import Path

import pytest

from src.workflow.executor import WorkflowExecutor
from src.workflow.loader import WorkflowLoader


REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_WORKFLOWS = (
    REPO_ROOT / "opencellcomms_adapters" / "MicroC" / "workflows" / "microc.json",
    REPO_ROOT
    / "opencellcomms_adapters"
    / "TCELL_CORRAL"
    / "workflows"
    / "tcell_corral.json",
    REPO_ROOT
    / "opencellcomms_adapters"
    / "SUGARSCAPE"
    / "workflows"
    / "sugarscape.json",
)


@pytest.mark.slow
@pytest.mark.parametrize("workflow_path", CANONICAL_WORKFLOWS, ids=lambda path: path.parent.parent.name)
def test_canonical_workflow_one_step_smoke(workflow_path: Path, tmp_path: Path):
    workflow = WorkflowLoader.load(workflow_path)

    for call in workflow.subworkflows["main"].subworkflow_calls:
        if call.subworkflow_name == "__scheduler__":
            call.iterations = 1

    # Keep the smoke bounded and free of plots/checkpoints. The scientific
    # initialization and one scheduler step still run through the real graph.
    for subworkflow in workflow.subworkflows.values():
        for function in subworkflow.functions:
            name = function.function_name.lower()
            if any(token in name for token in ("plot", "save_", "export_", "write_")):
                function.enabled = False

    result = WorkflowExecutor(
        workflow,
        results_dir=tmp_path / "observability",
        gui_results_dir=tmp_path / "run",
        workflow_file=workflow_path,
    ).execute_main({})

    assert isinstance(result, dict)
    assert result.get("population") is not None or result.get("abm_population") is not None
