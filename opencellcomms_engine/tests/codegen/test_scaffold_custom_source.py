"""Tests for scaffold.py project-template mode (Phase 4.5).

Validates that when spec['custom_modules_source'] is set:
  - The project's custom.cpp / custom.h are copied (not the stub template).
  - occ_glue.cpp is generated.
  - occ_observability.{h,cpp} are still present.
  - When NOT set, the stub template is used and occ_glue.cpp is absent.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import pytest

from opencellcomms_adapters.PhysiBoSS.codegen.scaffold import SpecError, generate_project

PHYSIBOSS_ROOT = os.environ.get("PHYSIBOSS_ROOT")
has_physiboss = pytest.mark.skipif(
    not PHYSIBOSS_ROOT or not (Path(PHYSIBOSS_ROOT) / "core").is_dir(),
    reason="PHYSIBOSS_ROOT not set or invalid",
)

_MINIMAL_SPEC: Dict[str, Any] = {
    "domain": {
        "x_min": -100.0, "x_max": 100.0,
        "y_min": -100.0, "y_max": 100.0,
        "z_min": -10.0,  "z_max": 10.0,
        "dx": 20.0, "dy": 20.0, "dz": 20.0,
        "use_2D": True,
    },
    "substrates": [
        {"name": "oxygen", "diffusion_coefficient": 1e5,
         "decay_rate": 0.1, "initial_condition": 38.0}
    ],
    "cell_types": [{"name": "default", "id": 0}],
}


def test_stub_mode_no_occ_glue(tmp_path):
    spec = {**_MINIMAL_SPEC}
    if PHYSIBOSS_ROOT and (Path(PHYSIBOSS_ROOT) / "core").is_dir():
        physiboss = Path(PHYSIBOSS_ROOT)
    else:
        pytest.skip("PHYSIBOSS_ROOT not set")
    project_dir = generate_project(spec, tmp_path, physiboss, "stub_test")
    cm = project_dir / "custom_modules"
    assert (cm / "custom.cpp").exists()
    assert (cm / "custom.h").exists()
    assert not (cm / "occ_glue.cpp").exists()
    assert (cm / "occ_observability.h").exists()
    assert (cm / "occ_observability.cpp").exists()


@has_physiboss
def test_project_template_mode_copies_source_and_generates_glue(tmp_path):
    physiboss = Path(PHYSIBOSS_ROOT)
    rules_sample_cm = physiboss / "sample_projects" / "rules_sample" / "custom_modules"
    if not rules_sample_cm.is_dir():
        pytest.skip("rules_sample not present")

    spec = {
        **_MINIMAL_SPEC,
        "custom_modules_source": {
            "type": "sample_project",
            "project_name": "rules_sample",
            "source_dir": str(rules_sample_cm),
        },
    }
    project_dir = generate_project(spec, tmp_path, physiboss, "template_test")
    cm = project_dir / "custom_modules"

    assert (cm / "custom.cpp").exists()
    assert (cm / "custom.h").exists()
    assert (cm / "occ_glue.cpp").exists()
    assert (cm / "occ_observability.h").exists()
    assert (cm / "occ_observability.cpp").exists()

    glue_text = (cm / "occ_glue.cpp").read_text()
    assert "update_phenotype_composed" in glue_text
    assert "occ_install_observability_hooks" in glue_text

    makefile_text = (project_dir / "Makefile").read_text()
    assert "occ_glue.o" in makefile_text

    main_text = (project_dir / "main.cpp").read_text()
    assert "occ_install_observability_hooks" in main_text


@has_physiboss
def test_project_template_coloring_flag(tmp_path):
    """projects that lack my_coloring_function get it from occ_glue.cpp."""
    physiboss = Path(PHYSIBOSS_ROOT)
    celltypes3_cm = physiboss / "sample_projects" / "celltypes3" / "custom_modules"
    if not celltypes3_cm.is_dir():
        pytest.skip("celltypes3 not present")

    header_text = (celltypes3_cm / "custom.h").read_text()
    project_provides_coloring = "my_coloring_function" in header_text

    spec = {
        **_MINIMAL_SPEC,
        "custom_modules_source": {
            "type": "sample_project",
            "project_name": "celltypes3",
            "source_dir": str(celltypes3_cm),
        },
    }
    project_dir = generate_project(spec, tmp_path, physiboss, "coloring_test")
    glue_text = (project_dir / "custom_modules" / "occ_glue.cpp").read_text()
    if not project_provides_coloring:
        assert "my_coloring_function" in glue_text
    else:
        assert "my_coloring_function" not in glue_text


@has_physiboss
def test_invalid_source_dir_raises(tmp_path):
    physiboss = Path(PHYSIBOSS_ROOT)
    spec = {
        **_MINIMAL_SPEC,
        "custom_modules_source": {
            "type": "sample_project",
            "project_name": "nonexistent",
            "source_dir": str(tmp_path / "does_not_exist"),
        },
    }
    with pytest.raises(SpecError, match="custom_modules_source"):
        generate_project(spec, tmp_path, physiboss, "bad_source_test")
