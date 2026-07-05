"""Build a per-T0-cell MaBoSS network for the Corral differentiation model.

Creates one ``BooleanNetwork`` per cell from ``tcell_corral.bnd``, loads the
MaBoSS transition rates and initial states from ``tcell_corral.cfg``, and
applies any per-node up-rate overrides. The overrides are where a PhysiBoSS
rate perturbation lives -- the ``FOXP3_2_lower`` run is simply
``up_rate_overrides = {"FOXP3_2": 0.2}`` -- surfaced in the GUI as an editable
table instead of an XML edit.

Each cell's network is advanced every tick by ``step_tcell_network`` using the
engine's continuous-time stochastic mode. Intended to run in the ``tcell``
kind's Setup canvas; it builds a network for every cell of the target ``kind``
(default ``tcell``), skipping other kinds (dendritic / endothelial) in the
multi-kind Corral population.
"""

from pathlib import Path
from typing import Dict, Union

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext
from src.biology.gene_network import BooleanNetwork

# .../TCELL_CORRAL/functions/initialization/<this file> -> .../TCELL_CORRAL/data
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@register_function(
    display_name="Build T-cell MaBoSS Networks",
    description="One continuous-time MaBoSS network per T0 cell (tcell_corral.bnd/.cfg), "
                "with editable node up-rate overrides for perturbations such as FOXP3_2.",
    category="INITIALIZATION",
    parameters=[
        {"name": "bnd_file", "type": "STRING",
         "description": "MaBoSS .bnd network file (relative to the plugin's data/ dir)",
         "default": "tcell_corral.bnd"},
        {"name": "cfg_file", "type": "STRING",
         "description": "MaBoSS .cfg with $u_/$d_ transition rates and .istate initial states",
         "default": "tcell_corral.cfg"},
        {"name": "up_rate_overrides", "type": "DICT",
         "description": "Per-node up-transition ($u_) rate overrides. The FOXP3_2_lower "
                        "perturbation is {\"FOXP3_2\": 0.2}; empty = wild type.",
         "default": {}},
        {"name": "kind", "type": "STRING",
         "description": "Only build networks for cells of this ABM kind. Untagged cells "
                        "(no _kind) still get one, so single-kind models are unaffected.",
         "default": "tcell"},
    ],
    inputs=["context"],
    outputs=["gene_network"],
    cloneable=False,
    compatible_kernels=["biophysics"],
    requires=["gene_networks", "population"],
)
def build_tcell_networks(
    env: BiologicalContext,
    bnd_file: str = "tcell_corral.bnd",
    cfg_file: str = "tcell_corral.cfg",
    up_rate_overrides: Union[Dict, None] = None,
    kind: str = "tcell",
    **kwargs,
) -> bool:
    if len(env.cells) == 0:
        print("[TCELL_CORRAL] No population found; run the population setup first.")
        return False

    bnd_path = _DATA_DIR / bnd_file
    cfg_path = _DATA_DIR / cfg_file
    if not bnd_path.exists() or not cfg_path.exists():
        print(f"[TCELL_CORRAL] Missing network files: {bnd_path} / {cfg_path}")
        return False

    overrides = {k: float(v) for k, v in (up_rate_overrides or {}).items()}

    # Parse + configure the template once, then copy() it per cell -- copy()
    # carries the rates and initial states and skips re-parsing the .bnd.
    template = BooleanNetwork(network_file=bnd_path)
    template.load_cfg(cfg_path)                       # $u_/$d_ rates + istate
    for node, up in overrides.items():
        template.set_rate(node, up=up)                # e.g. FOXP3_2 -> 0.2

    env.raw_context.setdefault("gene_networks", {})
    built = 0
    for cell in env.cells:
        cell_kind = cell.raw.state.metabolic_state.get("_kind")
        if cell_kind is not None and cell_kind != kind:
            continue                        # only T0 (tcell) cells carry a network
        cell_gn = template.copy()
        env.set_gene_network(cell, cell_gn)
        cell.set_gene_state_snapshot(cell_gn.get_all_states())
        built += 1

    active = ", ".join(f"$u_{k}={v}" for k, v in overrides.items()) or "wild type"
    print(f"[TCELL_CORRAL] Built {built} MaBoSS networks for kind '{kind}' ({active})")
    return True
