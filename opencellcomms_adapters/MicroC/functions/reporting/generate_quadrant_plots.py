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

Every overlay is individually switchable: show_cells, show_metabolism_colors,
show_fate_colors, show_legends, show_gradient_legends and show_isolines each
remove one layer (the cell overlay, the metabolic interior colouring, the
phenotype border colouring, the cell-colour key, the per-quadrant gradient
bars, the threshold isolines) for clean figures.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


def _to_bool(val) -> bool:
    """Coerce a value to bool, tolerating GUI strings ("true"/"false")."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'on', 'yes')
    return bool(val)


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
                         output_file: Path, *, show_cells: bool = True,
                         show_metabolism_colors: bool = True,
                         show_fate_colors: bool = True,
                         show_legends: bool = True,
                         show_gradient_legends: bool = True) -> Path:
    """Render the 2x2 quadrant figure. Pure plotting — no context access.

    ``specs`` maps substance name -> {"color", "vmin", "vmax"}; a None bound
    falls back to the field's own min/max (auto-range). A fixed range keeps
    the colour scale stable across iterations and gives a uniform field a
    proportional shade instead of a washed-out auto-scaled one.

    The ``show_*`` flags each remove one overlay: the cell overlay, the
    metabolic interior colouring (off = lightgray interiors), the phenotype
    border colouring (off = gray borders), the cell-colour key right of the
    plot, and the per-quadrant gradient bars. A legend is drawn only for a
    colouring actually in effect, so the key never describes a hidden layer."""
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
            # zorder 5/6: above the cells (zorder 2/3) so the contour stays
            # visible through the spheroid; legends are separate artists drawn
            # on top regardless.
            cs = ax.contour(X, Y, concentrations, levels=[iso_value],
                            colors=['red'], linewidths=2.5, linestyles=style,
                            zorder=5)
            _clip_contour(cs, clip_rect)
            # Label placed by hand at a contour vertex inside this quadrant,
            # nudged toward the quadrant centre. Deliberately NOT clabel
            # (inline=True cuts the line under the label — a short clipped
            # arc, e.g. an oxygen-threshold loop hugging the domain centre,
            # would be swallowed entirely and the contour become invisible).
            label_at = _label_point_in_quadrant(cs, (x0, y0, x1, y1))
            if label_at:
                cx_q, cy_q = (x0 + x1) / 2, (y0 + y1) / 2
                tx = label_at[0] + 0.25 * (cx_q - label_at[0])
                ty = label_at[1] + 0.25 * (cy_q - label_at[1])
                ax.text(tx, ty, f'{name} {iso_label}: {iso_value:.3g}',
                        color='red', fontsize=11, ha='center', va='center',
                        zorder=6,
                        bbox=dict(boxstyle='round,pad=0.25', facecolor='white',
                                  alpha=0.75, edgecolor='none'))

        # Per-quadrant gradient legend with the substance's min/max
        if show_gradient_legends:
            lx, ly = legend_positions[idx]
            cax = ax.inset_axes([lx, ly, 0.28, 0.035])
            gradient = np.linspace(0, 1, 256).reshape(1, -1)
            cax.imshow(gradient, aspect='auto', cmap=cmap)
            cax.set_yticks([])
            cax.set_xticks([0, 255])
            cax.set_xticklabels([f'{vmin:.3g}', f'{vmax:.3g}'], fontsize=8)
            cax.set_title(f'{name} (mM)', fontsize=11, fontweight='bold', pad=2)
            # With a fixed range the ticks show the scale, not the data — add the
            # field's actual extremes so consumption/production stays readable.
            if fixed_min is not None or fixed_max is not None:
                cax.set_xlabel(f'now: {float(concentrations.min()):.3g} – '
                               f'{float(concentrations.max()):.3g}',
                               fontsize=7, labelpad=2)
            for spine in cax.spines.values():
                spine.set_linewidth(0.8)

    # Cells drawn over the whole domain, MicroC colouring. Tally the colours
    # actually drawn so the legends can carry per-category counts.
    #
    # Colour comes from EACH CELL OBJECT DIRECTLY — never from a position
    # lookup (get_cell_at_position). A position lookup returns the first cell
    # matching the coordinate, so any representation drift or co-location
    # colours a cell with a NEIGHBOUR's phenotype; this once inflated the
    # plot's Necrosis count far above the fate census.
    cell_diameter = config.domain.cell_height.value
    spacing = config.domain.cell_height.value
    interior_counts: Dict[str, int] = {}
    border_counts: Dict[str, int] = {}
    if not show_cells:
        draw_items = []
    elif population is not None:
        draw_items = [(c.state.position, c.state.phenotype, c)
                      for c in population.state.cells.values()]
    else:
        draw_items = [(position, phenotype, None) for position, phenotype in cell_data]
    for position, phenotype, cell in draw_items:
        x, y = position[0], position[1]
        phys_x, phys_y = (x + 0.5) * spacing, (y + 0.5) * spacing

        interior_color, border_color = 'lightgray', _PHENOTYPE_BORDER_COLORS.get(phenotype, 'gray')
        if cell_color_fn and cell is not None:
            try:
                gene_states = getattr(cell.state, 'gene_states', {}) or {}
                custom = cell_color_fn(cell=cell, gene_states=gene_states,
                                       config=population.config)
                if custom and '|' in custom:
                    interior_color, border_color = custom.split('|', 1)
            except Exception:
                pass
        # Disabled colourings collapse to the neutral colours, so the flag
        # removes the encoding without removing the cells themselves.
        if not show_metabolism_colors:
            interior_color = 'lightgray'
        if not show_fate_colors:
            border_color = 'gray'
        interior_counts[interior_color] = interior_counts.get(interior_color, 0) + 1
        border_counts[border_color] = border_counts.get(border_color, 0) + 1
        # Fate-marked cells (non-gray border) get a thicker ring and draw on
        # top of quiescent neighbours so sparse marks stay visible.
        marked = border_color != 'gray'
        circle = patches.Circle((phys_x, phys_y), cell_diameter / 2,
                                facecolor=interior_color, edgecolor=border_color,
                                alpha=0.9, linewidth=2.5 if marked else 1.2,
                                fill=True, zorder=3 if marked else 2)
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

    # Cell-colour key, right of the plot. Fixed entries mirroring
    # jayatilake_cell_color: interior = metabolic mode, border = phenotype.
    # Each legend appears only when its colouring is actually drawn, so the
    # key never describes a layer the show_* flags removed.
    if show_legends and show_cells:
        from matplotlib.lines import Line2D

        def _cell_marker(face, edge):
            return Line2D([], [], marker='o', linestyle='', markersize=10,
                          markerfacecolor=face, markeredgecolor=edge, markeredgewidth=2)

        interior_legend = None
        if show_metabolism_colors:
            interior_key = [('Quiescent', 'lightgray'), ('Mixed', 'violet'),
                            ('mitoATP', 'blue'), ('glycoATP', 'green')]
            interior_handles = [_cell_marker(c, 'gray') for _, c in interior_key]
            interior_labels = [f'{label}: {interior_counts.get(c, 0)}'
                               for label, c in interior_key]
            interior_legend = ax.legend(interior_handles, interior_labels,
                                        title='Interior — metabolism',
                                        loc='upper left', bbox_to_anchor=(1.02, 1.0),
                                        fontsize=9, title_fontsize=10, frameon=True,
                                        edgecolor='black', framealpha=0.95)
            interior_legend.get_title().set_fontweight('bold')

        if show_fate_colors:
            if interior_legend is not None:
                ax.add_artist(interior_legend)
            # Listed in priority order: necrosis wins over apoptosis, apoptosis over
            # proliferation (enforced by the fate_update behaviour, shown here as a key).
            border_key = [('Necrosis', 'black'), ('Apoptosis', 'red'),
                          ('Proliferation', 'lightgreen'), ('Growth arrest', 'orange'),
                          ('Quiescence', 'gray')]
            border_handles = [_cell_marker('white', c) for _, c in border_key]
            border_labels = [f'{label}: {border_counts.get(c, 0)}'
                             for label, c in border_key]
            border_legend = ax.legend(border_handles, border_labels,
                                      title='Border — phenotype',
                                      loc='upper left', bbox_to_anchor=(1.02, 0.72),
                                      fontsize=9, title_fontsize=10, frameon=True,
                                      edgecolor='black', framealpha=0.95)
            border_legend.get_title().set_fontweight('bold')
        ax.text(1.02, 0.44, f'Total cells: {len(draw_items)}',
                transform=ax.transAxes, fontsize=10, fontweight='bold',
                verticalalignment='top')
        if show_fate_colors:
            ax.text(1.02, 0.39, 'priority:\nNecrosis > Apoptosis\n> Proliferation',
                    transform=ax.transAxes, fontsize=8, style='italic',
                    verticalalignment='top')

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
                "substance name. Every overlay (cells, metabolism colours, fate "
                "colours, legends, gradient bars, isolines) has its own show_* "
                "switch for clean figures.",
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
        {"name": "show_isolines", "type": "BOOL",
         "description": "Draw the threshold isolines (gene-association thresholds "
                        "and necrosis thresholds) in each substance's quadrant, on "
                        "top of the cells. Off = clean fields only.",
         "default": True},
        {"name": "show_cells", "type": "BOOL",
         "description": "Draw the cells over the substance fields. Off = fields "
                        "only; the cell legends and counts disappear with them.",
         "default": True},
        {"name": "show_metabolism_colors", "type": "BOOL",
         "description": "Colour each cell's interior by metabolic mode (green "
                        "glycoATP / blue mitoATP / violet mixed / lightgray none). "
                        "Off = neutral lightgray interiors and no metabolism legend.",
         "default": True},
        {"name": "show_fate_colors", "type": "BOOL",
         "description": "Colour each cell's border by marked phenotype (black "
                        "Necrosis / red Apoptosis / lightgreen Proliferation / "
                        "orange Growth arrest / gray Quiescence). Off = neutral "
                        "gray borders and no phenotype legend.",
         "default": True},
        {"name": "show_legends", "type": "BOOL",
         "description": "Draw the cell-colour key right of the plot (metabolism "
                        "and phenotype legends with per-category counts, total "
                        "cell count, fate priority note). Off = plot area only.",
         "default": True},
        {"name": "show_gradient_legends", "type": "BOOL",
         "description": "Draw each quadrant's white-to-colour gradient bar with "
                        "its min/max labels. Off = no in-plot colour scales.",
         "default": True},
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
    show_isolines: bool = True,
    show_cells: bool = True,
    show_metabolism_colors: bool = True,
    show_fate_colors: bool = True,
    show_legends: bool = True,
    show_gradient_legends: bool = True,
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

    show_cells = _to_bool(show_cells)
    show_metabolism_colors = _to_bool(show_metabolism_colors)
    show_fate_colors = _to_bool(show_fate_colors)
    show_legends = _to_bool(show_legends)
    show_gradient_legends = _to_bool(show_gradient_legends)

    # Isolines: gene-association threshold + necrosis thresholds, per substance
    if isinstance(show_isolines, str):
        show_isolines = show_isolines.strip().lower() in ('true', '1', 'yes')
    isolines: Dict[str, List[Tuple[float, str]]] = {}
    for name in quadrants if show_isolines else ():
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

    hidden = [label for label, shown in [('cells', show_cells),
                                         ('metabolism colours', show_metabolism_colors),
                                         ('fate colours', show_fate_colors),
                                         ('legends', show_legends),
                                         ('gradient legends', show_gradient_legends),
                                         ('isolines', show_isolines)] if not shown]
    print(f"[WORKFLOW] Generating quadrant plot for iteration {iteration} "
          f"({', '.join(quadrants)})"
          + (f" — hidden: {', '.join(hidden)}" if hidden else ""))

    try:
        from opencellcomms_adapters.MicroC.functions.reporting.cell_colors import jayatilake_cell_color
        filepath = render_quadrant_plot(
            config, fields, quadrants,
            population.get_cell_positions(), jayatilake_cell_color, population,
            isolines, current_time, title_suffix, output_file,
            show_cells=show_cells,
            show_metabolism_colors=show_metabolism_colors,
            show_fate_colors=show_fate_colors,
            show_legends=show_legends,
            show_gradient_legends=show_gradient_legends,
        )
        print(f"[WORKFLOW] Quadrant plot written: {filepath}")
        return True
    except Exception as e:
        print(f"[WORKFLOW] Error generating quadrant plot: {e}")
        import traceback
        traceback.print_exc()
        return False
