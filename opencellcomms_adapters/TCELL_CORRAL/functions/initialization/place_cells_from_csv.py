"""Place PhysiCell-format cells (x,y,z,type) onto the lattice for the Corral model.

The Corral experiment ships a PhysiCell ``cells.csv``: physical coordinates in
micrometers centered on the origin, plus a ``type`` column (T0 / dendritic_cell /
endothelial_cell). This node converts those centered-micrometer coordinates to
non-negative bio-grid indices, tags each cell with its ABM kind (T0 -> ``tcell``)
and — for T0 — a starting ``fate`` of ``naive``, then loads them into the legacy
CellPopulation. ``build_tcell_abm_population`` wraps that population afterwards so
the per-kind asks and gene-network steps run on the ABM motor.

This is the one loader that cannot reuse ``load_cells_from_csv``: the PhysiCell
CSV has no ``x,y`` grid columns or ``phenotype``, and its coordinates are centered
micrometers rather than grid indices.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.workflow.decorators import register_function
from src.interfaces.base import IConfig

# .../TCELL_CORRAL/functions/initialization/<this file> -> .../TCELL_CORRAL/data
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# PhysiCell `type` column -> ABM agent kind (others map to themselves).
_KIND_MAP = {"T0": "tcell"}

Pos = Tuple[int, int]


def _nearest_free(pos: Pos, taken: Set[Pos], nx: int, ny: int) -> Optional[Pos]:
    """Return ``pos`` if free, else the closest free tile by expanding-ring search.

    On-lattice placement of the dense T0 cluster produces collisions; nudging to
    the nearest free tile keeps every cell instead of dropping the overlaps.
    """
    if pos not in taken and 0 <= pos[0] < nx and 0 <= pos[1] < ny:
        return pos
    for r in range(1, max(nx, ny)):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                cand = (pos[0] + dx, pos[1] + dy)
                if 0 <= cand[0] < nx and 0 <= cand[1] < ny and cand not in taken:
                    return cand
    return None


@register_function(
    typed_env_exempt=True,
    requires=["population"],
    display_name="Place Cells from PhysiCell CSV",
    description="Load PhysiCell-format cells (x,y,z,type in centered micrometers) onto "
                "the bio-grid, tagging each with its ABM kind and a naive fate.",
    category="INITIALIZATION",
    parameters=[
        {"name": "file_path", "type": "STRING",
         "description": "PhysiCell cells.csv (relative to the plugin's data/ dir, or absolute)",
         "default": "cells.csv"},
    ],
    inputs=["context"],
    outputs=["loaded_cells"],
    cloneable=False,
)
def place_cells_from_csv(
    context: Dict[str, Any],
    file_path: str = "cells.csv",
    **kwargs,
) -> bool:
    population = context.get("population")
    config: Optional[IConfig] = context.get("config")
    if not population or not config:
        print("[TCELL_CORRAL] Population and config must be set up before placing cells")
        return False

    csv_path = Path(file_path)
    if not csv_path.is_absolute():
        csv_path = _DATA_DIR / file_path
    if not csv_path.exists():
        print(f"[TCELL_CORRAL] CSV not found: {csv_path}")
        return False

    # Centered micrometers -> non-negative grid index. Bio-grid spacing is the
    # cell height; the domain is centered on the origin, so x_min = -size_x / 2.
    size_x = config.domain.size_x.micrometers
    size_y = config.domain.size_y.micrometers
    cell_um = config.domain.cell_height.micrometers
    nx = int(size_x / cell_um)
    ny = int(size_y / cell_um)
    x_min, y_min = -size_x / 2.0, -size_y / 2.0

    taken: Set[Pos] = set()
    cell_data: List[Dict[str, Any]] = []
    nudged = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ctype = (row.get("type") or "").strip()
            if not ctype:
                continue
            kind = _KIND_MAP.get(ctype, ctype)
            gx = max(0, min(nx - 1, int((float(row["x"]) - x_min) / cell_um)))
            gy = max(0, min(ny - 1, int((float(row["y"]) - y_min) / cell_um)))
            free = _nearest_free((gx, gy), taken, nx, ny)
            if free is None:
                print(f"[TCELL_CORRAL] No free tile for a {ctype} cell; skipped")
                continue
            if free != (gx, gy):
                nudged += 1
            taken.add(free)
            meta: Dict[str, Any] = {"_kind": kind}
            if kind == "tcell":
                meta["fate"] = "naive"
            cell_data.append({
                "position": free,
                "phenotype": "naive" if kind == "tcell" else kind,
                "metabolic_state": meta,
            })

    added = population.initialize_cells(cell_data)
    by_kind: Dict[str, int] = {}
    for cd in cell_data:
        k = cd["metabolic_state"]["_kind"]
        by_kind[k] = by_kind.get(k, 0) + 1
    print(f"[TCELL_CORRAL] Placed {added}/{len(cell_data)} cells on a {nx}x{ny} bio-grid "
          f"({nudged} nudged off collisions): {by_kind}")
    return added > 0
