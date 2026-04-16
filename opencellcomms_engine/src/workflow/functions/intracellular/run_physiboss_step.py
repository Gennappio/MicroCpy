"""
Run PhysiBoss Step - Per-cell MaBoSS coupling with environment.

For each living cell:
1. Sample local substrate concentrations (vectorized when using CellContainer)
2. Convert to MaBoSS input node states via coupling thresholds
3. Run one MaBoSS stochastic simulation
4. Store output node probabilities for phenotype mapping

Supports two backends:
- CellContainer (NumPy SoA): vectorized concentration sampling + coupling
- Legacy Dict[str, Cell]: per-cell Python loop (backward compat)
"""

from typing import Dict, Any, Optional
import numpy as np
from src.workflow.decorators import register_function
from src.workflow.logging import log


@register_function(
    display_name="Run PhysiBoss Step",
    description=(
        "Run one MaBoSS step per cell, using PhysiBoss coupling: "
        "substance concentrations → BN input nodes → MaBoSS run → "
        "output node probabilities stored on cell"
    ),
    category="INTRACELLULAR",
    parameters=[
        {
            "name": "verbose",
            "type": "BOOL",
            "description": "Enable detailed per-cell logging",
            "default": None,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def run_physiboss_step(
    context: Dict[str, Any],
    verbose: Optional[bool] = None,
    **kwargs,
) -> None:
    """
    Run one PhysiBoss intracellular step for all living cells.

    Detects whether a CellContainer is available and uses the vectorized
    path for concentration sampling and coupling thresholds.  MaBoSS itself
    is always per-cell (inherently sequential).
    """
    from src.biology.cell_container import CellContainer

    container = context.get('cell_container')
    if isinstance(container, CellContainer):
        _run_vectorized(context, container, verbose)
    else:
        _run_legacy(context, verbose)


# ── Vectorized path (CellContainer) ────────────────────────────────────

def _run_vectorized(context, container, verbose):
    """CellContainer-backed: vectorized coupling + per-cell MaBoSS."""
    from src.biology.cell_container import phenotype_id

    coupling = context.get('physiboss_coupling')
    maboss_sim = context.get('maboss_sim')
    if maboss_sim is None:
        return

    simulator = context.get('simulator')
    N = container.count

    # Active mask: alive + not dead phenotypes
    alive = container.alive[:N].copy()
    dead_ids = {phenotype_id(p) for p in ("apoptotic", "necrotic", "dead", "removed")}
    for did in dead_ids:
        alive &= (container.phenotype_ids[:N] != did)
    alive_idx = np.where(alive)[0]

    if len(alive_idx) == 0:
        return

    # ── 1. Sample concentrations at all alive cell positions (vectorized) ──
    positions = container.positions[alive_idx]  # (M, dims)
    substance_arrays = _sample_concentrations_vectorized(positions, simulator)

    # ── 2. Compute BN input states (vectorized threshold) ──
    if coupling:
        bn_input_arrays = coupling.compute_bn_inputs_vectorized(substance_arrays)
    else:
        bn_input_arrays = {}

    # Ensure output columns exist
    node_names = list(maboss_sim.network.keys())
    for node in node_names:
        col_name = f"bn_prob_{node}"
        if not container.has_column(col_name):
            container.add_float_column(col_name, default=0.0)
        bool_col = f"bn_state_{node}"
        if not container.has_column(bool_col):
            container.add_bool_column(bool_col, default=False)

    # ── 3 & 4. Per-cell MaBoSS run (sequential — inherently stochastic) ──
    cells_processed = 0
    for local_i, global_i in enumerate(alive_idx):
        # Set BN input states for this cell
        for node_name, state_arr in bn_input_arrays.items():
            if node_name in maboss_sim.network:
                if state_arr[local_i]:
                    maboss_sim.network.set_istate(node_name, [0.0, 1.0])
                else:
                    maboss_sim.network.set_istate(node_name, [1.0, 0.0])

        result = maboss_sim.run()
        probs = _extract_node_probabilities(result, node_names)

        # Store probabilities into container columns
        for node, prob in probs.items():
            container.get_float(f"bn_prob_{node}")[global_i] = prob
            container.get_bool(f"bn_state_{node}")[global_i] = (prob >= 0.5)

        cells_processed += 1

    if cells_processed > 0:
        log(context, f"PhysiBoss: updated {cells_processed} cells (vectorized)",
            prefix="[BN]", node_verbose=verbose)


# ── Legacy path (Dict[str, Cell]) ──────────────────────────────────────

def _run_legacy(context, verbose):
    """Legacy Dict[str, Cell] path — backward compatible."""
    population = context.get('population')
    if population is None:
        return

    coupling = context.get('physiboss_coupling')
    maboss_sim = context.get('maboss_sim')
    if maboss_sim is None:
        return

    simulator = context.get('simulator')
    cells_processed = 0
    updated_cells = {}

    for cell_id, cell in population.state.cells.items():
        phenotype = getattr(cell.state, 'phenotype', '')
        if phenotype in ('apoptotic', 'necrotic', 'dead', 'removed'):
            continue

        local_concs = _get_local_concentrations(cell, simulator)

        if coupling:
            bn_inputs = coupling.compute_bn_inputs(local_concs)
        else:
            bn_inputs = {}

        for node_name, state in bn_inputs.items():
            if node_name in maboss_sim.network:
                if state:
                    maboss_sim.network.set_istate(node_name, [0.0, 1.0])
                else:
                    maboss_sim.network.set_istate(node_name, [1.0, 0.0])

        result = maboss_sim.run()
        bn_output_probs = _extract_node_probabilities(result, maboss_sim.network.keys())

        cell._physiboss_bn_outputs = bn_output_probs
        cell._physiboss_local_concs = local_concs

        gene_states = {node: (prob >= 0.5) for node, prob in bn_output_probs.items()}
        cell.state = cell.state.with_updates(gene_states=gene_states)
        updated_cells[cell_id] = cell
        cells_processed += 1

    if updated_cells:
        population.state = population.state.with_updates(cells=updated_cells)

    if cells_processed > 0:
        log(context, f"PhysiBoss: updated {cells_processed} cells",
            prefix="[BN]", node_verbose=verbose)


def _get_local_concentrations(cell, simulator) -> Dict[str, float]:
    """Get substance concentrations at the cell's position."""
    concs: Dict[str, float] = {}
    if simulator is None:
        return concs

    pos = cell.state.position
    x, y = pos[0], pos[1]

    try:
        # Try the standard OpenCellComms interface
        if hasattr(simulator, 'get_all_concentrations_at'):
            return simulator.get_all_concentrations_at(x, y)
        # Fall back to per-substance lookup
        if hasattr(simulator, 'substances'):
            for name in simulator.substances:
                concs[name] = simulator.get_substance_concentration(name, x, y)
    except Exception:
        pass

    return concs


def _extract_node_probabilities(result, node_names) -> Dict[str, float]:
    """Extract per-node probabilities from MaBoSS result."""
    probs: Dict[str, float] = {}

    try:
        last_states = result.get_last_nodes_probtraj()
        if hasattr(last_states, 'iloc'):
            last_row = last_states.iloc[-1]
            for node in node_names:
                probs[node] = float(last_row.get(node, 0.0))
        else:
            for node in node_names:
                probs[node] = float(last_states.get(node, 0.0))
    except Exception:
        # Fallback: parse state probabilities
        try:
            final_states = result.get_last_states_probtraj()
            if hasattr(final_states, 'iloc'):
                last_row = final_states.iloc[-1].to_dict()
            else:
                last_row = dict(final_states)
            for node in node_names:
                prob = 0.0
                for state_str, state_prob in last_row.items():
                    if state_str == 'Time':
                        continue
                    active_nodes = set(state_str.replace(" ", "").split("--"))
                    if node in active_nodes:
                        prob += float(state_prob)
                probs[node] = prob
        except Exception:
            for node in node_names:
                probs[node] = 0.0

    return probs



def _sample_concentrations_vectorized(positions, simulator) -> Dict[str, np.ndarray]:
    """
    Sample substance concentrations at all positions at once.

    If the simulator supports vectorized sampling (sample_at), uses that.
    Otherwise falls back to per-cell sampling.
    """
    N = positions.shape[0]
    result: Dict[str, np.ndarray] = {}

    if simulator is None:
        return result

    try:
        # Preferred: vectorized sampling
        if hasattr(simulator, 'sample_at'):
            return simulator.sample_at(positions)

        # Try bulk method
        if hasattr(simulator, 'get_concentrations_at_positions'):
            return simulator.get_concentrations_at_positions(positions)

        # Fallback: per-cell sampling into arrays
        if hasattr(simulator, 'substances'):
            for name in simulator.substances:
                concs = np.zeros(N, dtype=np.float64)
                for i in range(N):
                    x, y = positions[i, 0], positions[i, 1]
                    concs[i] = simulator.get_substance_concentration(name, x, y)
                result[name] = concs
    except Exception:
        pass

    return result