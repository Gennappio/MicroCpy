"""
Generate Initial Cells Packed in a Sphere (3D) or Circle (2D).

Writes a VTK checkpoint file with N cells at discrete integer grid positions
arranged in a sphere (3D) or circle (2D, z=0).  Does NOT write to the workflow
context — the next workflow node should be ``read_checkpoint`` pointing at
the generated file.

The dimensions (2 vs 3) are read from ``context['dimensions']`` which must
be set by ``setup_simulation`` before calling this function.

ALGORITHM:
    1. Read dimensions from context['dimensions']
    2. Read cell_height from context config (or use parameter default)
    3. Compute grid center (or use provided center)
    4. Estimate radius R from N:
       - 3D: R = (3N / (4*pi))^(1/3) + 2
       - 2D: R = sqrt(N / pi) + 2
    5. Enumerate ALL integer grid positions (x,y,z) with distance(center) <= R
    6. Sort by Euclidean distance from center (true sphere/circle)
    7. Take the closest N positions
    8. Write enhanced VTK UNSTRUCTURED_GRID file (hexahedron cells, coords
       in meters = grid_coord * cell_height_m)

The VTK file uses the **enhanced** format (metadata header with ``size=``,
``genes=``, ``phenotypes=``) so that ``read_checkpoint`` →
``InitialStateManager`` → ``VTKDomainLoader.load_complete_domain`` correctly
recovers integer grid positions.
"""

