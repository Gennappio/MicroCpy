"""Permanent C++ runtime sources copied verbatim into every generated project.

This is the only C++ owned by OpenCellComms; everything else under a
generated project's ``custom_modules/`` is templated per-workflow.
"""

from pathlib import Path

RUNTIME_DIR: Path = Path(__file__).resolve().parent
OBSERVABILITY_HEADER: Path = RUNTIME_DIR / "occ_observability.h"
OBSERVABILITY_SOURCE: Path = RUNTIME_DIR / "occ_observability.cpp"

__all__ = ["RUNTIME_DIR", "OBSERVABILITY_HEADER", "OBSERVABILITY_SOURCE"]
