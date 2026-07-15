"""Load and lightly validate the case / condition YAML configs."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml

from evals.harness import _engine as E

EVALS = Path(__file__).resolve().parents[1]
CASES = EVALS / "cases"
CONDITIONS = EVALS / "conditions"


def load_case(name: str) -> dict:
    cfg = yaml.safe_load((CASES / f"{name}.yaml").read_text(encoding="utf-8"))
    cfg["_plugin_abs"] = str(E.REPO_ROOT / cfg["plugin"])
    cfg["_benchmark_abs"] = str(E.REPO_ROOT / cfg["benchmark_workflow"])
    return cfg


def load_condition(name: str) -> dict:
    return yaml.safe_load((CONDITIONS / f"{name}.yaml").read_text(encoding="utf-8"))


def all_cases() -> Dict[str, dict]:
    return {p.stem: load_case(p.stem) for p in sorted(CASES.glob("*.yaml"))}


def all_conditions() -> Dict[str, dict]:
    return {p.stem: load_condition(p.stem) for p in sorted(CONDITIONS.glob("*.yaml"))}
