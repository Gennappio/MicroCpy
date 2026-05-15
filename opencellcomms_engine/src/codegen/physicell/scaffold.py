"""Generate a PhysiCell project tree from an OpenCellComms spec.

See ``docs/Physicell_Facade_plan.md`` for the architecture. This is Phase
2's entry point: workflow JSON → (eventually, via the Phase-3 GUI nodes)
the ``spec`` dict consumed here → a directory that ``make && ./project``
runs against unmodified ``PhysiBoSS-master/``.
"""
from __future__ import annotations

import copy
import shutil
from pathlib import Path
from typing import Any, Dict

import jinja2

from src.codegen.physicell.hill_grammar import normalize_rule, validate_rules
from src.codegen.physicell.runtime import (
    OBSERVABILITY_HEADER,
    OBSERVABILITY_SOURCE,
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Upstream subdirectories of PhysiBoSS-master that the generated Makefile
# expects to find at ./core, ./BioFVM, ./modules, ./addons.
_UPSTREAM_SYMLINKS = ("core", "BioFVM", "modules", "addons")


class SpecError(ValueError):
    """Raised when the spec dict is missing required fields."""


# -- Spec defaults ------------------------------------------------------------

_DEFAULT_OVERALL: Dict[str, Any] = {
    "max_time": 60.0,
    "dt_diffusion": 0.01,
    "dt_mechanics": 0.1,
    "dt_phenotype": 6.0,
}

_DEFAULT_PARALLEL: Dict[str, Any] = {"omp_num_threads": 4}

_DEFAULT_SAVE: Dict[str, Any] = {
    "folder": "output",
    "full_data_interval": 30.0,
    "svg_interval": 30.0,
    "svg_enabled": False,
}

_DEFAULT_OPTIONS: Dict[str, Any] = {
    "random_seed": 0,
    "virtual_wall_at_domain_edge": True,
}

_DEFAULT_USER_PARAMETERS: Dict[str, Any] = {"number_of_cells": 5}


def _validate_and_default(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-copy the spec, fill defaults, validate required fields."""
    out = copy.deepcopy(spec)

    if "domain" not in out:
        raise SpecError("spec.domain is required")
    required_domain = {
        "x_min", "x_max", "y_min", "y_max", "z_min", "z_max",
        "dx", "dy", "dz", "use_2D",
    }
    missing = required_domain - set(out["domain"])
    if missing:
        raise SpecError(f"spec.domain missing keys: {sorted(missing)}")

    if not out.get("substrates"):
        raise SpecError("spec.substrates must list at least one substrate")
    for i, sub in enumerate(out["substrates"]):
        for k in ("name", "diffusion_coefficient", "decay_rate", "initial_condition"):
            if k not in sub:
                raise SpecError(f"spec.substrates[{i}] missing '{k}'")
        sub.setdefault("units", "dimensionless")
        sub.setdefault("dirichlet_enabled", False)
        sub.setdefault("dirichlet_value", sub["initial_condition"])

    if not out.get("cell_types"):
        raise SpecError("spec.cell_types must list at least one cell type")
    for i, ct in enumerate(out["cell_types"]):
        if "name" not in ct:
            raise SpecError(f"spec.cell_types[{i}] missing 'name'")
        ct.setdefault("id", i)

    out.setdefault("overall", {})
    out["overall"] = {**_DEFAULT_OVERALL, **out["overall"]}

    out.setdefault("parallel", {})
    out["parallel"] = {**_DEFAULT_PARALLEL, **out["parallel"]}

    out.setdefault("save", {})
    out["save"] = {**_DEFAULT_SAVE, **out["save"]}

    out.setdefault("options", {})
    out["options"] = {**_DEFAULT_OPTIONS, **out["options"]}

    out.setdefault("user_parameters", {})
    out["user_parameters"] = {**_DEFAULT_USER_PARAMETERS, **out["user_parameters"]}

    out.setdefault("hill_rules", [])
    if out["hill_rules"]:
        substrate_names = [s["name"] for s in out["substrates"]]
        cell_type_names = [c["name"] for c in out["cell_types"]]
        errors = validate_rules(out["hill_rules"], substrate_names, cell_type_names)
        if errors:
            raise SpecError("Hill-rule grammar errors:\n  " + "\n  ".join(errors))
        out["hill_rules"] = [normalize_rule(r) for r in out["hill_rules"]]
    out.setdefault("cell_rules_enabled", bool(out["hill_rules"]))

    return out


# -- File materialization -----------------------------------------------------

def _env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
    )


def _render(env: jinja2.Environment, template_name: str, ctx: Dict[str, Any]) -> str:
    return env.get_template(template_name).render(**ctx)


def _link_upstream(project_dir: Path, physiboss_root: Path) -> None:
    """Symlink the upstream tree's source dirs into the project root.

    Symlinks (not copies) so a `git pull` of PhysiBoSS-master is visible to
    every generated project automatically.
    """
    for name in _UPSTREAM_SYMLINKS:
        target = physiboss_root / name
        if not target.exists():
            # 'addons' may legitimately be absent in stripped checkouts; skip.
            if name == "addons":
                continue
            raise SpecError(
                f"PhysiBoSS source dir not found: {target}. "
                f"Pass physiboss_root pointing at an extracted PhysiBoSS-master tree."
            )
        link = project_dir / name
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target.resolve())


def _write_cell_rules_csv(project_dir: Path, spec: Dict[str, Any]) -> None:
    """Emit the upstream CBHG v3.0 8-column CSV (one rule per row).

    Field names with commas would break the format; cell-type and signal
    names are upstream-defined strings so we leave them unquoted, matching
    the rules_sample reference CSV exactly.
    """
    csv_path = project_dir / "config" / "cell_rules.csv"
    if not spec["hill_rules"]:
        csv_path.write_text("")
        return
    # Column order matches PhysiCell_rules.cpp::parse_csv_rule_v3:
    #   cell_type, signal, direction, behavior,
    #   max_response, half_max, hill_power, use_for_dead
    rows = []
    for r in spec["hill_rules"]:
        rows.append(
            f"{r['cell_type']},{r['signal']},{r['direction']},{r['behavior']},"
            f"{r['max_response']},{r['half_max']},{r['hill_power']},{r['use_on_dead']}"
        )
    csv_path.write_text("\n".join(rows) + "\n")


# -- Public entry point ------------------------------------------------------

def generate_project(
    spec: Dict[str, Any],
    output_dir: Path,
    physiboss_root: Path,
    project_name: str = "physicell_project",
) -> Path:
    """Materialize a runnable PhysiCell project under ``output_dir/<project_name>``.

    Args:
        spec: validated/defaulted PhysiCell domain spec. See module docstring.
        output_dir: parent directory; will be created if it does not exist.
        physiboss_root: extracted ``PhysiBoSS-master`` tree.
        project_name: subdirectory name under ``output_dir``.

    Returns:
        The generated project directory.
    """
    output_dir = Path(output_dir)
    physiboss_root = Path(physiboss_root)
    if not physiboss_root.exists():
        raise SpecError(f"physiboss_root does not exist: {physiboss_root}")

    spec = _validate_and_default(spec)

    project_dir = output_dir / project_name
    (project_dir / "config").mkdir(parents=True, exist_ok=True)
    (project_dir / "custom_modules").mkdir(parents=True, exist_ok=True)
    (project_dir / "output").mkdir(parents=True, exist_ok=True)

    env = _env()

    ctx = {
        "domain": spec["domain"],
        "overall": spec["overall"],
        "parallel": spec["parallel"],
        "save": spec["save"],
        "options": spec["options"],
        "substrates": spec["substrates"],
        "cell_types": spec["cell_types"],
        "user_parameters": spec["user_parameters"],
        "cell_rules_enabled": spec["cell_rules_enabled"],
        "program_name": project_name,
    }

    (project_dir / "config" / "PhysiCell_settings.xml").write_text(
        _render(env, "PhysiCell_settings.xml.j2", ctx)
    )
    (project_dir / "custom_modules" / "custom.h").write_text(
        _render(env, "custom.h.j2", ctx)
    )
    (project_dir / "custom_modules" / "custom.cpp").write_text(
        _render(env, "custom.cpp.j2", ctx)
    )
    (project_dir / "main.cpp").write_text(
        _render(env, "main.cpp.j2", ctx)
    )
    (project_dir / "Makefile").write_text(
        _render(env, "Makefile.j2", ctx)
    )

    shutil.copy(OBSERVABILITY_HEADER, project_dir / "custom_modules" / "occ_observability.h")
    shutil.copy(OBSERVABILITY_SOURCE, project_dir / "custom_modules" / "occ_observability.cpp")

    _write_cell_rules_csv(project_dir, spec)
    _link_upstream(project_dir, physiboss_root)

    return project_dir


__all__ = ["generate_project", "SpecError"]
