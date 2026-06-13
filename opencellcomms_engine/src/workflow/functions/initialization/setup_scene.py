"""
Setup scene — build the discrete tile-grid "world" and seed its resource fields.

This is the single read-once "world description -> world" step. It reads a
declarative scene description (physical extent, tile size, per-axis topology,
and which fields exist with their initial values) and builds a ``TileGrid`` in
the context. Per-step resource dynamics (growback, decay, ...) are NOT here —
they live in visible workflow nodes that read/write the fields this creates.

The tile grid is independent of the FiPy diffusion mesh: it has its own
resolution (derived from extent / tile_size) and its own topology.
"""

import json
from typing import Any, Dict, List, Optional

from src.workflow.decorators import register_function
from src.workflow.logging import log, log_always


def _coerce_fields(fields: Any) -> List[Dict[str, Any]]:
    """Accept fields as a list of dicts or JSON strings (GUI listParameterNode)."""
    out: List[Dict[str, Any]] = []
    if not fields:
        return out
    for entry in fields:
        if isinstance(entry, str):
            entry = json.loads(entry)
        if not isinstance(entry, dict) or "name" not in entry:
            raise ValueError(f"Each scene field needs a 'name'; got {entry!r}")
        out.append(entry)
    return out


@register_function(
    display_name="Setup Scene",
    description="Build the discrete tile-grid world and seed its resource fields",
    category="INITIALIZATION",
    parameters=[
        {"name": "size_x", "type": "FLOAT", "description": "World extent in X (micrometers)", "default": 500.0},
        {"name": "size_y", "type": "FLOAT", "description": "World extent in Y (micrometers)", "default": 500.0},
        {"name": "tile_size", "type": "FLOAT", "description": "Edge length of one tile (micrometers)", "default": 10.0},
        {"name": "topology_x", "type": "STRING", "description": "X-axis topology", "default": "bounded", "options": ["bounded", "toroidal"]},
        {"name": "topology_y", "type": "STRING", "description": "Y-axis topology", "default": "bounded", "options": ["bounded", "toroidal"]},
        {"name": "fields", "type": "LIST", "description": "Resource fields: list of {name, initial_value}", "default": []},
    ],
    inputs=["context"],
    outputs=["tile_grid", "fields"],
    cloneable=False,
    compatible_kernels=["*"],
    requires=[],
    typed_env_exempt=True,
)
def setup_scene(
    context: Dict[str, Any],
    size_x: float = 500.0,
    size_y: float = 500.0,
    tile_size: float = 10.0,
    topology_x: str = "bounded",
    topology_y: str = "bounded",
    fields: Optional[List[Any]] = None,
    **kwargs,
) -> bool:
    """Build a TileGrid from the scene description and seed its fields.

    Args:
        context: Workflow context (TileGrid is stored under ``context['tile_grid']``
            and its field arrays under ``context['fields']``).
        size_x, size_y: World extent in micrometers.
        tile_size: Tile edge length in micrometers; tile counts derive from this.
        topology_x, topology_y: 'bounded' or 'toroidal' per axis.
        fields: List of {"name", "initial_value"} describing resource fields.

    Returns:
        True on success.
    """
    from src.core.tile_grid import TileGrid

    if tile_size <= 0:
        log_always(f"[ERROR] [setup_scene] tile_size must be positive, got {tile_size}")
        return False

    try:
        field_specs = _coerce_fields(fields)
    except (ValueError, json.JSONDecodeError) as e:
        log_always(f"[ERROR] [setup_scene] bad 'fields' parameter: {e}")
        return False

    nx_t = max(1, int(round(size_x / tile_size)))
    ny_t = max(1, int(round(size_y / tile_size)))

    grid = TileGrid(
        size_x=size_x,
        size_y=size_y,
        nx_t=nx_t,
        ny_t=ny_t,
        topology_x=topology_x,
        topology_y=topology_y,
    )

    for spec in field_specs:
        grid.add_field(spec["name"], float(spec.get("initial_value", 0.0)))

    context["tile_grid"] = grid
    context["fields"] = grid.fields

    # Mirror onto config for discoverability (optional; non-fatal if config absent).
    config = context.get("config")
    if config is not None:
        try:
            from src.config.config import FieldConfig, SceneConfig
            from src.core.units import Length
            config.scene = SceneConfig(
                size_x=Length(size_x, "um"),
                size_y=Length(size_y, "um"),
                tile_size=Length(tile_size, "um"),
                topology_x=topology_x,
                topology_y=topology_y,
                fields=[FieldConfig(s["name"], float(s.get("initial_value", 0.0))) for s in field_specs],
            )
        except Exception:
            pass  # config mirror is a convenience, not a requirement

    log(context, f"Scene: {nx_t}x{ny_t} tiles "
                 f"({topology_x}/{topology_y}), fields={[s['name'] for s in field_specs]}",
        prefix="[+]")
    return True
