"""Per-iteration state checkpoints: everything needed to re-render the
iteration plots without re-running the simulation.

One checkpoint = two sibling files in a ``checkpoints/`` directory:

- ``checkpoint_ITER_000012.json`` — iteration/time, domain geometry, resolved
  isoline thresholds, and every cell (position, phenotype, gene states,
  metabolic state, age, division count). Human-readable; ``gene_names`` is
  stored once and each cell's ``gene_states`` is a 0/1 list aligned to it
  (a per-cell ``{name: bool}`` dict when a cell's genes differ from the
  union — lossless either way).
- ``checkpoint_ITER_000012_fields.npz`` — every substance's concentration
  array, saved verbatim in the renderers' native orientation: 2D ``[y, x]``,
  3D ``[z, y, x]``.

The JSON is written last, so its presence marks a complete checkpoint. The
``cells`` list order is the population's iteration order — it is also the
draw order of overlapping circles in the 2D figures, so readers must
preserve it. Written by the ``save_state_checkpoint`` workflow node; read
back by ``tools/replot_checkpoint.py`` and analysis scripts.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

SCHEMA_VERSION = 1
CHECKPOINT_KIND = "occ_state_checkpoint"
FIELD_ORIENTATION = "2d:[y,x];3d:[z,y,x]"


def checkpoint_paths(out_dir: Union[str, Path], iteration: int) -> Tuple[Path, Path]:
    """(json_path, npz_path) for a checkpoint of this iteration."""
    out_dir = Path(out_dir)
    stem = f"checkpoint_ITER_{int(iteration):06d}"
    return out_dir / f"{stem}.json", out_dir / f"{stem}_fields.npz"


def resolve_association_threshold(config, substance_name: str) -> Optional[float]:
    """Gene-association threshold for a substance:
    ``config.associations[substance] -> config.thresholds[gene].threshold``.

    Same law as the MicroC adapter's ``_association_threshold`` (the engine
    cannot import the adapter); equivalence is pinned by a test. The value is
    returned UNCOERCED — an int threshold must stay an int so a replot
    serializes plot data (e.g. plotly isosurface levels) byte-identically.
    """
    if not hasattr(config, 'associations') or not hasattr(config, 'thresholds'):
        return None
    gene_input = config.associations.get(substance_name)
    if gene_input and gene_input in config.thresholds:
        return config.thresholds[gene_input].threshold
    return None


def resolve_isolines(config, substance_names: Iterable[str],
                     necrosis_thresholds: Dict[str, float],
                     ) -> Dict[str, List[Tuple[float, str]]]:
    """Per-substance isoline list [(value, label)], exactly as the plot nodes
    build it (association threshold + necrosis threshold), over all
    substances given."""
    isolines: Dict[str, List[Tuple[float, str]]] = {}
    for name in substance_names:
        entries: List[Tuple[float, str]] = []
        threshold = resolve_association_threshold(config, name)
        if threshold is not None:
            entries.append((threshold, 'threshold'))
        necrosis = (necrosis_thresholds or {}).get(name)
        if necrosis is not None:
            entries.append((necrosis, 'Necrosis'))
        if entries:
            isolines[name] = entries
    return isolines


def _length_dict(length) -> Optional[Dict[str, Any]]:
    if length is None:
        return None
    return {"value": float(length.value), "unit": str(length.unit),
            "micrometers": float(length.micrometers)}


def domain_geometry(config) -> Dict[str, Any]:
    """The domain fields the renderers consume, JSON-safe."""
    dom = config.domain
    dimensions = int(getattr(dom, 'dimensions', 2) or 2)
    return {
        "dimensions": dimensions,
        "size_x": _length_dict(dom.size_x),
        "size_y": _length_dict(dom.size_y),
        "size_z": _length_dict(getattr(dom, 'size_z', None)),
        "nx": int(dom.nx),
        "ny": int(dom.ny),
        "nz": int(dom.nz) if getattr(dom, 'nz', None) is not None else None,
        "cell_height": _length_dict(dom.cell_height),
    }


def _json_safe(value):
    """Coerce numpy scalars / tuples so json.dumps round-trips exactly."""
    import numpy as np
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _position_list(position) -> List[Any]:
    out = []
    for p in position:
        p = float(p)
        out.append(int(p) if p.is_integer() else p)
    return out


def serialize_cells(cells: Iterable[Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """(gene_names, cell dicts) in the given cell order.

    gene_names is the sorted union of all cells' gene keys; a cell whose keys
    equal the union stores gene_states as a 0/1 list aligned to gene_names,
    otherwise as an explicit {name: bool} dict (lossless fallback).
    """
    cell_list = list(cells)
    union: set = set()
    for cell in cell_list:
        union.update((getattr(cell.state, 'gene_states', {}) or {}).keys())
    gene_names = sorted(union)

    records = []
    for cell in cell_list:
        state = cell.state
        genes = getattr(state, 'gene_states', {}) or {}
        if set(genes.keys()) == union:
            gene_field: Any = [1 if genes[g] else 0 for g in gene_names]
        else:
            gene_field = {str(k): bool(v) for k, v in genes.items()}
        records.append({
            "id": str(state.id),
            "position": _position_list(state.position),
            "phenotype": str(state.phenotype),
            "age": float(getattr(state, 'age', 0.0) or 0.0),
            "division_count": int(getattr(state, 'division_count', 0) or 0),
            "metabolic_state": _json_safe(getattr(state, 'metabolic_state', {}) or {}),
            "gene_states": gene_field,
        })
    return gene_names, records


def _npz_keys_for(substances: List[str]) -> Dict[str, str]:
    """Substance name -> npz member key. np.savez's first positional
    parameter is literally ``file``, and path separators break zip member
    names — such names fall back to a positional key."""
    keys = {}
    for i, name in enumerate(substances):
        unsafe = name == "file" or "/" in name or "\\" in name
        keys[name] = f"field_{i:02d}" if unsafe else name
    return keys


def write_state_checkpoint(
    out_dir: Union[str, Path],
    iteration: int,
    *,
    fields: Dict[str, Any],
    cells: Iterable[Any],
    config: Any,
    necrosis_thresholds: Optional[Dict[str, float]] = None,
    proliferation_gate: Optional[Dict[str, float]] = None,
    time: float = 0.0,
    render_time: float = 0.0,
    dt: float = 1.0,
    dt_source: str = "default",
    provenance: Optional[Dict[str, Any]] = None,
) -> Tuple[Path, Path]:
    """Write one checkpoint (npz first, JSON second). Returns (json, npz)."""
    import numpy as np

    json_path, npz_path = checkpoint_paths(out_dir, iteration)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    substances = list(fields)
    npz_keys = _npz_keys_for(substances)
    arrays = {npz_keys[name]: np.asarray(fields[name]) for name in substances}
    np.savez_compressed(npz_path, **arrays)

    # Thresholds keep their numeric type (int vs float) end to end — see
    # resolve_association_threshold.
    necrosis = {str(k): _json_safe(v)
                for k, v in (necrosis_thresholds or {}).items() if v is not None}
    gene_names, cell_records = serialize_cells(cells)

    meta = {
        "schema_version": SCHEMA_VERSION,
        "kind": CHECKPOINT_KIND,
        "iteration": int(iteration),
        "time": float(time),
        "render_time": float(render_time),
        "dt": float(dt),
        "dt_source": str(dt_source),
        "domain": domain_geometry(config),
        "field_orientation": FIELD_ORIENTATION,
        "npz_file": npz_path.name,
        "substances": substances,
        "npz_keys": npz_keys,
        "field_dtypes": {name: str(arrays[npz_keys[name]].dtype)
                         for name in substances},
        "association_thresholds": {
            name: _json_safe(threshold) for name in substances
            if (threshold := resolve_association_threshold(config, name)) is not None},
        "necrosis_thresholds": necrosis,
        # Resolved proliferation ATP gate (threshold + the KO2/KG snapshot the
        # publisher included), stored verbatim so a replot contours the exact
        # rule the run applied. Empty dict when no gated node ran.
        "proliferation_gate": {str(k): _json_safe(v)
                               for k, v in (proliferation_gate or {}).items()
                               if v is not None},
        "isolines": {name: [[_json_safe(value), label] for value, label in entries]
                     for name, entries in
                     resolve_isolines(config, substances, necrosis).items()},
        "gene_names": gene_names,
        "cells": cell_records,
        "counts": {"num_cells": len(cell_records), "num_genes": len(gene_names)},
        "provenance": {**(provenance or {}),
                       "saved_at": datetime.now().isoformat(timespec='seconds')},
    }

    json_path.write_text(
        json.dumps(meta, ensure_ascii=False, separators=(',', ':')) + "\n",
        encoding='utf-8')
    return json_path, npz_path


def _stub_length(entry) -> Optional[SimpleNamespace]:
    if entry is None:
        return None
    return SimpleNamespace(value=entry["value"], unit=entry["unit"],
                           micrometers=entry["micrometers"])


@dataclass
class StateCheckpoint:
    """A loaded checkpoint plus the stub builders the replot path uses."""
    meta: Dict[str, Any]
    fields: Dict[str, Any]  # substance name -> ndarray
    json_path: Path
    npz_path: Path

    @property
    def iteration(self) -> int:
        return int(self.meta["iteration"])

    @property
    def time(self) -> float:
        return float(self.meta["time"])

    @property
    def render_time(self) -> float:
        return float(self.meta["render_time"])

    @property
    def dimensions(self) -> int:
        return int(self.meta["domain"]["dimensions"])

    @property
    def substances(self) -> List[str]:
        return list(self.meta["substances"])

    def config_stub(self) -> SimpleNamespace:
        """A config double exposing exactly what the renderers read
        (domain geometry; empty associations/thresholds — isolines come
        pre-resolved from the checkpoint)."""
        dom = self.meta["domain"]
        return SimpleNamespace(
            domain=SimpleNamespace(
                dimensions=dom["dimensions"],
                size_x=_stub_length(dom["size_x"]),
                size_y=_stub_length(dom["size_y"]),
                size_z=_stub_length(dom["size_z"]),
                nx=dom["nx"], ny=dom["ny"], nz=dom["nz"],
                cell_height=_stub_length(dom["cell_height"]),
            ),
            associations={}, thresholds={},
        )

    def cell_stubs(self) -> List[SimpleNamespace]:
        """Cell doubles (state.position/phenotype/gene_states/...) in the
        checkpoint's order — which is the original draw order."""
        gene_names = self.meta.get("gene_names", [])
        stubs = []
        for rec in self.meta["cells"]:
            genes = rec.get("gene_states", {})
            if isinstance(genes, list):
                genes = {name: bool(flag) for name, flag in zip(gene_names, genes)}
            else:
                genes = {str(k): bool(v) for k, v in genes.items()}
            stubs.append(SimpleNamespace(state=SimpleNamespace(
                id=rec["id"],
                position=tuple(rec["position"]),
                phenotype=rec["phenotype"],
                gene_states=genes,
                metabolic_state=rec.get("metabolic_state", {}),
                age=rec.get("age", 0.0),
                division_count=rec.get("division_count", 0),
            )))
        return stubs

    def isolines(self) -> Dict[str, List[Tuple[float, str]]]:
        # Values keep the numeric type JSON preserved (int stays int) so a
        # replot serializes plot data byte-identically to the live run.
        return {name: [(value, str(label)) for value, label in entries]
                for name, entries in self.meta.get("isolines", {}).items()}

    @property
    def proliferation_gate(self) -> Optional[Dict[str, float]]:
        """The resolved ATP gate stored at save time, or None when the run
        had no gated proliferation node."""
        return self.meta.get("proliferation_gate") or None


def read_state_checkpoint(path: Union[str, Path]) -> StateCheckpoint:
    """Load a checkpoint from its JSON path (fields loaded from the sibling
    npz named in the JSON)."""
    import numpy as np

    json_path = Path(path)
    meta = json.loads(json_path.read_text(encoding='utf-8'))
    if meta.get("kind") != CHECKPOINT_KIND:
        raise ValueError(f"Not a state checkpoint: {json_path}")
    npz_path = json_path.parent / meta["npz_file"]
    with np.load(npz_path) as data:
        fields = {name: data[key].copy()
                  for name, key in meta["npz_keys"].items()}
    return StateCheckpoint(meta=meta, fields=fields,
                           json_path=json_path, npz_path=npz_path)
