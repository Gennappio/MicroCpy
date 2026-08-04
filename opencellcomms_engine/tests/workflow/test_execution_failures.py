import json
from pathlib import Path

import pytest

from src.workflow.executor import WorkflowExecutionError, WorkflowExecutor
from src.workflow.schema import (
    SubWorkflow,
    WorkflowDefinition,
    WorkflowFunction,
    WorkflowStage,
)


def _workflow(function: WorkflowFunction) -> WorkflowDefinition:
    return WorkflowDefinition(
        version="2.0",
        name="failure-test",
        subworkflows={
            "main": SubWorkflow(
                name="main",
                deletable=False,
                functions=[function],
                execution_order=[function.id],
            )
        },
    )


def test_registered_finalizer_wins_over_legacy_fallback():
    executor = WorkflowExecutor(WorkflowDefinition(), observability_enabled=False)

    implementation = executor._get_function_implementation("export_final_state")

    assert implementation is not None
    assert implementation.__module__ == (
        "src.workflow.functions.finalization.export_final_state"
    )


def test_failing_node_records_error_event_and_raises(tmp_path: Path):
    function_file = tmp_path / "broken_function.py"
    function_file.write_text(
        "def explode(context, **kwargs):\n"
        "    raise ValueError('deliberate failure')\n",
        encoding="utf-8",
    )
    node = WorkflowFunction(
        id="explode-node",
        function_name="explode",
        function_file=str(function_file),
    )
    executor = WorkflowExecutor(
        _workflow(node),
        observability_enabled=True,
        results_dir=tmp_path / "results",
    )

    with pytest.raises(WorkflowExecutionError) as exc_info:
        executor.execute_main({})

    error = exc_info.value
    assert error.node_id == "explode-node"
    assert error.function_name == "explode"
    assert error.subworkflow_name == "main"
    events_file = tmp_path / "results" / "observability" / "events.jsonl"
    events = [json.loads(line) for line in events_file.read_text().splitlines()]
    failed = [event for event in events if event["event"] == "node_end"]
    assert failed[-1]["payload"]["status"] == "error"
    assert "deliberate failure" in failed[-1]["payload"]["errorMessage"]
    run_meta = json.loads(
        (tmp_path / "results" / "observability" / "run_meta.json").read_text()
    )
    assert run_meta["status"] == "failed"


def test_ordinary_return_value_is_kept_as_result(tmp_path: Path):
    function_file = tmp_path / "return_function.py"
    function_file.write_text(
        "def answer(context, **kwargs):\n"
        "    return 42\n",
        encoding="utf-8",
    )
    node = WorkflowFunction(
        id="answer-node",
        function_name="answer",
        function_file=str(function_file),
    )

    result = WorkflowExecutor(
        _workflow(node), observability_enabled=False
    ).execute_main({})

    assert result["result"] == 42


def test_missing_function_is_fatal():
    node = WorkflowFunction(id="missing-node", function_name="not_registered_anywhere")
    executor = WorkflowExecutor(_workflow(node), observability_enabled=False)

    with pytest.raises(WorkflowExecutionError) as exc_info:
        executor.execute_main({})

    assert exc_info.value.node_id == "missing-node"


def test_invalid_typed_argument_is_fatal_and_identifies_node():
    node = WorkflowFunction(
        id="invalid-argument-node",
        function_name="configure_time_and_steps",
        parameters={"dt": "not-a-number"},
    )
    executor = WorkflowExecutor(_workflow(node), observability_enabled=False)

    with pytest.raises(WorkflowExecutionError) as exc_info:
        executor.execute_main({})

    assert exc_info.value.node_id == "invalid-argument-node"
    assert exc_info.value.function_name == "configure_time_and_steps"
    assert "Invalid value" in str(exc_info.value)


def test_legacy_macrostep_propagates_node_failure(tmp_path: Path):
    function_file = tmp_path / "broken_macrostep.py"
    function_file.write_text(
        "def explode(context, **kwargs):\n"
        "    raise RuntimeError('macrostep failure')\n",
        encoding="utf-8",
    )
    node = WorkflowFunction(
        id="macrostep-node",
        function_name="explode",
        function_file=str(function_file),
    )
    workflow = WorkflowDefinition(
        version="1.0",
        name="legacy-failure-test",
        stages={
            "macrostep": WorkflowStage(
                functions=[node],
                execution_order=[node.id],
            )
        },
    )
    executor = WorkflowExecutor(workflow, observability_enabled=False)

    with pytest.raises(WorkflowExecutionError) as exc_info:
        executor.execute_macrostep({})

    assert exc_info.value.node_id == "macrostep-node"
    assert exc_info.value.subworkflow_name == "macrostep"
