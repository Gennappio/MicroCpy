from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from src.config.config import OpenCellCommsConfig, OutputConfig
from src.core.units import Length
from src.io.initial_state import InitialStateManager
from src.io.vtk_domain_loader import VTKDomainLoader
from src.workflow.functions.initialization.setup_output import setup_output
from src.workflow.functions.finalization.save_checkpoint import save_checkpoint_vtk
from src.workflow.registry import discover_adapter_names


CONFIG_DIR = Path(__file__).resolve().parents[2] / "src" / "config"
BUNDLED_CONFIGS = (
    "complete_substances_config.yaml",
    "drug_treatment_study.yaml",
    "gradient_test_config_working.yaml",
    "gradient_test_simple.yaml",
    "high_res_complete_substances.yaml",
    "high_res_oxygen_glucose.yaml",
    "simple_oxygen_glucose.yaml",
)


def test_setup_output_updates_engine_consumed_values():
    config = SimpleNamespace(output=OutputConfig())

    assert setup_output(
        {"config": config},
        save_data_interval=3,
        save_plots_interval=5,
        save_final_plots=False,
        save_initial_plots=False,
        status_print_interval=7,
        save_cellstate_interval=11,
    )

    assert config.output.save_data_interval == 3
    assert config.output.save_plots_interval == 5
    assert config.output.save_final_plots is False
    assert config.output.save_initial_plots is False
    assert config.output.status_print_interval == 7
    assert config.output.save_cellstate_interval == 11


@pytest.mark.parametrize("field", ["save_data_interval", "save_plots_interval", "status_print_interval"])
def test_setup_output_rejects_nonpositive_active_intervals(field):
    config = SimpleNamespace(output=OutputConfig())
    arguments = {field: 0}

    with pytest.raises(ValueError, match=field):
        setup_output({"config": config}, **arguments)


def test_vtk_checkpoint_round_trip(tmp_path: Path):
    path = tmp_path / "checkpoint.vtk"
    writer = VTKDomainLoader()
    writer.save_complete_domain(
        str(path),
        positions=[(1, 2, 3), (-4, 0, 2)],
        gene_states=[{"A": True, "B": False}, {"A": False, "B": True}],
        phenotypes=["PROLIFERATING", "APOPTOTIC"],
        metabolism=[0.25, 1.5],
        gene_nodes=["A", "B"],
        metadata={
            "biocell_grid_size_um": 20.0,
            "ages": [2.5, 8.0],
            "generations": [1, 4],
        },
    )

    loaded = VTKDomainLoader().load_complete_domain(str(path))

    np.testing.assert_allclose(loaded["positions"], [[1, 2, 3], [-4, 0, 2]])
    assert loaded["gene_states"] == {
        0: {"A": True, "B": False},
        1: {"A": False, "B": True},
    }
    assert loaded["phenotypes"] == ["PROLIFERATING", "APOPTOTIC"]
    assert loaded["metabolism"] == [0.25, 1.5]
    assert loaded["ages"] == [2.5, 8.0]
    assert loaded["generations"] == [1, 4]

    config = SimpleNamespace(
        domain=SimpleNamespace(
            cell_height=Length(20, "um"),
            size_x=Length(400, "um"),
            size_y=Length(400, "um"),
            size_z=None,
            dimensions=2,
        )
    )
    cells, cell_size = InitialStateManager(config).load_initial_state_from_vtk(path)
    assert cell_size == 20.0
    assert cells[0]["position"] == (1, 2)
    assert cells[0]["phenotype"] == "PROLIFERATING"
    assert cells[0]["age"] == 2.5
    assert cells[0]["division_count"] == 1
    assert cells[0]["gene_states"] == {"A": True, "B": False}
    assert cells[0]["metabolic_state"] == {"value": 0.25}


def test_checkpoint_writer_reads_population_and_cell_state(tmp_path: Path):
    cell_state = SimpleNamespace(
        id="cell-1",
        position=(3, 4),
        phenotype="QUIESCENT",
        age=6.5,
        division_count=2,
        metabolic_state={"value": 0.75},
    )
    population = SimpleNamespace(
        state=SimpleNamespace(cells={"cell-1": SimpleNamespace(state=cell_state)})
    )
    config = SimpleNamespace(
        domain=SimpleNamespace(
            cell_height=Length(20, "um"),
            dimensions=2,
        )
    )
    target = tmp_path / "from_population.vtk"

    assert save_checkpoint_vtk(
        {"population": population, "config": config},
        file_path=str(target),
        include_gene_states=False,
    )

    loaded = VTKDomainLoader().load_complete_domain(str(target))
    np.testing.assert_allclose(loaded["positions"], [[3, 4, 0]])
    assert loaded["phenotypes"] == ["QUIESCENT"]
    assert loaded["ages"] == [6.5]
    assert loaded["generations"] == [2]


@pytest.mark.parametrize("filename", BUNDLED_CONFIGS)
def test_bundled_config_paths_load_from_any_working_directory(filename, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    config = OpenCellCommsConfig.load_from_yaml(CONFIG_DIR / filename)

    assert Path(config.custom_functions_path).is_file()


def _plugin(root: Path, name: str, manifest: str | None) -> None:
    directory = root / name
    directory.mkdir()
    (directory / "register.py").write_text("", encoding="utf-8")
    if manifest is not None:
        (directory / "plugin.toml").write_text(manifest, encoding="utf-8")


def test_only_enabled_compatible_manifested_plugins_are_discovered(tmp_path: Path):
    _plugin(
        tmp_path,
        "valid_plugin",
        '[plugin]\nname="valid_plugin"\nversion="1.0"\nengine_version=">=2,<3"\n',
    )
    _plugin(tmp_path, "no_manifest", None)
    _plugin(
        tmp_path,
        "disabled_plugin",
        '[plugin]\nname="disabled_plugin"\nversion="1.0"\nenabled=false\n',
    )
    _plugin(
        tmp_path,
        "incompatible_plugin",
        '[plugin]\nname="incompatible_plugin"\nversion="1.0"\nengine_version=">=99"\n',
    )
    _plugin(tmp_path, "malformed_plugin", "this is not toml =")
    _plugin(
        tmp_path,
        "unversioned_engine",
        '[plugin]\nname="unversioned_engine"\nversion="1.0"\n',
    )

    assert discover_adapter_names(tmp_path) == ["valid_plugin"]
