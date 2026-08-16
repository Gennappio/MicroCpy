"""
Compact four-substance quadrant plot (MicroC-paper style).

One square figure shows the whole domain split into four quadrants; each
quadrant renders ONE substance's concentration field over that quarter of the
domain, on a white-to-colour gradient specific to that substance (e.g. Lactate
orange, Glucose teal, TGFA yellow, H magenta — as in the Jayatilake MicroC
figure). Cells are drawn on top across the whole domain with the usual
metabolic-interior / phenotype-border colouring.

Each quadrant carries its OWN gradient legend showing that substance's colour
range, and any threshold isolines (gene-association thresholds, necrosis
thresholds published by mark_necrotic_cells) are drawn only inside the owning
substance's quadrant and labelled with the substance name so there is no
ambiguity about which field they belong to.

The colour range per substance is either automatic (the field's min/max at
that iteration) or FIXED via {"color", "vmin", "vmax"} in the
quadrant_substances dict. Fixed ranges keep shades comparable across
iterations and give a uniform field its proportional shade — with auto-range
a uniform field always renders at the degenerate midpoint regardless of its
level.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


# Quadrant order is the dict entry order: top-left, top-right,
# bottom-left, bottom-right — matching the reference MicroC figure.
DEFAULT_QUADRANTS: Dict[str, str] = {
    "Lactate": "darkorange",
    "Glucose": "teal",
    "TGFA": "gold",
    "H": "mediumvioletred",
}

_PHENOTYPE_BORDER_COLORS = {
    'Proliferation': 'lightgreen',
    'proliferation': 'lightgreen',
    'Quiescence': 'gray',
    'Necrosis': 'black',
    'Apoptosis': 'red',
    'Growth_Arrest': 'orange',
    'growth_arrest': 'orange',
}


def _normalize_quadrants(raw: Dict[str, Any], autorange: bool) -> Dict[str, Dict[str, Any]]:
    """Normalize quadrant_substances values to {"color", "vmin", "vmax"} specs.

    Each raw value is either a colour string (auto-range) or a dict
    {"color", "vmin", "vmax"} with optional fixed bounds. With autorange=True
    any fixed bounds are ignored and every quadrant scales to its field's
    min/max for that iteration."""
    def _bound(value):
        if autorange or value is None or value == "":
            return None
        return float(value)

    quadrants = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            quadrants[str(key)] = {"color": str(value.get("color", "gray")),
                                   "vmin": _bound(value.get("vmin")),
                                   "vmax": _bound(value.get("vmax"))}
        else:
            quadrants[str(key)] = {"color": str(value), "vmin": None, "vmax": None}
    return quadrants


def _association_threshold(config, substance_name: str) -> Optional[float]:
    """Gene-association threshold for a substance (same lookup as AutoPlotter)."""
    if not hasattr(config, 'associations') or not hasattr(config, 'thresholds'):
        return None
    gene_input = config.associations.get(substance_name)
    if gene_input and gene_input in config.thresholds:
        return config.thresholds[gene_input].threshold
    return None


def _clip_contour(contour_set, clip_rect):
    """Clip a contour to a quadrant rectangle across matplotlib versions."""
    try:
        artists = list(contour_set.collections)
    except AttributeError:
        artists = [contour_set]
    for artist in artists:
        artist.set_clip_path(clip_rect)


def _label_point_in_quadrant(contour_set, bounds):
    """Pick the contour vertex inside (x0, y0, x1, y1) nearest the quadrant
    centre, so the label sits well away from quadrant boundaries."""
    x0, y0, x1, y1 = bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    inside = []
    for path in contour_set.get_paths():
        for vx, vy in path.vertices:
            if x0 <= vx <= x1 and y0 <= vy <= y1:
                inside.append((vx, vy))
    if not inside:
        return None
    return min(inside, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)


def render_quadrant_plot(config, fields: Dict[str, Any], specs: Dict[str, Dict[str, Any]],
                         cell_data: List[Tuple[Any, str]], cell_color_fn,
                         population, isolines: Dict[str, List[Tuple[float, str]]],
                         time_point: float, title_suffix: str,
                         output_file: Path) -> Path:
    """Render the 2x2 quadrant figure. Pure plotting — no context access.

    ``specs`` maps substance name -> {"color", "vmin", "vmax"}; a None bound
    falls back to the field's own min/max (auto-range). A fixed range keeps
    the colour scale stable across iterations and gives a uniform field a
    proportional shade instead of a washed-out auto-scaled one."""
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.colors import LinearSegmentedColormap

    size_x = config.domain.size_x.value
    size_y = config.domain.size_y.value
    mid_x, mid_y = size_x / 2.0, size_y / 2.0

    # (x0, y0, x1, y1) of each quadrant, in dict-entry order TL, TR, BL, BR
    quadrant_bounds = [
        (0.0, mid_y, mid_x, size_y),
        (mid_x, mid_y, size_x, size_y),
        (0.0, 0.0, mid_x, mid_y),
        (mid_x, 0.0, size_x, mid_y),
    ]
    # Where each quadrant's legend sits (axes fraction): pushed toward the
    # outer corner so the tumour at the centre stays unobstructed.
    legend_positions = [
        (0.05, 0.86), (0.62, 0.86),
        (0.05, 0.06), (0.62, 0.06),
    ]

    fig, ax = plt.subplots(figsize=(11, 11))
    ax.set_xlim(0, size_x)
    ax.set_ylim(0, size_y)
    ax.set_aspect('equal')

    substance_names = list(specs.keys())
    for idx, name in enumerate(substance_names):
        concentrations = np.asarray(fields[name])
        if concentrations.ndim == 3:
            concentrations = concentrations[concentrations.shape[0] // 2, :, :]

        spec = specs[name]
        fixed_min, fixed_max = spec.get('vmin'), spec.get('vmax')
        vmin = fixed_min if fixed_min is not None else float(concentrations.min())
        vmax = fixed_max if fixed_max is not None else float(concentrations.max())
        if vmax - vmin < 1e-10:  # degenerate range (auto on a uniform field)
            eps = max(abs(vmin) * 1e-6, 1e-10)
            vmin, vmax = vmin - eps, vmax + eps

        cmap = LinearSegmentedColormap.from_list(f'white_to_{name}',
                                                 ['white', spec['color']])

        x0, y0, x1, y1 = quadrant_bounds[idx]
        clip_rect = patches.Rectangle((x0, y0), x1 - x0, y1 - y0,
                                      transform=ax.transData)
        im = ax.imshow(concentrations, cmap=cmap, origin='lower',
                       extent=[0, size_x, 0, size_y], vmin=vmin, vmax=vmax)
        im.set_clip_path(clip_rect)

        # Threshold isolines for THIS substance, clipped to its quadrant and
        # labelled with the substance name.
        x_coords = np.linspace(0, size_x, concentrations.shape[1])
        y_coords = np.linspace(0, size_y, concentrations.shape[0])
        X, Y = np.meshgrid(x_coords, y_coords)
        for iso_value, iso_label in isolines.get(name, []):
            style = '--' if 'Necrosis' in iso_label else '-'
            cs = ax.contour(X, Y, concentrations, levels=[iso_value],
                            colors=['red'], linewidths=1.5, linestyles=style)
            _clip_contour(cs, clip_rect)
            # Label manually at a point inside this quadrant so the label
            # cannot land in another substance's quadrant.
            label_at = _label_point_in_quadrant(cs, (x0, y0, x1, y1))
            if label_at:
                ax.clabel(cs, inline=True, fontsize=8, manual=[label_at],
                          fmt=f'{name} {iso_label}: {iso_value:.3g}')

        # Per-quadrant gradient legend with the substance's min/max
        lx, ly = legend_positions[idx]
        cax = ax.inset_axes([lx, ly, 0.28, 0.035])
        gradient = np.linspace(0, 1, 256).reshape(1, -1)
        cax.imshow(gradient, aspect='auto', cmap=cmap)
        cax.set_yticks([])
        cax.set_xticks([0, 255])
        cax.set_xticklabels([f'{vmin:.3g}', f'{vmax:.3g}'], fontsize=8)
        cax.set_title(f'{name} (mM)', fontsize=11, fontweight='bold', pad=2)
        for spine in cax.spines.values():
            spine.set_linewidth(0.8)

    # Cells drawn over the whole domain, MicroC colouring
    cell_diameter = config.domain.cell_height.value
    spacing = config.domain.cell_height.value
    for position, phenotype in cell_data:
        x, y = position[0], position[1]
        phys_x, phys_y = (x + 0.5) * spacing, (y + 0.5) * spacing

        interior_color, border_color = 'lightgray', _PHENOTYPE_BORDER_COLORS.get(phenotype, 'gray')
        if cell_color_fn and population:
            try:
                cell = population.get_cell_at_position((x, y))
                if cell is None:
                    cell = population.get_cell_at_position(position)
                if cell is not None:
                    gene_states = getattr(cell.state, 'gene_states', {}) or {}
                    custom = cell_color_fn(cell=cell, gene_states=gene_states,
                                           config=population.config)
                    if custom and '|' in custom:
                        interior_color, border_color = custom.split('|', 1)
            except Exception:
                pass
        circle = patches.Circle((phys_x, phys_y), cell_diameter / 2,
                                facecolor=interior_color, edgecolor=border_color,
                                alpha=0.9, linewidth=1.5, fill=True)
        ax.add_patch(circle)

    # Quadrant dividers and outer frame, as in the reference figure
    ax.axvline(mid_x, color='black', linewidth=2)
    ax.axhline(mid_y, color='black', linewidth=2)
    for spine in ax.spines.values():
        spine.set_linewidth(3)
        spine.set_color('black')

    ax.set_xlabel(f'X Position ({config.domain.size_x.unit})')
    ax.set_ylabel(f'Y Position ({config.domain.size_y.unit})')
    ax.set_title(f'{" / ".join(substance_names)} at t = {time_point:.3f} {title_suffix}',
                 fontsize=13, pad=12)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return output_file


@register_function(
    requires=['population', 'simulator'],
    display_name="Generate Quadrant Plots",
    description="Compact 2x2 view: the domain is split into four quadrants, each "
                "showing one substance's field on its own white-to-colour gradient "
                "(dict order = top-left, top-right, bottom-left, bottom-right). "
                "Each quadrant gets its own min/max legend; threshold isolines are "
                "drawn in the owning substance's quadrant and labelled with the "
                "substance name.",
    category="FINALIZATION",
    parameters=[
        {"name": "quadrant_substances", "type": "DICT",
         "description": "Substance -> gradient spec. Exactly 4 entries; entry order "
                        "places them top-left, top-right, bottom-left, bottom-right. "
                        "Value is either a matplotlib colour string (colour scale "
                        "auto-ranges to the field's min/max each iteration) or a dict "
                        "{color, vmin, vmax} fixing the colour range - a fixed range "
                        "keeps shades comparable across iterations and shows a "
                        "proportional shade even when the field is uniform. vmin/vmax "
                        "may be given individually; an omitted bound stays automatic. "
                        "Empty = Lactate/Glucose/TGFA/H as in the MicroC reference "
                        "figure.",
         "default": {}},
        {"name": "autorange", "type": "BOOL",
         "description": "Ignore any fixed vmin/vmax in Quadrant Substances and scale "
                        "every quadrant to its field's min/max at each iteration. "
                        "Lets you flip between fixed and automatic colour scales "
                        "without editing the dict.",
         "default": False},
        {"name": "plot_interval", "type": "INT",
         "description": "Plot every N iterations (1 = every iteration).",
         "default": 1},
        {"name": "plot_name_suffix", "type": "STRING",
         "description": "Suffix appended to the plot filename and title.",
         "default": ""},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def generate_quadrant_plots(
    env: BiologicalContext,
    quadrant_substances: Union[Dict[str, Any], None] = None,
    autorange: bool = False,
    plot_interval: int = 1,
    plot_name_suffix: str = "",
    **kwargs
) -> bool:
    """Generate the compact four-substance quadrant plot for this iteration."""
    ctx = env.raw_context
    population = env.cells.raw
    simulator = env.environment.raw_simulator
    config = env.config
    results = ctx.get('results', {})

    iteration = ctx.get('loop_iteration', 0)
    if iteration == 0:
        iteration = ctx.get('macrostep', env.step)

    plot_interval = int(plot_interval)
    if plot_interval > 1 and iteration % plot_interval != 0:
        print(f"[WORKFLOW] Skipping quadrant plot for iteration {iteration} "
              f"(plot_interval={plot_interval})")
        return True

    if not simulator or not population or not config:
        print("[WARNING] Simulator/population/config not available - skipping quadrant plot")
        return False

    raw = dict(quadrant_substances or {}) or dict(DEFAULT_QUADRANTS)
    if len(raw) != 4:
        print(f"[WORKFLOW] Quadrant plot needs exactly 4 substances, got "
              f"{list(raw)} - skipping")
        return False

    if isinstance(autorange, str):
        autorange = autorange.strip().lower() in ('true', '1', 'yes')
    quadrants = _normalize_quadrants(raw, bool(autorange))
    missing = [s for s in quadrants if s not in simulator.state.substances]
    if missing:
        print(f"[WORKFLOW] Substances not found in simulator: {missing} - skipping quadrant plot")
        return False

    if 'plots_dir' in ctx:
        output_path = Path(ctx['plots_dir'])
    elif getattr(config, 'plots_dir', None):
        output_path = Path(config.plots_dir)
    else:
        output_path = Path('results/plots')

    fields = {name: simulator.state.substances[name].concentrations
              for name in quadrants}

    # Isolines: gene-association threshold + necrosis thresholds, per substance
    isolines: Dict[str, List[Tuple[float, str]]] = {}
    for name in quadrants:
        entries: List[Tuple[float, str]] = []
        threshold = _association_threshold(config, name)
        if threshold is not None:
            entries.append((threshold, 'threshold'))
        necrosis = results.get('necrosis_thresholds', {}).get(name)
        if necrosis is not None:
            entries.append((necrosis, 'Necrosis'))
        if entries:
            isolines[name] = entries

    time_points = results.get('time', [])
    current_time = time_points[-1] if time_points else getattr(simulator, 'current_time', 0.0) or 0.0

    marker = f"ITER_{iteration:03d}{plot_name_suffix}"
    title_suffix = f"[Iteration {iteration}{' ' + plot_name_suffix.strip('_') if plot_name_suffix else ''}]"
    output_file = output_path / "heatmaps" / f"quadrants_heatmap_t{current_time:.3f}_{marker}.png"

    print(f"[WORKFLOW] Generating quadrant plot for iteration {iteration} "
          f"({', '.join(quadrants)})")

    try:
        from opencellcomms_adapters.MicroC.functions.reporting.cell_colors import jayatilake_cell_color
        filepath = render_quadrant_plot(
            config, fields, quadrants,
            population.get_cell_positions(), jayatilake_cell_color, population,
            isolines, current_time, title_suffix, output_file,
        )
        print(f"[WORKFLOW] Quadrant plot written: {filepath}")
        return True
    except Exception as e:
        print(f"[WORKFLOW] Error generating quadrant plot: {e}")
        import traceback
        traceback.print_exc()
        return False
