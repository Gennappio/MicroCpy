"""
3D MicroC plots: sliced quadrant figures + an interactive Plotly viewer.

SLICES. The node cuts the 3D domain along configurable planes (parameter
``slices``, entries ``"axis:index"`` with axis x/y/z and index a solver-voxel
integer or ``mid``) and renders each plane with the SAME quadrant figure the
2D model uses (``render_quadrant_plot``): four substances on white-to-colour
gradients, threshold isolines, and the cells of that plane drawn with the
metabolic-interior / phenotype-border colouring — both encodings work on a
slice because it is an ordinary 2D drawing.

WHICH CELLS BELONG TO A SLICE (``cell_band``): a slab is one solver voxel
thick, but cells live on the finer bio grid (e.g. 2.5 cell layers per voxel
at 750 µm / 15 voxels / 20 µm cells).
- ``layer`` (default): only the single bio cell layer nearest the slab
  centre — non-overlapping circles, visually exactly the 2D figure, and every
  drawn cell maps to the plotted voxel plane via the shared coords law.
- ``slab``: every cell whose ``cell_to_solver_index`` lands in the voxel
  plane (2-3 stacked layers; circles overlap). The figure title states axis,
  voxel index and bio layer(s) so the rule is always visible.

3D VIEWER. With ``html_enabled``, every ``html_interval`` iterations a
self-contained interactive HTML is written to ``plots_dir/viewer3d/``
(``include_plotlyjs='directory'`` — plotly.min.js written once beside the
HTMLs). Cells are 3D markers; a marker has ONE colour, so metabolism and fate
cannot be shown together in 3D: the two encodings are separate toggleable
views (buttons), included per ``html_metabolism_view`` / ``html_fate_view``.
Substances appear as legend-toggleable isosurfaces at their gene-association
threshold (plus the necrosis threshold when published).
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext
from src.core.coords import cell_to_solver_index

from opencellcomms_adapters.MicroC.functions.reporting.generate_quadrant_plots import (
    DEFAULT_QUADRANTS,
    _association_threshold,
    _normalize_quadrants,
    _to_bool,
    render_quadrant_plot,
)

# axis name -> (index into a bio position tuple, index from the END of the
# (nz, ny, nx) array shape)
_AXES = ('x', 'y', 'z')

# In-plane axes per slice normal: (horizontal, vertical), as bio-tuple indices
_PLANE_AXES = {'z': (0, 1), 'y': (0, 2), 'x': (1, 2)}

_METABOLISM_KEY = [('Quiescent', 'lightgray'), ('Mixed', 'violet'),
                   ('mitoATP', 'blue'), ('glycoATP', 'green')]
_FATE_KEY = [('Necrosis', 'black'), ('Apoptosis', 'red'),
             ('Proliferation', 'lightgreen'), ('Growth arrest', 'orange'),
             ('Quiescence', 'gray')]
_INTERIOR_TO_LABEL = {'lightgray': 'Quiescent', 'violet': 'Mixed',
                      'blue': 'mitoATP', 'green': 'glycoATP'}
_BORDER_TO_LABEL = {'black': 'Necrosis', 'red': 'Apoptosis',
                    'lightgreen': 'Proliferation', 'orange': 'Growth arrest',
                    'gray': 'Quiescence'}


# --------------------------------------------------------------------------
# Pure helpers (unit-testable without matplotlib/plotly)
# --------------------------------------------------------------------------

def parse_slice_spec(spec: str, grid_dims: Tuple[int, int, int]) -> Tuple[str, int]:
    """``"z:mid"`` / ``"x:7"`` -> ('z', nz//2) / ('x', 7), clamped to the grid.

    grid_dims is (nx, ny, nz).
    """
    axis, _, index_s = str(spec).strip().lower().partition(':')
    if axis not in _AXES:
        raise ValueError(f"Slice axis must be x, y or z: {spec!r}")
    n = grid_dims[_AXES.index(axis)]
    index = n // 2 if index_s in ('', 'mid') else int(index_s)
    return axis, max(0, min(n - 1, index))


def slice_field(arr, axis: str, index: int):
    """Cut a (nz, ny, nx) field along a plane; returns a 2D array whose
    [row, col] orientation matches the plane axes of ``_PLANE_AXES``:
    z -> [y, x], y -> [z, x], x -> [z, y]."""
    if axis == 'z':
        return arr[index, :, :]
    if axis == 'y':
        return arr[:, index, :]
    return arr[:, :, index]


def slice_bio_layers(config, axis: str, index: int, cell_band: str) -> List[int]:
    """Bio cell layers belonging to a slice, per the band rule (see module
    docstring). 'layer' -> [nearest layer to the slab centre]; 'slab' -> all
    layers whose voxel index equals ``index``."""
    dom = config.domain
    cell_um = dom.cell_height.micrometers
    size_um = {'x': dom.size_x, 'y': dom.size_y, 'z': dom.size_z}[axis].micrometers
    n_axis = {'x': dom.nx, 'y': dom.ny, 'z': dom.nz}[axis]
    spacing = size_um / n_axis
    bio_n = max(1, int(size_um / cell_um))

    if cell_band == 'layer':
        return [max(0, min(bio_n - 1, int((index + 0.5) * spacing / cell_um)))]
    # 'slab': every bio layer mapping into this voxel
    return [layer for layer in range(bio_n)
            if int((layer * cell_um) / spacing) == index]


def select_band_cells(cells, config, axis: str, index: int,
                      cell_band: str = 'layer'):
    """Cells belonging to a slice, projected onto the plane.

    Returns (triples, layers): triples = [(pos2d, phenotype, cell)] ready for
    render_quadrant_plot's population=None path, with pos2d in bio in-plane
    coordinates ordered (horizontal, vertical).
    """
    layers = set(slice_bio_layers(config, axis, index, cell_band))
    axis_i = _AXES.index(axis)
    h_i, v_i = _PLANE_AXES[axis]

    triples = []
    for cell in cells:
        pos = cell.state.position
        bio_a = int(round(pos[axis_i])) if len(pos) > axis_i else 0
        if bio_a not in layers:
            continue
        pos2d = (pos[h_i] if len(pos) > h_i else 0,
                 pos[v_i] if len(pos) > v_i else 0)
        triples.append((pos2d, cell.state.phenotype, cell))
    return triples, sorted(layers)


def plane_geometry(config, axis: str) -> Tuple[Tuple[float, float], Tuple[str, str]]:
    """(plane_sizes, axis_labels) for a slice figure."""
    dom = config.domain
    unit = dom.size_x.unit
    names = {'x': f'X Position ({unit})', 'y': f'Y Position ({unit})',
             'z': f'Z Position ({unit})'}
    sizes = {'x': dom.size_x.value, 'y': dom.size_y.value, 'z': dom.size_z.value}
    h_i, v_i = _PLANE_AXES[axis]
    h_axis, v_axis = _AXES[h_i], _AXES[v_i]
    return (sizes[h_axis], sizes[v_axis]), (names[h_axis], names[v_axis])


def _cell_view_colors(cell, cell_color_fn, config):
    """(interior, border) colours for one cell via jayatilake_cell_color."""
    try:
        custom = cell_color_fn(cell=cell,
                               gene_states=getattr(cell.state, 'gene_states', {}) or {},
                               config=config)
        if custom and '|' in custom:
            interior, border = custom.split('|', 1)
            return interior, border
    except Exception:
        pass
    return 'lightgray', 'gray'


# --------------------------------------------------------------------------
# Plotly viewer
# --------------------------------------------------------------------------

def write_viewer_html(config, fields: Dict[str, Any], specs: Dict[str, Dict[str, Any]],
                      cells, cell_color_fn, isolines: Dict[str, List[Tuple[float, str]]],
                      substances_3d: List[str], metabolism_view: bool,
                      fate_view: bool, time_point: float, title_suffix: str,
                      output_file: Path) -> Optional[Path]:
    """Write the interactive 3D HTML. Returns the path, or None when plotly
    is unavailable (PNG slices are unaffected)."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("[WORKFLOW] plotly not installed - skipping 3D viewer HTML")
        return None
    import numpy as np

    dom = config.domain
    cell_um = dom.cell_height.micrometers

    def phys(p, i):
        return (float(p[i]) + 0.5) * cell_um if len(p) > i else 0.5 * cell_um

    # --- cells, grouped per category so the legend is the colour key -------
    groups: Dict[Tuple[str, str], list] = {}
    for cell in cells:
        interior, border = _cell_view_colors(cell, cell_color_fn, config)
        p = cell.state.position
        xyz = (phys(p, 0), phys(p, 1), phys(p, 2))
        if metabolism_view:
            label = _INTERIOR_TO_LABEL.get(interior, interior)
            groups.setdefault(('metabolism', label), []).append((xyz, interior))
        if fate_view:
            label = _BORDER_TO_LABEL.get(border, border)
            groups.setdefault(('fate', label), []).append((xyz, border))

    traces = []
    trace_views = []  # 'metabolism' / 'fate' / 'always'
    both_views = metabolism_view and fate_view
    for (view, label), entries in sorted(groups.items()):
        xs, ys, zs = zip(*(e[0] for e in entries))
        color = entries[0][1]
        traces.append(go.Scatter3d(
            x=xs, y=ys, z=zs, mode='markers',
            marker=dict(size=3, color=color,
                        line=dict(width=0.5, color='dimgray')),
            name=f"{label}: {len(entries)}",
            legendgroup=view,
            legendgrouptitle_text=('Metabolism' if view == 'metabolism' else 'Fate'),
            visible=True if (view == 'metabolism' or not metabolism_view) else False,
        ))
        trace_views.append(view)

    # --- substance isosurfaces at their thresholds -------------------------
    nz, ny, nx = None, None, None
    for name in substances_3d:
        field = fields.get(name)
        if field is None:
            continue
        arr = np.asarray(field)
        if arr.ndim != 3:
            continue
        nz, ny, nx = arr.shape
        xs = (np.arange(nx) + 0.5) * (dom.size_x.micrometers / nx)
        ys = (np.arange(ny) + 0.5) * (dom.size_y.micrometers / ny)
        zs = (np.arange(nz) + 0.5) * (dom.size_z.micrometers / nz)
        Z, Y, X = np.meshgrid(zs, ys, xs, indexing='ij')
        color = specs.get(name, {}).get('color', 'gray')
        for iso_value, iso_label in isolines.get(name, []):
            if not (arr.min() < iso_value < arr.max()):
                continue  # threshold outside the field: no surface exists
            traces.append(go.Isosurface(
                x=X.ravel(), y=Y.ravel(), z=Z.ravel(), value=arr.ravel(),
                isomin=iso_value, isomax=iso_value, surface_count=1,
                opacity=0.25, showscale=False,
                colorscale=[[0, color], [1, color]],
                name=f"{name} {iso_label}: {iso_value:.3g}",
                showlegend=True, visible='legendonly',
            ))
            trace_views.append('always')

    if not traces:
        print("[WORKFLOW] 3D viewer: nothing to draw - skipping HTML")
        return None

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=f"MicroC 3D at t = {time_point:.3f} {title_suffix}",
        scene=dict(
            xaxis_title='X (um)', yaxis_title='Y (um)', zaxis_title='Z (um)',
            aspectmode='data',
        ),
        legend=dict(groupclick='togglegroup'),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    if both_views:
        def mask(active):
            return [view == active or view == 'always' for view in trace_views]
        fig.update_layout(updatemenus=[dict(
            type='buttons', direction='right', x=0.0, y=1.08,
            buttons=[
                dict(label='Metabolism view', method='update',
                     args=[{'visible': mask('metabolism')}]),
                dict(label='Fate view', method='update',
                     args=[{'visible': mask('fate')}]),
            ],
        )])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_file), include_plotlyjs='directory')
    return output_file


