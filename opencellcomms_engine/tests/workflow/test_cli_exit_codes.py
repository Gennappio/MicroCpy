import pytest

import run_workflow
from tools import run_sim


def test_master_runner_rejects_combined_simulation_modes():
    with pytest.raises(SystemExit) as exc_info:
        run_workflow.main(["--sim", "config.yaml", "--workflow", "workflow.json"])

    assert exc_info.value.code == 2


def test_generic_runner_rejects_combined_simulation_modes():
    with pytest.raises(SystemExit) as exc_info:
        run_sim.parse_arguments(["--sim", "config.yaml", "--workflow", "workflow.json"])

    assert exc_info.value.code == 2


def test_master_runner_returns_nonzero_when_child_fails(monkeypatch):
    monkeypatch.setattr(run_workflow, "run_tool", lambda *args, **kwargs: False)

    assert run_workflow.main(["--workflow", "broken.json"]) == 1
