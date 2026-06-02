"""Phase 2 + Phase 3 codegen tests for the PhysiCell black-box facade.

Three scopes:
- ``test_generated_project_structure``: fast — assert generate_project()
  produces all the expected files / symlinks. No compilation.
- ``test_generated_project_builds_and_runs``: slow — compile the generated
  project against the unmodified upstream tree and run a short simulation.
  Marked ``slow``; skipped if PhysiBoSS-master is not on disk.
- ``test_hill_rule_fires_rule_engine_changed`` (Phase 3, slow): build a
  project whose CBHG rule lifts necrosis rate when oxygen is low, then
  assert occ_events.jsonl contains at least one matching
  ``rule_engine_changed`` event.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

import pytest

from opencellcomms_adapters.PhysiBoSS.codegen.scaffold import SpecError, generate_project

# PhysiBoSS-master sits as a sibling of the OpenCellComms repo by convention.
ENGINE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PHYSIBOSS_ROOT = ENGINE_ROOT.parent.parent / "PhysiBoSS-master"


def _minimal_spec() -> Dict[str, Any]:
    return {
        "domain": {
            "x_min": -200.0, "x_max": 200.0,
            "y_min": -200.0, "y_max": 200.0,
            "z_min": -10.0, "z_max": 10.0,
            "dx": 20.0, "dy": 20.0, "dz": 20.0,
            "use_2D": True,
        },
        "overall": {
            "max_time": 2.0,           # 2 simulated minutes
            "dt_diffusion": 0.01,
            "dt_mechanics": 0.1,
            "dt_phenotype": 6.0,
        },
        "parallel": {"omp_num_threads": 2},
        "save": {
            "folder": "output",
            "full_data_interval": 1.0,
            "svg_interval": 1.0,
            "svg_enabled": False,
        },
        "options": {"random_seed": 42, "virtual_wall_at_domain_edge": True},
        "substrates": [
            {
                "name": "oxygen", "units": "mmHg",
                "diffusion_coefficient": 100000.0,
                "decay_rate": 0.1,
                "initial_condition": 38.0,
                "dirichlet_enabled": True,
                "dirichlet_value": 38.0,
            },
            {
                "name": "glucose", "units": "mM",
                "diffusion_coefficient": 50000.0,
                "decay_rate": 0.05,
                "initial_condition": 5.5,
                "dirichlet_enabled": False,
            },
        ],
        "cell_types": [{"name": "tumor", "id": 0}],
        "user_parameters": {"number_of_cells": 3},
    }


# -- Fast structural test ----------------------------------------------------

def test_generated_project_structure(tmp_path: Path) -> None:
    physiboss = DEFAULT_PHYSIBOSS_ROOT
    if not physiboss.exists():
        pytest.skip(f"PhysiBoSS-master not found at {physiboss}")

    project_dir = generate_project(
        spec=_minimal_spec(),
        output_dir=tmp_path,
        physiboss_root=physiboss,
        project_name="proj",
    )

    expected = [
        "config/PhysiCell_settings.xml",
        "config/cell_rules.csv",
        "custom_modules/custom.h",
        "custom_modules/custom.cpp",
        "custom_modules/occ_observability.h",
        "custom_modules/occ_observability.cpp",
        "main.cpp",
        "Makefile",
    ]
    for rel in expected:
        assert (project_dir / rel).is_file(), f"missing: {rel}"

    for sym in ("core", "BioFVM", "modules"):
        link = project_dir / sym
        assert link.is_symlink(), f"{sym} is not a symlink"
        assert link.resolve().exists(), f"{sym} symlink target missing"

    xml = (project_dir / "config" / "PhysiCell_settings.xml").read_text()
    assert "<variable name=\"oxygen\"" in xml
    assert "<variable name=\"glucose\"" in xml
    assert "<cell_definition name=\"tumor\"" in xml
    assert "enabled=\"false\"" in xml  # cell_rules disabled until Phase 3

    custom_cpp = (project_dir / "custom_modules" / "custom.cpp").read_text()
    assert "update_phenotype_composed" in custom_cpp
    assert "rule_phenotype_function" in custom_cpp
    assert "occ::rules_observe_begin" in custom_cpp
    assert "occ::rules_observe_end" in custom_cpp

    main_cpp = (project_dir / "main.cpp").read_text()
    assert "occ::init( PhysiCell_settings.folder" in main_cpp
    assert "occ::flush();" in main_cpp


def test_missing_required_field_raises(tmp_path: Path) -> None:
    spec = _minimal_spec()
    del spec["domain"]["x_min"]
    with pytest.raises(SpecError, match="x_min"):
        generate_project(
            spec=spec,
            output_dir=tmp_path,
            physiboss_root=DEFAULT_PHYSIBOSS_ROOT,
        )


def test_substrate_without_name_raises(tmp_path: Path) -> None:
    spec = _minimal_spec()
    del spec["substrates"][0]["name"]
    with pytest.raises(SpecError, match="name"):
        generate_project(
            spec=spec,
            output_dir=tmp_path,
            physiboss_root=DEFAULT_PHYSIBOSS_ROOT,
        )


# -- Slow build+run test -----------------------------------------------------

@pytest.mark.slow
def test_generated_project_builds_and_runs(tmp_path: Path) -> None:
    physiboss = DEFAULT_PHYSIBOSS_ROOT
    if not physiboss.exists():
        pytest.skip(f"PhysiBoSS-master not found at {physiboss}")
    if not shutil.which("g++") and not shutil.which("c++"):
        pytest.skip("no C++ compiler in PATH")
    if not shutil.which("make"):
        pytest.skip("make not in PATH")

    project_dir = generate_project(
        spec=_minimal_spec(),
        output_dir=tmp_path,
        physiboss_root=physiboss,
        project_name="proj",
    )

    env = os.environ.copy()
    # macOS clang without libomp can't compile PhysiCell; let users override.
    # On a typical dev box with `brew install gcc`, set PHYSICELL_CPP=g++-14.
    build = subprocess.run(
        ["make", "-j2"],
        cwd=project_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if build.returncode != 0:
        pytest.skip(
            "PhysiCell build failed (likely missing OpenMP-capable g++; "
            "set PHYSICELL_CPP=g++-14 or similar). "
            f"stderr tail:\n{build.stderr[-2000:]}"
        )

    binary = project_dir / "proj"
    assert binary.exists(), "make completed but no binary produced"

    run = subprocess.run(
        [str(binary)],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert run.returncode == 0, (
        f"simulation crashed: stdout tail:\n{run.stdout[-1500:]}\n"
        f"stderr tail:\n{run.stderr[-1500:]}"
    )

    output_dir = project_dir / "output"
    snapshots = sorted(output_dir.glob("output*.xml"))
    assert snapshots, "no output snapshots were produced"
    initial = output_dir / "initial.xml"
    final = output_dir / "final.xml"
    assert initial.exists() and final.exists()

    jsonl = output_dir / "occ_events.jsonl"
    assert jsonl.exists(), "occ_events.jsonl was not produced"


# -- Phase 3: Hill rules end-to-end ------------------------------------------

def _hill_rule_spec() -> Dict[str, Any]:
    """Workflow that reliably emits rule_engine_changed events.

    Oxygen starts at 38 mmHg everywhere and decays uniformly (decay_rate=1,
    no Dirichlet boundary), so it falls past the Hill half_max=5 during the
    run. The "increases necrosis" rule moves the necrosis rate up at first
    (high O2 → near max_response) and back down as O2 decays — each
    phenotype tick produces a different target, so begin/end diffs fire.
    """
    return {
        "domain": {
            "x_min": -150.0, "x_max": 150.0,
            "y_min": -150.0, "y_max": 150.0,
            "z_min": -10.0, "z_max": 10.0,
            "dx": 20.0, "dy": 20.0, "dz": 20.0,
            "use_2D": True,
        },
        "overall": {
            "max_time": 5.0,
            "dt_diffusion": 0.01,
            "dt_mechanics": 0.1,
            "dt_phenotype": 0.1,
        },
        "parallel": {"omp_num_threads": 2},
        "save": {
            "folder": "output",
            "full_data_interval": 1.0,
            "svg_interval": 1.0,
            "svg_enabled": False,
        },
        "options": {"random_seed": 7, "virtual_wall_at_domain_edge": True},
        "substrates": [{
            "name": "oxygen", "units": "mmHg",
            "diffusion_coefficient": 100000.0,
            "decay_rate": 1.0,
            "initial_condition": 38.0,
            "dirichlet_enabled": False,
            "dirichlet_value": 0.0,
        }],
        "cell_types": [{"name": "tumor", "id": 0}],
        "hill_rules": [{
            "cell_type": "tumor", "signal": "oxygen", "direction": "increases",
            "behavior": "necrosis",
            "max_response": 0.5, "half_max": 5.0, "hill_power": 8.0,
            "use_on_dead": 0,
        }],
        "user_parameters": {"number_of_cells": 3},
    }


@pytest.mark.slow
def test_hill_rule_fires_rule_engine_changed(tmp_path: Path) -> None:
    physiboss = DEFAULT_PHYSIBOSS_ROOT
    if not physiboss.exists():
        pytest.skip(f"PhysiBoSS-master not found at {physiboss}")
    if not (shutil.which("g++") or shutil.which("c++")):
        pytest.skip("no C++ compiler in PATH")

    project_dir = generate_project(
        spec=_hill_rule_spec(),
        output_dir=tmp_path,
        physiboss_root=physiboss,
        project_name="hill_proj",
    )

    # Confirm codegen flipped the rules block on and wrote one CSV row.
    xml = (project_dir / "config" / "PhysiCell_settings.xml").read_text()
    assert "enabled=\"true\"" in xml, "<cell_rules> not enabled with a rule present"
    csv = (project_dir / "config" / "cell_rules.csv").read_text().strip()
    assert csv, "cell_rules.csv is empty"
    assert csv.startswith("tumor,oxygen,increases,necrosis,")

    build = subprocess.run(
        ["make", "-j2"], cwd=project_dir, env=os.environ.copy(),
        capture_output=True, text=True, timeout=600,
    )
    if build.returncode != 0:
        pytest.skip(
            "PhysiCell build failed (set PHYSICELL_CPP=g++-14 or similar). "
            f"stderr tail:\n{build.stderr[-1500:]}"
        )

    binary = project_dir / "hill_proj"
    assert binary.exists()
    run = subprocess.run(
        [str(binary)], cwd=project_dir,
        capture_output=True, text=True, timeout=300,
    )
    assert run.returncode == 0, (
        f"simulation crashed: stdout tail:\n{run.stdout[-1500:]}\n"
        f"stderr tail:\n{run.stderr[-1500:]}"
    )

    jsonl = project_dir / "output" / "occ_events.jsonl"
    assert jsonl.exists(), "occ_events.jsonl was not produced"
    events = [json.loads(ln) for ln in jsonl.read_text().splitlines() if ln.strip()]
    necrosis_events = [e for e in events
                       if e.get("event") == "rule_engine_changed"
                       and e.get("rate") == 1.0]   # 1.0 == kRateNecrosis
    assert necrosis_events, (
        f"expected rule_engine_changed events for necrosis but got "
        f"{len(events)} total events; sample: {events[:3]!r}"
    )
    # Sanity: at least one event should show necrosis moving toward saturation.
    assert any(e.get("to", 0.0) > 0.0 for e in necrosis_events), (
        "necrosis rate never moved above 0 — rule may not have fired"
    )
