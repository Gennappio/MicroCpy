import json
from pathlib import Path

from src.workflow.executor import WorkflowExecutor
from src.workflow.observability.context_snapshot import ContextSnapshotManager
from src.workflow.observability.event_emitter import NodeEventEmitter
from src.workflow.schema import WorkflowDefinition


def test_executor_default_observability_path_is_independent_of_cwd(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    executor = WorkflowExecutor(
        WorkflowDefinition(),
        observability_enabled=False,
    )

    assert executor._results_dir == (Path(__file__).resolve().parents[2] / "results")


def test_context_snapshots_keep_only_rolling_history(tmp_path: Path):
    manager = ContextSnapshotManager(
        tmp_path,
        max_snapshots_per_scope=3,
    )
    manager.initialize()

    for value in range(6):
        manager.take_snapshot("subworkflow:step", {"value": value})

    scope_dir = tmp_path / "observability" / "context" / "subworkflow_step"
    assert [path.name for path in sorted(scope_dir.glob("v*.json"))] == [
        "v000004.json",
        "v000005.json",
        "v000006.json",
    ]
    assert [path.name for path in sorted((scope_dir / "diff").glob("*.json"))] == [
        "v000004_to_v000005.json",
        "v000005_to_v000006.json",
    ]
    latest = json.loads((scope_dir / "v000006.json").read_text())
    assert latest["keys"]["value"]["preview"] == 5


def test_event_stream_compacts_to_recent_complete_json_lines(tmp_path: Path):
    emitter = NodeEventEmitter(
        tmp_path,
        max_event_bytes=1200,
        retained_event_bytes=600,
        size_check_interval=1,
    )
    emitter.initialize()

    for index in range(40):
        emitter.emit_log(f"event-{index}-" + "x" * 80)

    events_file = tmp_path / "observability" / "events.jsonl"
    events = [json.loads(line) for line in events_file.read_text().splitlines()]

    assert events_file.stat().st_size <= 1200
    assert len(events) < 40
    assert events[-1]["payload"]["message"].startswith("event-39-")