import math
from typing import Dict, Any, List, Tuple
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Generate Initial Cells",
    description="Create N cells packed in a sphere (3D) or circle (2D), write VTK file",
    category="INITIALIZATION",
    parameters=[
        {"name": "num_cells", "type": "INT",
         "description": "Number of cells to create", "default": 1000},
        {"name": "file_path", "type": "STRING",
         "description": "Output VTK file path (relative to engine root)",
         "default": "generated_cells.vtk"},
        {"name": "center_x", "type": "INT",
         "description": "Center X (grid coord). -1 = auto (domain center)",
         "default": -1},
        {"name": "center_y", "type": "INT",
         "description": "Center Y (grid coord). -1 = auto (domain center)",
         "default": -1},
        {"name": "center_z", "type": "INT",
         "description": "Center Z (grid coord, 3D only). -1 = auto",
         "default": -1},
        {"name": "cell_height_um", "type": "FLOAT",
         "description": "Cell height in um (read from config if available)",
         "default": 5.0},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def generate_initial_cells(
    context: Dict[str, Any],
    num_cells: int = 1000,
    file_path: str = "generated_cells.vtk",
    center_x: int = -1,
    center_y: int = -1,
    center_z: int = -1,
    cell_height_um: float = 5.0,
    **kwargs,
) -> bool:
    """
    Generate N cells packed in a sphere or circle and write to a VTK file.

    This function ONLY writes a VTK checkpoint file.  It does NOT modify the
    workflow context population.  The next workflow step should be
    ``read_checkpoint`` with ``file_path`` pointing to the same file.

    The dimensions (2D circle vs 3D sphere) are read from
    ``context['dimensions']`` which must be set by ``setup_simulation``.

    Args:
        context:        Workflow context (reads dimensions from context['dimensions'])
        num_cells:      Number of cells to generate
        file_path:      Output VTK file path (relative to engine root)
        center_x/y/z:  Center of the cluster in grid coords (-1 = domain center)
        cell_height_um: Cell height in micrometers (overridden by config if present)

    Returns:
        True if successful, False otherwise
    """
    # ------------------------------------------------------------------
    # Read dimensions from context (set by setup_simulation)
    # ------------------------------------------------------------------
    dimensions = context.get('dimensions')
    if dimensions is None:
        print("[ERROR] 'dimensions' not found in context. Run setup_simulation first.")
        return False
    
    is_3d = (dimensions == 3)

    # ------------------------------------------------------------------
    # Read cell_height and domain size from context config
    # ------------------------------------------------------------------
    ch_um = cell_height_um  # fallback
    domain_grid_x = domain_grid_y = domain_grid_z = 40  # defaults

    config = context.get("config")
    if config is not None:
        try:
            ch_um = float(config.domain.cell_height.micrometers)
        except Exception:
            pass
        try:
            domain_grid_x = int(config.domain.size_x.micrometers / ch_um)
            domain_grid_y = int(config.domain.size_y.micrometers / ch_um)
            domain_grid_z = int(config.domain.size_z.micrometers / ch_um) if is_3d else 1
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Determine cluster center (default: domain center)
    # ------------------------------------------------------------------
    cx = center_x if center_x >= 0 else domain_grid_x // 2
    cy = center_y if center_y >= 0 else domain_grid_y // 2
    cz = center_z if center_z >= 0 else (domain_grid_z // 2 if is_3d else 0)

    # ------------------------------------------------------------------
    # Generate sphere / circle positions sorted by Euclidean distance
    # ------------------------------------------------------------------
    if is_3d:
        positions = _sphere_positions(cx, cy, cz, num_cells)
    else:
        positions = _circle_positions(cx, cy, num_cells)

    actual = len(positions)
    if actual < num_cells:
        print(f"[WARNING] Could only place {actual}/{num_cells} cells")

    # ------------------------------------------------------------------
    # Resolve output path
    # ------------------------------------------------------------------
    vtk_path = _resolve_output_path(context, file_path)
    vtk_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Write enhanced VTK file (coords in meters)
    # ------------------------------------------------------------------
    _write_enhanced_vtk(vtk_path, positions, ch_um, is_3d)

    print(f"[GENERATE] Wrote {actual} cells to {vtk_path} "
          f"({'sphere' if is_3d else 'circle'}, "
          f"center=({cx},{cy}{f',{cz}' if is_3d else ''}), "
          f"cell_height={ch_um} um)")

    return True


# =====================================================================
# POSITION GENERATORS — Euclidean distance for true sphere / circle
# =====================================================================

def _sphere_positions(
    cx: int, cy: int, cz: int, n: int,
) -> List[Tuple[int, int, int]]:
    """
    Return the *N* closest integer grid positions to (cx, cy, cz).

    Uses Euclidean distance → true spherical shape.
    Overestimates radius, enumerates candidates, sorts, takes first N.
    """
    r_est = (3.0 * n / (4.0 * math.pi)) ** (1.0 / 3.0) + 2
    r_max = int(math.ceil(r_est))

    # Iteratively grow r_max until we have enough candidates
    while True:
        candidates: List[Tuple[float, Tuple[int, int, int]]] = []
        for dx in range(-r_max, r_max + 1):
            for dy in range(-r_max, r_max + 1):
                for dz in range(-r_max, r_max + 1):
                    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                    x, y, z = cx + dx, cy + dy, cz + dz
                    if x >= 0 and y >= 0 and z >= 0:
                        candidates.append((dist, (x, y, z)))
        if len(candidates) >= n:
            break
        r_max += 1

    candidates.sort(key=lambda t: t[0])
    return [pos for _, pos in candidates[:n]]


def _circle_positions(
    cx: int, cy: int, n: int,
) -> List[Tuple[int, int, int]]:
    """
    Return the *N* closest integer grid positions to (cx, cy) on the z=0 plane.

    Uses Euclidean distance → true circular shape.
    """
    r_est = math.sqrt(n / math.pi) + 2
    r_max = int(math.ceil(r_est))

    while True:
        candidates: List[Tuple[float, Tuple[int, int, int]]] = []
        for dx in range(-r_max, r_max + 1):
            for dy in range(-r_max, r_max + 1):
                dist = math.sqrt(dx * dx + dy * dy)
                x, y = cx + dx, cy + dy
                if x >= 0 and y >= 0:
                    candidates.append((dist, (x, y, 0)))
        if len(candidates) >= n:
            break
        r_max += 1

    candidates.sort(key=lambda t: t[0])
    return [pos for _, pos in candidates[:n]]


# =====================================================================
# VTK WRITER — enhanced format (read by VTKDomainLoader)
# =====================================================================

def _write_enhanced_vtk(
    vtk_path: Path,
    positions: List[Tuple[int, ...]],
    cell_height_um: float,
    is_3d: bool,
) -> None:
    """
    Write an **enhanced-format** VTK UNSTRUCTURED_GRID file.

    Coordinates are in **meters** (grid_coord × cell_height_m) so that
    ``VTKDomainLoader.load_complete_domain`` divides by ``cell_size_m``
    and recovers integer grid positions exactly.

    The description line contains ``size=``, ``genes=``, and
    ``phenotypes=`` markers so that ``InitialStateManager`` dispatches to
    the enhanced loader path.
    """
    n = len(positions)
    num_points = n * 8  # 8 vertices per hexahedron

    cell_height_m = cell_height_um * 1e-6  # metres
    half_edge = cell_height_m / 2.0

    # Vertex offsets for a unit cube (VTK_HEXAHEDRON ordering)
    # Scaled to cell_height_m
    offsets = [
        (-half_edge, -half_edge, -half_edge),
        (+half_edge, -half_edge, -half_edge),
        (+half_edge, +half_edge, -half_edge),
        (-half_edge, +half_edge, -half_edge),
        (-half_edge, -half_edge, +half_edge),
        (+half_edge, -half_edge, +half_edge),
        (+half_edge, +half_edge, +half_edge),
        (-half_edge, +half_edge, +half_edge),
    ]

    with open(vtk_path, "w") as f:
        # ---- Header (line 1) -----------------------------------------
        f.write("# vtk DataFile Version 3.0\n")

        # ---- Description (line 2) — must contain |, genes=, phenotypes=
        desc = (
            f"| size={cell_height_um}um "
            f"| dimensions={3 if is_3d else 2} "
            f"| cells={n} "
            f"| genes= "
            f"| phenotypes=Quiescent"
        )
        f.write(f"{desc}\n")

        f.write("ASCII\n")
        f.write("DATASET UNSTRUCTURED_GRID\n\n")

        # ---- POINTS (in metres) --------------------------------------
        f.write(f"POINTS {num_points} float\n")
        for gx, gy, gz in positions:
            # Center in metres
            cx_m = gx * cell_height_m
            cy_m = gy * cell_height_m
            cz_m = gz * cell_height_m
            for dx, dy, dz in offsets:
                f.write(f"{cx_m + dx:.10e} {cy_m + dy:.10e} {cz_m + dz:.10e}\n")
        f.write("\n")

        # ---- CELLS (hexahedra) ----------------------------------------
        total_ints = n * 9  # 1 count + 8 indices
        f.write(f"CELLS {n} {total_ints}\n")
        for i in range(n):
            base = i * 8
            indices = " ".join(str(base + j) for j in range(8))
            f.write(f"8 {indices}\n")
        f.write("\n")

        # ---- CELL_TYPES (12 = VTK_HEXAHEDRON) -------------------------
        f.write(f"CELL_TYPES {n}\n")
        for _ in range(n):
            f.write("12\n")
        f.write("\n")

        # ---- CELL_DATA ------------------------------------------------
        f.write(f"CELL_DATA {n}\n")

        # Phenotype scalar — 0 = Quiescent (maps to phenotypes= list)
        f.write("SCALARS Phenotype int 1\n")
        f.write("LOOKUP_TABLE default\n")
        for _ in range(n):
            f.write("0\n")


# =====================================================================
# PATH RESOLUTION
# =====================================================================

def _resolve_output_path(context: Dict[str, Any], file_path: str) -> Path:
    """
    Resolve the output VTK file path.

    Tries (in order):
        1. context['resolve_path'](file_path)
        2. Relative to engine root
        3. file_path as-is
    """
    if "resolve_path" in context:
        return Path(context["resolve_path"](file_path))

    p = Path(file_path)
    if p.is_absolute():
        return p

    # Relative to engine root (opencellcomms_engine/)
    engine_root = Path(__file__).parent.parent.parent.parent
    return engine_root / file_path
