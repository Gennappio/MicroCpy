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
HTMLs). The scene is the FIXED domain box — axis ranges pinned to the domain
size with a proportional aspect ratio and a faint wireframe — never
autoranged to the occupied region. Cells are true-size spheres (radius
``cell_height/2`` µm, one instanced Mesh3d per category) so their scale
matches the 2D circles; a sphere has ONE colour, so metabolism and fate
cannot be shown together in 3D: the two encodings are separate toggleable
views (buttons), included per ``html_metabolism_view`` / ``html_fate_view``.
Every configured substance threshold (gene-association + necrosis) is a
legend-toggleable isosurface from iteration 1 — a threshold outside the
field's current range renders nothing and is named "... (not crossed)".
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from src.workflow.decorators import register_function
from src.core.coords import centred_um
from src.biology.context import BiologicalContext
from src.core.coords import cell_to_solver_index

from opencellcomms_adapters.MicroC.functions.reporting.generate_quadrant_plots import (
    ATP_GATE_KEY,
    DEFAULT_QUADRANTS,
    _association_threshold,
    _normalize_quadrants,
    _to_bool,
    atp_gate_payload,
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

def _sphere_template(kind: str = 'uv'):
    """Unit-sphere mesh (vertices, faces) used to instance one Mesh3d per
    cell category. 'uv': 8 segments x 6 rings = 42 verts / 80 triangles;
    'octa': octahedron (6 verts / 8 triangles) for very populous traces."""
    import numpy as np
    if kind == 'octa':
        verts = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0],
                          [0, -1, 0], [0, 0, 1], [0, 0, -1]], dtype=float)
        faces = np.array([[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
                          [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]])
        return verts, faces
    n_seg, n_rings = 8, 6
    verts = [(0.0, 0.0, 1.0)]
    for r in range(1, n_rings):
        phi = np.pi * r / n_rings
        for s in range(n_seg):
            theta = 2 * np.pi * s / n_seg
            verts.append((np.sin(phi) * np.cos(theta),
                          np.sin(phi) * np.sin(theta), np.cos(phi)))
    verts.append((0.0, 0.0, -1.0))

    def ring(r, s):
        return 1 + (r - 1) * n_seg + s % n_seg

    faces = []
    for s in range(n_seg):
        faces.append((0, ring(1, s), ring(1, s + 1)))
    for r in range(1, n_rings - 1):
        for s in range(n_seg):
            faces.append((ring(r, s), ring(r + 1, s), ring(r + 1, s + 1)))
            faces.append((ring(r, s), ring(r + 1, s + 1), ring(r, s + 1)))
    bottom = 1 + (n_rings - 1) * n_seg
    for s in range(n_seg):
        faces.append((bottom, ring(n_rings - 1, s + 1), ring(n_rings - 1, s)))
    return np.array(verts), np.array(faces)


def _instanced_spheres(centers, radius: float, template):
    """Translate copies of the unit-sphere template to every centre and
    concatenate them into one Mesh3d vertex/face soup: (x, y, z, i, j, k)."""
    import numpy as np
    verts, faces = template
    centers = np.asarray(centers, dtype=float)
    pts = (verts[None, :, :] * radius + centers[:, None, :]).reshape(-1, 3)
    offsets = (np.arange(len(centers)) * len(verts))[:, None, None]
    tris = (faces[None, :, :] + offsets).reshape(-1, 3)
    return pts[:, 0], pts[:, 1], pts[:, 2], tris[:, 0], tris[:, 1], tris[:, 2]


def _domain_wireframe(sx: float, sy: float, sz: float):
    """The 12 box edges of the centred domain [-sx/2,sx/2]x[-sy/2,sy/2]x
    [-sz/2,sz/2] as one None-separated polyline (x, y, z) for a Scatter3d
    lines trace."""
    corners = [(x, y, z) for x in (-sx / 2, sx / 2) for y in (-sy / 2, sy / 2) for z in (-sz / 2, sz / 2)]
    xs, ys, zs = [], [], []
    for ai, a in enumerate(corners):
        for b in corners[ai + 1:]:
            if sum(u != v for u, v in zip(a, b)) == 1:  # edge, not diagonal
                xs += [a[0], b[0], None]
                ys += [a[1], b[1], None]
                zs += [a[2], b[2], None]
    return xs, ys, zs


# Above this many cells in one category trace, instance octahedra instead of
# uv-spheres to cap the vertex count the browser has to push around.
_SPHERE_DETAIL_LIMIT = 4000


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
    sx, sy, sz = (dom.size_x.micrometers, dom.size_y.micrometers,
                  dom.size_z.micrometers)

    sizes = (sx, sy, sz)

    def phys(p, i):
        # Centred frame: 0 = domain centre (src/core/coords.py)
        return centred_um(p[i] if len(p) > i else 0, cell_um, sizes[i])

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
        centers = [e[0] for e in entries]
        color = entries[0][1]
        # True-size cells: spheres of radius cell_height/2 in data um, the
        # same physical footprint as the 2D figure's circles.
        template = _sphere_template(
            'octa' if len(centers) > _SPHERE_DETAIL_LIMIT else 'uv')
        x, y, z, i, j, k = _instanced_spheres(centers, cell_um / 2.0, template)
        traces.append(go.Mesh3d(
            x=x, y=y, z=z, i=i, j=j, k=k,
            color=color, hoverinfo='skip',
            name=f"{label}: {len(entries)}",
            showlegend=True,
            legendgroup=view,
            legendgrouptitle_text=('Metabolism' if view == 'metabolism' else 'Fate'),
            visible=True if (view == 'metabolism' or not metabolism_view) else False,
        ))
        trace_views.append(view)

    # --- substance isosurfaces at their thresholds -------------------------
    # Every configured (substance, threshold) is listed in the legend so it
    # can be shown/hidden from iteration 1; a threshold the field does not
    # cross yet renders nothing and says so in its name. The first crossed
    # surface starts visible.
    iso_visible_seen = False
    for name in substances_3d:
        field = fields.get(name)
        if field is None:
            continue
        arr = np.asarray(field)
        if arr.ndim != 3:
            continue
        nz, ny, nx = arr.shape
        xs = (np.arange(nx) + 0.5) * (sx / nx) - sx / 2
        ys = (np.arange(ny) + 0.5) * (sy / ny) - sy / 2
        zs = (np.arange(nz) + 0.5) * (sz / nz) - sz / 2
        Z, Y, X = np.meshgrid(zs, ys, xs, indexing='ij')
        color = specs.get(name, {}).get('color', 'gray')
        for iso_value, iso_label in isolines.get(name, []):
            crossed = bool(arr.min() < iso_value < arr.max())
            visible = True if (crossed and not iso_visible_seen) else 'legendonly'
            iso_visible_seen = iso_visible_seen or crossed
            traces.append(go.Isosurface(
                x=X.ravel(), y=Y.ravel(), z=Z.ravel(), value=arr.ravel(),
                isomin=iso_value, isomax=iso_value, surface_count=1,
                opacity=0.25, showscale=False,
                caps=dict(x=dict(show=False), y=dict(show=False),
                          z=dict(show=False)),
                colorscale=[[0, color], [1, color]],
                name=f"{name} {iso_label}: {iso_value:.3g}"
                     + ('' if crossed else ' (not crossed)'),
                showlegend=True, visible=visible,
            ))
            trace_views.append('always')

    if not traces:
        print("[WORKFLOW] 3D viewer: nothing to draw - skipping HTML")
        return None

    # Faint wireframe of the full domain box, so the fixed extent reads even
    # where nothing lives. Added after the empty-check: a wireframe alone is
    # not worth an HTML.
    wx, wy, wz = _domain_wireframe(sx, sy, sz)
    traces.insert(0, go.Scatter3d(
        x=wx, y=wy, z=wz, mode='lines',
        line=dict(color='rgba(120,120,120,0.45)', width=1.5),
        hoverinfo='skip', showlegend=False,
    ))
    trace_views.insert(0, 'always')

    fig = go.Figure(data=traces)
    max_size = max(sx, sy, sz)
    fig.update_layout(
        title=f"MicroC 3D at t = {time_point:.3f} {title_suffix}",
        scene=dict(
            # Fixed domain box, never autoranged to the occupied region.
            xaxis=dict(title='X (um, 0 = centre)', range=[-sx / 2, sx / 2]),
            yaxis=dict(title='Y (um, 0 = centre)', range=[-sy / 2, sy / 2]),
            zaxis=dict(title='Z (um, 0 = centre)', range=[-sz / 2, sz / 2]),
            aspectmode='manual',
            aspectratio=dict(x=sx / max_size, y=sy / max_size, z=sz / max_size),
        ),
        legend=dict(groupclick='togglegroup'),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    if both_views:
        # Restyle only the cell traces: wireframe and isosurfaces keep the
        # show/hide state the user set via the legend across view switches.
        cell_idx = [idx for idx, view in enumerate(trace_views)
                    if view in ('metabolism', 'fate')]

        def mask(active):
            return [trace_views[idx] == active for idx in cell_idx]
        fig.update_layout(updatemenus=[dict(
            type='buttons', direction='right', x=0.0, y=1.08,
            buttons=[
                dict(label='Metabolism view', method='restyle',
                     args=[{'visible': mask('metabolism')}, cell_idx]),
                dict(label='Fate view', method='restyle',
                     args=[{'visible': mask('fate')}, cell_idx]),
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
                        "Empty = Lactate/Glucose/TGFA/H. The reserved entry "
                        "'ATP_gate' renders the proliferation ATP-gate "
                        "isolines per pathway on a blank panel (slice "
                        "figures; not in the HTML viewer).",
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
                        "there). Empty = all four quadrant substances.",
         "default": []},
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
    missing = [s for s in specs
               if s != ATP_GATE_KEY and s not in simulator.state.substances]
    if missing:
        print(f"[WORKFLOW] Substances not found in simulator: {missing} - skipping 3D plots")
        return False

    fields = {name: simulator.state.substances[name].concentrations
              for name in specs if name != ATP_GATE_KEY}

    # ATP-gate panel data over the full 3D O2/Glucose grids; the term arrays
    # are sliced per plane below, exactly like the substance fields.
    atp_gate = None
    if ATP_GATE_KEY in specs and _to_bool(show_isolines):
        subs = simulator.state.substances
        atp_gate = atp_gate_payload(
            results.get('proliferation_gate'),
            getattr(subs.get('Oxygen'), 'concentrations', None),
            getattr(subs.get('Glucose'), 'concentrations', None))
        if 'note' in atp_gate:
            print(f"[WORKFLOW] ATP-gate quadrant: "
                  f"{atp_gate['note'].replace(chr(10), ' ')}")

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
                plane_gate = atp_gate
                if atp_gate is not None and 'terms' in atp_gate:
                    plane_gate = {
                        'threshold': atp_gate['threshold'],
                        'terms': {k: slice_field(np.asarray(t), axis, index)
                                  for k, t in atp_gate['terms'].items()},
                    }
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
                    atp_gate=plane_gate,
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
            # The interactive viewer renders substance volumes only; the
            # ATP-gate panel is a slice-figure feature for now.
            viewer_specs = {k: v for k, v in specs.items() if k != ATP_GATE_KEY}
            wanted_3d = list(substances_3d) if substances_3d else list(viewer_specs)
            if ATP_GATE_KEY in wanted_3d:
                print("[WORKFLOW] 3D viewer: ATP_gate has no volume - skipped there")
                wanted_3d = [n for n in wanted_3d if n != ATP_GATE_KEY]
            written = write_viewer_html(
                config, fields, viewer_specs, list(population.state.cells.values()),
                jayatilake_cell_color, isolines,
                wanted_3d,
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