# --------------------------------------------------------------------------
# The node
# --------------------------------------------------------------------------

@register_function(
    requires=['population', 'simulator'],
    display_name="Generate 3D Plots",
    description="3D MicroC visualization: slices the volume along configurable "
                "planes and renders each as the standard four-substance quadrant "
                "figure (cells with metabolic interiors + fate borders), plus an "
                "interactive Plotly HTML viewer (rotate/zoom; metabolism and "
                "fate as separate toggleable views, substances as threshold "
                "isosurfaces). See the node source for the slice band rule.",
    category="FINALIZATION",
    parameters=[
        {"name": "slices", "type": "LIST",
         "description": "Slice planes, entries 'axis:index' with axis x/y/z and "
                        "index a solver-voxel integer or 'mid'. Each entry "
                        "renders one quadrant-style figure per iteration.",
         "default": ["z:mid", "y:mid", "x:mid"]},
        {"name": "quadrant_substances", "type": "DICT",
         "description": "Substance -> gradient spec, exactly as on the 2D "
                        "quadrant node: a colour string (auto-range) or "
                        "{color, vmin, vmax}. Entry order = TL, TR, BL, BR. "
                        "Empty = Lactate/Glucose/TGFA/H.",
         "default": {}},
        {"name": "cell_band", "type": "STRING",
         "description": "Cells drawn on a slice: 'layer' = the single bio cell "
                        "layer nearest the slab centre (non-overlapping, like "
                        "the 2D figure); 'slab' = every cell layer mapping into "
                        "the voxel plane (2-3 layers, circles overlap).",
         "default": "layer"},
        {"name": "show_isolines", "type": "BOOL",
         "description": "Threshold isolines on the slice figures.", "default": True},
        {"name": "show_cells", "type": "BOOL",
         "description": "Cell overlay on the slice figures.", "default": True},
        {"name": "show_metabolism_colors", "type": "BOOL",
         "description": "Metabolic interior colouring on slices.", "default": True},
        {"name": "show_fate_colors", "type": "BOOL",
         "description": "Phenotype border colouring on slices.", "default": True},
        {"name": "show_legends", "type": "BOOL",
         "description": "Cell-colour key on slices.", "default": True},
        {"name": "show_gradient_legends", "type": "BOOL",
         "description": "Per-quadrant gradient bars on slices.", "default": True},
        {"name": "autorange", "type": "BOOL",
         "description": "Ignore fixed vmin/vmax and scale every quadrant to the "
                        "slice's min/max.", "default": False},
        {"name": "plot_interval", "type": "INT",
         "description": "Slice PNGs every N iterations.", "default": 1},
        {"name": "html_enabled", "type": "BOOL",
         "description": "Write the interactive 3D HTML viewer.", "default": True},
        {"name": "html_interval", "type": "INT",
         "description": "HTML viewer every N iterations (files are ~1-3 MB).",
         "default": 10},
        {"name": "substances_3d", "type": "LIST",
         "description": "Substances shown as threshold isosurfaces in the HTML "
                        "viewer (colours from Quadrant Substances when listed "
                        "there).",
         "default": ["Oxygen", "Glucose"]},
        {"name": "html_metabolism_view", "type": "BOOL",
         "description": "Include the metabolism-coloured cell view in the HTML.",
         "default": True},
        {"name": "html_fate_view", "type": "BOOL",
         "description": "Include the fate-coloured cell view in the HTML (with "
                        "both views, buttons toggle between them - a 3D marker "
                        "has one colour, so the encodings cannot overlap).",
         "default": True},
        {"name": "plot_name_suffix", "type": "STRING",
         "description": "Suffix appended to filenames and titles.", "default": ""},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def generate_3d_plots(
    env: BiologicalContext,
    slices: Union[List[str], None] = None,
    quadrant_substances: Union[Dict[str, Any], None] = None,
    cell_band: str = "layer",
    show_isolines: bool = True,
    show_cells: bool = True,
    show_metabolism_colors: bool = True,
    show_fate_colors: bool = True,
    show_legends: bool = True,
    show_gradient_legends: bool = True,
    autorange: bool = False,
    plot_interval: int = 1,
    html_enabled: bool = True,
    html_interval: int = 10,
    substances_3d: Union[List[str], None] = None,
    html_metabolism_view: bool = True,
    html_fate_view: bool = True,
    plot_name_suffix: str = "",
    **kwargs
) -> bool:
    """Render sliced quadrant figures + the interactive 3D viewer."""
    import numpy as np

    ctx = env.raw_context
    population = env.cells.raw
    simulator = env.environment.raw_simulator
    config = env.config
    results = ctx.get('results', {})

    if not simulator or not population or not config:
        print("[WARNING] Simulator/population/config not available - skipping 3D plots")
        return False
    if getattr(config.domain, 'dimensions', 2) != 3:
        print("[WORKFLOW] generate_3d_plots: domain is not 3D - nothing to do")
        return True

    iteration = ctx.get('loop_iteration', 0) or ctx.get('macrostep', env.step)
    plot_interval = int(plot_interval)
    html_interval = max(1, int(html_interval))
    do_png = not (plot_interval > 1 and iteration % plot_interval != 0)
    do_html = _to_bool(html_enabled) and iteration % html_interval == 0
    if not do_png and not do_html:
        return True

    raw = dict(quadrant_substances or {}) or dict(DEFAULT_QUADRANTS)
    if len(raw) != 4:
        print(f"[WORKFLOW] 3D plots need exactly 4 quadrant substances, got "
              f"{list(raw)} - skipping")
        return False
    specs = _normalize_quadrants(raw, _to_bool(autorange))
    missing = [s for s in specs if s not in simulator.state.substances]
    if missing:
        print(f"[WORKFLOW] Substances not found in simulator: {missing} - skipping 3D plots")
        return False

    fields = {name: simulator.state.substances[name].concentrations
              for name in specs}

    # Isolines per substance (association + necrosis), as on the 2D node
    isolines: Dict[str, List[Tuple[float, str]]] = {}
    if _to_bool(show_isolines):
        for name in specs:
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
    marker = f"ITER_{int(iteration):03d}{plot_name_suffix}"
    base_suffix = f"[Iteration {iteration}{' ' + plot_name_suffix.strip('_') if plot_name_suffix else ''}]"

    if 'plots_dir' in ctx:
        output_path = Path(ctx['plots_dir'])
    else:
        output_path = Path('results/plots')

    from opencellcomms_adapters.MicroC.functions.reporting.cell_colors import jayatilake_cell_color

    ok = True
    if do_png:
        grid_dims = (config.domain.nx, config.domain.ny, config.domain.nz)
        for spec in (list(slices) if slices else ["z:mid", "y:mid", "x:mid"]):
            try:
                axis, index = parse_slice_spec(spec, grid_dims)
            except (ValueError, TypeError) as e:
                print(f"[WORKFLOW] Bad slice spec {spec!r}: {e} - skipped")
                continue
            try:
                plane_fields = {name: slice_field(np.asarray(arr), axis, index)
                                for name, arr in fields.items()}
                triples, layers = select_band_cells(
                    population.state.cells.values(), config, axis, index,
                    cell_band=str(cell_band))
                plane_sizes, axis_labels = plane_geometry(config, axis)
                layer_note = f"{axis}={index} (cells: bio layer {layers})"
                out = output_path / "heatmaps" / (
                    f"quadrants_heatmap_t{current_time:.3f}_{marker}_slice_{axis}{index:02d}.png")
                render_quadrant_plot(
                    config, plane_fields, specs, triples, jayatilake_cell_color,
                    None, isolines, current_time,
                    f"{base_suffix} slice {layer_note}", out,
                    show_cells=_to_bool(show_cells),
                    show_metabolism_colors=_to_bool(show_metabolism_colors),
                    show_fate_colors=_to_bool(show_fate_colors),
                    show_legends=_to_bool(show_legends),
                    show_gradient_legends=_to_bool(show_gradient_legends),
                    plane_sizes=plane_sizes, axis_labels=axis_labels,
                )
                print(f"[WORKFLOW] 3D slice figure written: {out.name}")
            except Exception as e:
                print(f"[WORKFLOW] Error rendering slice {spec!r}: {e}")
                import traceback
                traceback.print_exc()
                ok = False

    if do_html:
        try:
            html_out = output_path / "viewer3d" / (
                f"spheroid3d_t{current_time:.3f}_{marker}.html")
            written = write_viewer_html(
                config, fields, specs, list(population.state.cells.values()),
                jayatilake_cell_color, isolines,
                list(substances_3d) if substances_3d else ["Oxygen", "Glucose"],
                _to_bool(html_metabolism_view), _to_bool(html_fate_view),
                current_time, base_suffix, html_out)
            if written:
                print(f"[WORKFLOW] 3D viewer written: {written}")
        except Exception as e:
            print(f"[WORKFLOW] Error writing 3D viewer: {e}")
            import traceback
            traceback.print_exc()
            ok = False

    return ok
