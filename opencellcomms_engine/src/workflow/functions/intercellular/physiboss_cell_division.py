"""
PhysiBoss Cell Division - Cell division with MaBoSS network inheritance.

When a cell's phenotype is 'Proliferation', this function divides it:
1. Create a daughter cell at a nearby position
2. Copy (or partially inherit) the MaBoSS Boolean network state
3. Reset parent cell phenotype to Quiescent
4. Optionally apply the PhysiBoss inheritance fraction (stochastic reset)

Supports CellContainer (vectorized daughter placement) and legacy Dict[str, Cell].
"""

from typing import Dict, Any, Optional, Set, Tuple
import random
import uuid
import numpy as np
from src.workflow.decorators import register_function
from src.workflow.logging import log
from src.biology.cell import Cell


@register_function(
    display_name="PhysiBoss Cell Division",
    description=(
        "Handle cell division with MaBoSS network state inheritance. "
        "Daughter cell inherits BN state with configurable stochasticity."
    ),
    category="INTERCELLULAR",
    parameters=[
        {
            "name": "inheritance_fraction",
            "type": "FLOAT",
            "description": (
                "Fraction of BN node states inherited by daughter. "
                "1.0 = exact copy, 0.0 = random reset. Uses PhysiBoss config if not set."
            ),
            "default": -1.0,
            "min_value": 0.0,
            "max_value": 1.0,
        },
        {
            "name": "verbose",
            "type": "BOOL",
            "description": "Enable detailed logging",
            "default": None,
        },
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def physiboss_cell_division(
    context: Dict[str, Any],
    inheritance_fraction: float = -1.0,
    verbose: Optional[bool] = None,
    **kwargs,
) -> None:
    """
    Handle cell division for PhysiBoss-coupled cells.

    Detects CellContainer and uses vectorized path, falling back to
    legacy Dict[str, Cell].
    """
    from src.biology.cell_container import CellContainer

    # Determine inheritance fraction
    inh_frac = inheritance_fraction
    if inh_frac < 0:
        pb_config = context.get('physiboss_config')
        if pb_config and pb_config.intracellular:
            inh_frac = pb_config.intracellular.inheritance_global
        else:
            inh_frac = 1.0

    container = context.get('cell_container')
    if isinstance(container, CellContainer):
        _divide_container(context, container, inh_frac, verbose)
        return

    population = context.get('population')
    if population is None:
        return

    dimensions = context.get('dimensions', 2)
    gene_networks = context.get('gene_networks', {})

    cells_to_divide = []
    for cell_id, cell in population.state.cells.items():
        if getattr(cell.state, 'phenotype', '') == 'Proliferation':
            cells_to_divide.append((cell_id, cell))

    if not cells_to_divide:
        return

    occupied: Set[Tuple] = {cell.state.position for cell in population.state.cells.values()}
    new_cells = {}
    updated_cells = {}
    divided = 0

    for cell_id, parent in cells_to_divide:
        daughter_pos = _find_position(parent.state.position, occupied, dimensions)
        if daughter_pos is None:
            # No space: arrest parent
            parent.state = parent.state.with_updates(phenotype='Growth_Arrest')
            updated_cells[cell_id] = parent
            continue

        # ── Create daughter ─────────────────────────────────────────────
        new_id = str(uuid.uuid4())

        # Inherit gene states
        parent_genes = getattr(parent.state, 'gene_states', {}) or {}
        daughter_genes = _inherit_gene_states(parent_genes, inh_frac)

        daughter = Cell(
            position=daughter_pos,
            phenotype='Quiescent',
            custom_functions_module=parent.custom_functions,
        )
        daughter.state = daughter.state.with_updates(
            age=0.0,
            division_count=0,
            gene_states=daughter_genes,
        )

        # Copy BN output cache
        parent_bn = getattr(parent, '_physiboss_bn_outputs', None)
        if parent_bn is not None:
            daughter._physiboss_bn_outputs = dict(parent_bn)

        new_cells[new_id] = daughter
        occupied.add(daughter_pos)

        # ── Reset parent ────────────────────────────────────────────────
        parent.state = parent.state.with_updates(
            age=0.0,
            phenotype='Quiescent',
            division_count=getattr(parent.state, 'division_count', 0) + 1,
        )
        updated_cells[cell_id] = parent
        divided += 1

    # Apply changes
    all_cells = {**population.state.cells, **updated_cells, **new_cells}
    population.state = population.state.with_updates(cells=all_cells, total_cells=len(all_cells))

    if divided > 0:
        log(context, f"PhysiBoss division: {divided} cells divided, "
            f"{len(cells_to_divide) - divided} blocked",
            prefix="[Div]", node_verbose=verbose)


def _inherit_gene_states(parent_genes: Dict[str, bool], fraction: float) -> Dict[str, bool]:
    """Inherit gene states with stochastic partial inheritance."""
    if fraction >= 1.0:
        return dict(parent_genes)
    daughter = {}
    for gene, state in parent_genes.items():
        if random.random() < fraction:
            daughter[gene] = state
        else:
            daughter[gene] = random.choice([True, False])
    return daughter


def _find_position(
    parent_pos: Tuple, occupied: Set[Tuple], dimensions: int = 2
) -> Optional[Tuple]:
    """Find a free adjacent position for a daughter cell."""
    if dimensions == 2:
        offsets = [(-1, -1), (-1, 0), (-1, 1),
                   (0, -1),           (0, 1),
                   (1, -1),  (1, 0),  (1, 1)]
    else:
        offsets = [(di, dj, dk)
                   for di in [-1, 0, 1]
                   for dj in [-1, 0, 1]
                   for dk in [-1, 0, 1]
                   if not (di == 0 and dj == 0 and dk == 0)]

    random.shuffle(offsets)

    for off in offsets:
        if dimensions == 2:
            candidate = (parent_pos[0] + off[0], parent_pos[1] + off[1])
            if len(parent_pos) > 2:
                candidate = (*candidate, parent_pos[2])
        else:
            candidate = (parent_pos[0] + off[0],
                         parent_pos[1] + off[1],
                         (parent_pos[2] if len(parent_pos) > 2 else 0) + off[2])

        if candidate not in occupied:
            return candidate
    return None



def _divide_container(context, container, inh_frac, verbose):
    """
    CellContainer-backed cell division.

    Finds all cells with Proliferation phenotype, places daughters at offset
    positions, copies BN state columns with optional stochastic inheritance,
    and resets parents to Quiescent.
    """
    from src.biology.cell_container import phenotype_id, phenotype_name

    N = container.count
    prolif_id = phenotype_id("Proliferation")
    quiescent_id = phenotype_id("Quiescent")

    # Find cells to divide
    dividing_mask = (container.phenotype_ids[:N] == prolif_id) & container.alive[:N]
    dividing_indices = np.where(dividing_mask)[0]

    if len(dividing_indices) == 0:
        return

    # Daughter positions: offset parent by a small random displacement
    parent_positions = container.positions[dividing_indices]  # (M, dims)
    offsets = np.random.uniform(-1.0, 1.0, parent_positions.shape)
    # Normalize to unit displacement
    norms = np.linalg.norm(offsets, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    offsets = offsets / norms
    # Displace by cell radius
    parent_radii = container.radii[dividing_indices]
    daughter_positions = parent_positions + offsets * parent_radii[:, np.newaxis]

    # Add daughters
    daughter_start = container.count
    daughter_indices = container.add_cells(daughter_positions, phenotype=quiescent_id)

    # Inherit BN state columns
    for col_name, arr in container._bool_columns.items():
        parent_vals = arr[dividing_indices]
        if inh_frac >= 1.0:
            arr[daughter_indices] = parent_vals
        else:
            # Stochastic: inherit with probability = inh_frac
            inherit_mask = np.random.random(len(dividing_indices)) < inh_frac
            random_vals = np.random.choice([True, False], len(dividing_indices))
            arr[daughter_indices] = np.where(inherit_mask, parent_vals, random_vals)

    for col_name, arr in container._float_columns.items():
        if col_name.startswith("bn_prob_"):
            parent_vals = arr[dividing_indices]
            if inh_frac >= 1.0:
                arr[daughter_indices] = parent_vals
            else:
                arr[daughter_indices] = parent_vals * inh_frac

    # Copy other properties
    container.cell_type_ids[daughter_indices] = container.cell_type_ids[dividing_indices]
    container.volumes[daughter_indices] = container.volumes[dividing_indices] * 0.5
    container.radii[daughter_indices] = (
        3.0 * container.volumes[daughter_indices] / (4.0 * np.pi)
    ) ** (1.0 / 3.0)

    # Reset parents: Quiescent, halve volume, increment division count
    container.phenotype_ids[dividing_indices] = quiescent_id
    container.ages[dividing_indices] = 0.0
    container.volumes[dividing_indices] *= 0.5
    container.radii[dividing_indices] = (
        3.0 * container.volumes[dividing_indices] / (4.0 * np.pi)
    ) ** (1.0 / 3.0)
    container.division_counts[dividing_indices] += 1

    n_divided = len(dividing_indices)
    log(context, f"PhysiBoss division: {n_divided} cells divided (container)",
        prefix="[Div]", node_verbose=verbose)