#!/usr/bin/env python3
"""Re-render iteration plots from saved state checkpoints — no simulation.

Reads the ``checkpoint_ITER_*.json`` + ``_fields.npz`` pairs written by the
``save_state_checkpoint`` node and regenerates, with the SAME rendering
functions the live run used:

- 2D: the four-substance quadrant figure (``generate_quadrant_plots``'s
  ``render_quadrant_plot``, cells with metabolic interiors + fate borders).
- 3D: the sliced quadrant figures and the interactive Plotly viewer HTML
  (``generate_3d_plots``'s helpers).

Rendering parameters (quadrant substances/colours, slices, show flags) are
NOT state — they are read from the run's archived ``workflow.json`` (the
copy the executor drops in every ``runs/<label>/``), resolved with the
executor's own parameter merge, so the replot uses exactly what the run
used. Override with ``--workflow``; with neither available, MicroC defaults
apply with a warning.

Outputs go to ``<checkpoints dir>/replot/{heatmaps,viewer3d}/`` by default —
originals are never touched. Filenames reproduce the live plots' naming
(including their ``render_time`` — 0.000 in current workflow runs); pass
``--use-true-time`` to stamp the checkpoint's iteration*dt time instead.

Scope (v1): regenerates the quadrant 2D figure and the 3D slices/viewer.
The AutoPlotter-based ``generate_iteration_plots`` figures are reproducible
from the same checkpoint data but are not rendered by this tool yet.

Usage:
    replot_checkpoint.py runs/p53off/iteration_plots/checkpoints/checkpoint_ITER_000003.json
    replot_checkpoint.py --run-dir runs/p53off            # latest checkpoint
    replot_checkpoint.py --run-dir runs/p53off --all      # every checkpoint
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_ENGINE = Path(__file__).resolve().parent.parent
for _p in (str(_ENGINE / "src"), str(_ENGINE), str(_ENGINE.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.io.state_checkpoint import StateCheckpoint, read_state_checkpoint  # noqa: E402

_PLOT_FUNCTIONS = ('generate_quadrant_plots', 'generate_3d_plots')


def load_plot_params(workflow_json: Path) -> Dict[str, Dict[str, Any]]:
    """{function_name: merged parameters} for every enabled plot node in the
    workflow, resolved with the executor's own merge (dict/list parameter
    nodes -> target_param, node parameters overlay)."""
    from src.workflow.schema import WorkflowDefinition

    wf = WorkflowDefinition.from_dict(
        json.loads(Path(workflow_json).read_text(encoding='utf-8')))
    params: Dict[str, Dict[str, Any]] = {}
    for sw in wf.subworkflows.values():
        for func in sw.functions:
            if func.function_name in _PLOT_FUNCTIONS and func.enabled:
                params[func.function_name] = sw.merge_parameters_for_function(func)
    return params


def _adapter():
    """The MicroC reporting functions (imported lazily so --help works
    without matplotlib)."""
    import matplotlib
    matplotlib.use('Agg')
    from opencellcomms_adapters.MicroC.functions.reporting import (
        generate_quadrant_plots as q,
        generate_3d_plots as p3,
    )
    from opencellcomms_adapters.MicroC.functions.reporting.cell_colors import (
        jayatilake_cell_color,
    )
    return q, p3, jayatilake_cell_color


def _common(ckpt: StateCheckpoint, params: Dict[str, Any], q, use_true_time: bool):
    """(quadrant specs, fields, isolines, flags, t, marker, title suffix) —
    the exact resolution the plot nodes perform."""
    raw = dict(params.get('quadrant_substances') or {}) or dict(q.DEFAULT_QUADRANTS)
    if len(raw) != 4:
        raise ValueError(f"Need exactly 4 quadrant substances, got {list(raw)}")
    specs = q._normalize_quadrants(raw, q._to_bool(params.get('autorange', False)))
    missing = [name for name in specs
               if name != q.ATP_GATE_KEY and name not in ckpt.fields]
    if missing:
        raise KeyError(f"Substances {missing} not in checkpoint "
                       f"(available: {ckpt.substances})")
    fields = {name: ckpt.fields[name] for name in specs
              if name != q.ATP_GATE_KEY}

    show = {key: q._to_bool(params.get(key, True))
            for key in ('show_isolines', 'show_cells', 'show_metabolism_colors',
                        'show_fate_colors', 'show_legends', 'show_gradient_legends')}
    isolines = ({name: entries for name, entries in ckpt.isolines().items()
                 if name in specs} if show['show_isolines'] else {})

    # ATP-gate panel: same shared builder as the live nodes, fed from the
    # checkpoint's stored gate record and saved O2/Glucose fields.
    atp_gate = None
    if q.ATP_GATE_KEY in specs and show['show_isolines']:
        atp_gate = q.atp_gate_payload(ckpt.proliferation_gate,
                                      ckpt.fields.get('Oxygen'),
                                      ckpt.fields.get('Glucose'))

    suffix = str(params.get('plot_name_suffix', '') or '')
    t = ckpt.time if use_true_time else ckpt.render_time
    marker = f"ITER_{ckpt.iteration:03d}{suffix}"
    title_suffix = (f"[Iteration {ckpt.iteration}"
                    f"{' ' + suffix.strip('_') if suffix else ''}]")
    return specs, fields, isolines, show, t, marker, title_suffix, atp_gate


def replot_2d(ckpt: StateCheckpoint, params: Dict[str, Any], out_root: Path,
              use_true_time: bool = False) -> List[Path]:
    """Regenerate the 2D quadrant figure from a checkpoint."""
    q, _, cell_color = _adapter()
    specs, fields, isolines, show, t, marker, title_suffix, atp_gate = _common(
        ckpt, params, q, use_true_time)

    cfg = ckpt.config_stub()
    triples = [(tuple(c.state.position[:2]), c.state.phenotype, c)
               for c in ckpt.cell_stubs()]
    out = out_root / "heatmaps" / f"quadrants_heatmap_t{t:.3f}_{marker}.png"
    q.render_quadrant_plot(
        cfg, fields, specs, triples, cell_color, None, isolines, t,
        title_suffix, out,
        show_cells=show['show_cells'],
        show_metabolism_colors=show['show_metabolism_colors'],
        show_fate_colors=show['show_fate_colors'],
        show_legends=show['show_legends'],
        show_gradient_legends=show['show_gradient_legends'],
        atp_gate=atp_gate,
    )
    return [out]


def replot_3d(ckpt: StateCheckpoint, params: Dict[str, Any], out_root: Path,
              use_true_time: bool = False, force_html: bool = False,
              no_html: bool = False) -> List[Path]:
    """Regenerate the 3D slice figures and viewer HTML from a checkpoint."""
    import numpy as np
    q, p3, cell_color = _adapter()
    specs, fields, isolines, show, t, marker, title_suffix, atp_gate = _common(
        ckpt, params, q, use_true_time)

    cfg = ckpt.config_stub()
    cells = ckpt.cell_stubs()
    grid_dims = (cfg.domain.nx, cfg.domain.ny, cfg.domain.nz)
    written: List[Path] = []

    for spec in list(params.get('slices') or ["z:mid", "y:mid", "x:mid"]):
        axis, index = p3.parse_slice_spec(spec, grid_dims)
        plane_fields = {name: p3.slice_field(np.asarray(arr), axis, index)
                        for name, arr in fields.items()}
        plane_gate = atp_gate
        if atp_gate is not None and 'terms' in atp_gate:
            plane_gate = {
                'threshold': atp_gate['threshold'],
                'terms': {k: p3.slice_field(np.asarray(v), axis, index)
                          for k, v in atp_gate['terms'].items()},
            }
        triples, layers = p3.select_band_cells(
            cells, cfg, axis, index,
            cell_band=str(params.get('cell_band', 'layer')))
        plane_sizes, axis_labels = p3.plane_geometry(cfg, axis)
        layer_note = f"{axis}={index} (cells: bio layer {layers})"
        out = out_root / "heatmaps" / (
            f"quadrants_heatmap_t{t:.3f}_{marker}_slice_{axis}{index:02d}.png")
        q.render_quadrant_plot(
            cfg, plane_fields, specs, triples, cell_color, None, isolines, t,
            f"{title_suffix} slice {layer_note}", out,
            show_cells=show['show_cells'],
            show_metabolism_colors=show['show_metabolism_colors'],
            show_fate_colors=show['show_fate_colors'],
            show_legends=show['show_legends'],
            show_gradient_legends=show['show_gradient_legends'],
            plane_sizes=plane_sizes, axis_labels=axis_labels,
            atp_gate=plane_gate,
        )
        written.append(out)

    html_enabled = q._to_bool(params.get('html_enabled', True))
    html_interval = max(1, int(params.get('html_interval', 10)))
    do_html = (not no_html) and (
        force_html or (html_enabled and ckpt.iteration % html_interval == 0))
    if do_html:
        # As on the live node: the viewer renders substance volumes only.
        substances_3d = [n for n in
                         (list(params.get('substances_3d') or []) or list(specs))
                         if n != q.ATP_GATE_KEY]
        html_out = p3.write_viewer_html(
            cfg, fields, specs, cells, cell_color, isolines, substances_3d,
            q._to_bool(params.get('html_metabolism_view', True)),
            q._to_bool(params.get('html_fate_view', True)),
            t, title_suffix,
            out_root / "viewer3d" / f"spheroid3d_t{t:.3f}_{marker}.html")
        if html_out:
            written.append(html_out)
    return written


def _find_checkpoints(run_dir: Path, take_all: bool) -> List[Path]:
    found = sorted(run_dir.glob("*/checkpoints/checkpoint_ITER_*.json"))
    if not found:
        raise FileNotFoundError(
            f"No checkpoints under {run_dir}/*/checkpoints/ "
            "(was save_state_checkpoint enabled in the run?)")
    return found if take_all else [found[-1]]


def _resolve_workflow(args, ckpt: StateCheckpoint,
                      run_dir: Optional[Path]) -> Optional[Path]:
    if args.workflow:
        return Path(args.workflow)
    if run_dir and (run_dir / "workflow.json").exists():
        return run_dir / "workflow.json"
    prov = str(ckpt.meta.get("provenance", {}).get("workflow_file") or "")
    if prov and Path(prov).exists():
        return Path(prov)
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-render iteration plots from state checkpoints.")
    parser.add_argument("checkpoints", nargs="*",
                        help="checkpoint_ITER_*.json paths")
    parser.add_argument("--run-dir", type=Path,
                        help="runs/<label> directory to scan for checkpoints "
                             "(latest only unless --all)")
    parser.add_argument("--all", action="store_true",
                        help="with --run-dir: replot every checkpoint")
    parser.add_argument("--workflow", type=Path,
                        help="workflow JSON to read plot parameters from "
                             "(default: <run-dir>/workflow.json)")
    parser.add_argument("--out", type=Path,
                        help="output directory (default: <checkpoints>/replot/)")
    parser.add_argument("--mode", choices=("auto", "2d", "3d"), default="auto",
                        help="force the render path (default: from the "
                             "checkpoint's domain dimensions)")
    parser.add_argument("--use-true-time", action="store_true",
                        help="stamp filenames/titles with iteration*dt instead "
                             "of the live run's render time")
    parser.add_argument("--force-html", action="store_true",
                        help="3D: write the viewer HTML for every checkpoint, "
                             "ignoring html_interval")
    parser.add_argument("--no-html", action="store_true",
                        help="3D: skip the viewer HTML")
    args = parser.parse_args(argv)

    if args.checkpoints:
        paths = [Path(p) for p in args.checkpoints]
        run_dir = args.run_dir
    elif args.run_dir:
        paths = _find_checkpoints(args.run_dir, args.all)
        run_dir = args.run_dir
    else:
        parser.error("give checkpoint paths or --run-dir")

    total = []
    params_cache: Dict[Path, Dict[str, Dict[str, Any]]] = {}
    for path in paths:
        ckpt = read_state_checkpoint(path)
        wf_path = _resolve_workflow(args, ckpt, run_dir)
        if wf_path is None:
            print("[replot] WARNING: no workflow.json found - using MicroC "
                  "default rendering parameters")
            all_params: Dict[str, Dict[str, Any]] = {}
        else:
            if wf_path not in params_cache:
                params_cache[wf_path] = load_plot_params(wf_path)
            all_params = params_cache[wf_path]

        mode = args.mode
        if mode == "auto":
            mode = "3d" if ckpt.dimensions == 3 else "2d"
        out_root = args.out or (path.parent / "replot")

        if mode == "3d":
            params = all_params.get('generate_3d_plots', {})
            written = replot_3d(ckpt, params, out_root,
                                use_true_time=args.use_true_time,
                                force_html=args.force_html,
                                no_html=args.no_html)
        else:
            params = all_params.get('generate_quadrant_plots', {})
            written = replot_2d(ckpt, params, out_root,
                                use_true_time=args.use_true_time)
        for w in written:
            print(f"[replot] {w}")
        total.extend(written)

    print(f"[replot] {len(total)} file(s) from {len(paths)} checkpoint(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
