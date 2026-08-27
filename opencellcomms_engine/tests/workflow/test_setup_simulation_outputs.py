from pathlib import Path

from src.workflow.functions.initialization.setup_simulation import setup_simulation


def test_setup_simulation_uses_executor_paths_without_creating_results(
    tmp_path: Path,
):
    managed_dir = tmp_path / "runs" / "experiment" / "__world__"
    legacy_dir = tmp_path / "results"
    context = {
        "output_dir": managed_dir,
        "plots_dir": managed_dir,
    }

    assert setup_simulation(context, output_dir=str(legacy_dir))

    assert context["config"].output_dir == managed_dir
    assert context["config"].plots_dir == managed_dir
    assert context["simulation_params"]["output_dir"] == managed_dir
    assert not legacy_dir.exists()
    assert not managed_dir.exists()


def test_setup_simulation_standalone_fallback_is_not_timestamped(tmp_path: Path):
    output_dir = tmp_path / "standalone-output"
    context = {}

    assert setup_simulation(context, output_dir=str(output_dir))

    assert context["config"].output_dir == output_dir
    assert context["config"].plots_dir == output_dir / "plots"
    assert not output_dir.exists()
