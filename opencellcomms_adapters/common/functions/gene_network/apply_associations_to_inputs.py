"""
Apply Associations to Inputs - Set gene inputs based on substance concentrations.

For each association (substance -> gene_input):
- Read substance concentration (cell-local from simulator, or flat from context)
- Compare to threshold
- Set gene_input = ON if concentration > threshold, else OFF

Associations flagged "activation": "hill" instead use the NetLogo probabilistic
drug activation (see below) rather than the deterministic threshold test.
"""

import random as _random

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


# NetLogo probabilistic activation (microC_Metabolic_Symbiosis.nlogo3d,
# -ACTIVE-FROM-PATCH-16): MCT1I and GLUT1I are set stochastically instead of
# by a hard threshold:
#     probability = 0.85 - 0.85 / (1 + (conc / threshold)^1.0)
#     active      = probability > cell_random
# where cell_random is a persistent per-cell value in [0, 1) drawn at cell
# creation and re-drawn for daughters on division (HierarchicalBooleanNetwork
# .copy() re-draws _cell_ran1/_cell_ran2). This gives stable cell-to-cell
# variability in drug response.
_HILL_MAX = 0.85
_HILL_EXPONENT = 1.0
# NetLogo pairing: my-cell-ran1 -> MCT1I, my-cell-ran2 -> GLUT1I. These attrs
# are drawn by initialize_netlogo_gene_networks; reuse them so init-time and
# per-step activation see the same per-cell random.
_CELL_RAN_ATTRS = {'MCT1I': '_cell_ran1', 'GLUT1I': '_cell_ran2'}


def _hill_probability(concentration: float, threshold: float) -> float:
    """NetLogo Hill activation probability. 0 at conc=0, saturates at 0.85."""
    if threshold <= 0 or concentration <= 0:
        return 0.0
    return _HILL_MAX - _HILL_MAX / (1.0 + (concentration / threshold) ** _HILL_EXPONENT)


def _cell_random(gene_network, gene_input: str) -> float:
    """Persistent per-cell random in [0, 1) for a hill-activated input.

    MCT1I/GLUT1I reuse _cell_ran1/_cell_ran2 (NetLogo my-cell-ran1/2); any
    other hill input gets a lazily drawn value cached on the network.
    """
    if gene_network is None:
        return _random.random()
    attr = _CELL_RAN_ATTRS.get(gene_input)
    if attr is not None:
        val = getattr(gene_network, attr, None)
        if val is None:
            val = _random.random()
            setattr(gene_network, attr, val)
        return val
    rans = getattr(gene_network, '_cell_input_rans', None)
    if rans is None:
        rans = {}
        gene_network._cell_input_rans = rans
    if gene_input not in rans:
        rans[gene_input] = _random.random()
    return rans[gene_input]


@register_function(
    requires=['gene_networks', 'population', 'simulator'],
    display_name="Apply Associations to Inputs",
    description="Set gene input states based on substance concentrations and association thresholds",
    category="INITIALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def apply_associations_to_inputs(
    env: BiologicalContext,
    **kwargs
) -> bool:
    """
    Apply substance-to-gene associations.

    When a simulator is available (spatial model), reads cell-local concentrations
    from the simulator's spatial grid. Each cell gets its own input states based on
    the concentrations at its grid position.

    When no simulator is available (standalone gene network), falls back to flat
    context['substances'] values applied uniformly to all cells.

    Associations with "activation": "hill" (MCT1I/GLUT1I in the NetLogo model)
    are set probabilistically: hill(conc/threshold) > persistent per-cell random,
    instead of the deterministic conc > threshold test.
    """
    try:
        # Population/simulator via the raw escape hatches: this reads neighbour-grid
        # concentrations with custom grid geometry and writes node states across the
        # gene-network dict, neither of which the typed views model.
        population = env.cells.raw
        config = env.config
        simulator = env.environment.raw_simulator

        # Get associations, thresholds and activation modes from context or config
        associations = env.raw_context.get('associations', {})
        thresholds = env.raw_context.get('thresholds', {})
        activations = env.raw_context.get('association_activations', {})

        # If not in context directly, try config object
        if not associations and config:
            associations = getattr(config, 'associations', {}) or {}
            thresholds_config = getattr(config, 'thresholds', {}) or {}
            activations = {}
            for gene_input, threshold_obj in thresholds_config.items():
                if hasattr(threshold_obj, 'threshold'):
                    thresholds[gene_input] = threshold_obj.threshold
                else:
                    thresholds[gene_input] = threshold_obj
                activations[gene_input] = getattr(threshold_obj, 'activation', 'threshold')

        if not associations:
            print("[WARNING] No associations defined")
            return True

        # Get spatial concentrations from simulator (if available).
        # NOTE: under the per-cell ask this runs once per cell, so the whole-grid
        # fetch happens per cell. Left un-cached deliberately: a per-tick cache
        # would need a reliable per-tick invalidation signal, and a wrong one
        # serves stale concentrations (wrong science). Optimize later only with a
        # verified step/diffusion signal — the FiPy solve dominates runtime anyway.
        substance_concentrations = {}
        if simulator and hasattr(simulator, 'get_substance_concentrations'):
            substance_concentrations = simulator.get_substance_concentrations()

        # Grid geometry (same pattern as _recalculate_metabolism)
        cell_size_um = 20.0
        if config and hasattr(config, 'domain'):
            domain = config.domain
            grid_spacing_x = domain.size_x.micrometers / domain.nx
            grid_spacing_y = domain.size_y.micrometers / domain.ny
        else:
            grid_spacing_x = grid_spacing_y = 30.0

        gene_networks = env.raw_context.get('gene_networks', {})

        # --- Spatial model: per-cell local concentrations from simulator ---
        if population and substance_concentrations:
            # Per-cell when the executor's per-cell ask bound a cell (env.cell);
            # else process the whole population. Diagnostic logging is suppressed
            # in per-cell mode (it would print once per cell).
            per_cell = env.cell is not None
            if per_cell:
                _bound = env.cell.raw
                cells_iter = [(_bound.state.id, _bound)]
            else:
                cells_iter = list(population.state.cells.items())
                print(f"[ASSOCIATIONS] Applying {len(associations)} associations (spatial, per-cell)")
            cells_on_count = {gene_input: 0 for gene_input in associations.values()}
            # Track the spatial concentration range per input so the resolution
            # table can show min..max and flag whether the field actually varies.
            conc_min = {gene_input: None for gene_input in associations.values()}
            conc_max = {gene_input: None for gene_input in associations.values()}

            for cell_id, cell in cells_iter:
                # Get cell grid position
                pos = cell.state.position
                if len(pos) == 2:
                    cell_x, cell_y = pos
                else:
                    cell_x, cell_y = pos[0], pos[1]
                phys_x = cell_x * cell_size_um
                phys_y = cell_y * cell_size_um
                grid_x = int(phys_x / grid_spacing_x)
                grid_y = int(phys_y / grid_spacing_y)

                # Clamp to valid grid bounds
                if config and hasattr(config, 'domain'):
                    grid_x = max(0, min(config.domain.nx - 1, grid_x))
                    grid_y = max(0, min(config.domain.ny - 1, grid_y))

                # This cell's gene network: write target (new pattern) and the
                # holder of the persistent per-cell randoms for hill inputs.
                cell_gn = gene_networks.get(cell_id)
                ran_gn = cell_gn
                if ran_gn is None and getattr(cell.state, 'gene_network', None):
                    ran_gn = cell.state.gene_network

                # Per-cell input states based on LOCAL concentrations
                cell_input_states = {}
                for substance_name, gene_input in associations.items():
                    local_conc = substance_concentrations.get(
                        substance_name, {}).get((grid_x, grid_y), 0.0)
                    threshold = thresholds.get(gene_input, 0.0)
                    if activations.get(gene_input) == 'hill':
                        # NetLogo probabilistic activation (MCT1I/GLUT1I)
                        is_on = (_hill_probability(local_conc, threshold)
                                 > _cell_random(ran_gn, gene_input))
                    else:
                        is_on = local_conc > threshold
                    cell_input_states[gene_input] = is_on
                    if is_on:
                        cells_on_count[gene_input] += 1
                    lc = float(local_conc)
                    if conc_min[gene_input] is None or lc < conc_min[gene_input]:
                        conc_min[gene_input] = lc
                    if conc_max[gene_input] is None or lc > conc_max[gene_input]:
                        conc_max[gene_input] = lc

                # Write to context['gene_networks'] (new pattern)
                if cell_gn is not None:
                    for node_name, state in cell_input_states.items():
                        if node_name in cell_gn.nodes:
                            cell_gn.nodes[node_name].current_state = state

                # Write to cell.state.gene_network (old pattern, if present)
                if hasattr(cell.state, 'gene_network') and cell.state.gene_network:
                    for node_name, state in cell_input_states.items():
                        if node_name in cell.state.gene_network.nodes:
                            cell.state.gene_network.nodes[node_name].current_state = state

            if not per_cell:
                total_cells = len(population.state.cells)
                cur_step = env.raw_context.get('current_step')
                iter_str = f"iter {cur_step}" if cur_step is not None else "init"
                print(f"[INPUT RESOLUTION] {iter_str} | {total_cells} cells | "
                      f"rule: concentration > threshold -> ON")
                print(f"   {'substance':<10} {'conc':<16} {'thr':<10} "
                      f"{'test':<26} {'input':<16} state ON/total")
                all_uniform = True
                for substance_name, gene_input in associations.items():
                    thr = float(thresholds.get(gene_input, 0.0))
                    cmin = conc_min.get(gene_input)
                    cmax = conc_max.get(gene_input)
                    on = cells_on_count.get(gene_input, 0)
                    if cmin is None:
                        cmin = cmax = 0.0
                    uniform = (cmin == cmax)
                    all_uniform = all_uniform and uniform
                    if uniform:
                        conc_disp = f"{cmin:.4g}"
                        test_disp = f"{cmin:.4g} > {thr:g}"
                    else:
                        conc_disp = f"{cmin:.4g}..{cmax:.4g}"
                        test_disp = f"[{cmin:.4g}..{cmax:.4g}] > {thr:g}"
                    if activations.get(gene_input) == 'hill':
                        test_disp = f"hill(conc/{thr:g}) > ran"
                    if total_cells > 0 and on == total_cells:
                        state_disp = "ON "
                    elif on == 0:
                        state_disp = "OFF"
                    else:
                        state_disp = "MIX"
                    print(f"   {substance_name:<10} {conc_disp:<16} {thr:<10g} "
                          f"{test_disp:<26} {gene_input:<16} {state_disp}  {on}/{total_cells}")
                if all_uniform:
                    print("   [note] all fields spatially uniform (min==max) -> no gradient; "
                          "if you expected spatial variation, check that a diffusion solver runs")

        # --- Fallback: no simulator (standalone gene network / initialization) ---
        elif population:
            substances = env.raw_context.get('substances', {})
            input_states = {}
            hill_inputs = []  # (gene_input, probability) — resolved per cell below

            print(f"[ASSOCIATIONS] Applying {len(associations)} associations (flat, uniform):")
            for substance_name, gene_input in associations.items():
                concentration = substances.get(substance_name, 0.0)
                threshold = thresholds.get(gene_input, 0.0)
                if activations.get(gene_input) == 'hill':
                    prob = _hill_probability(concentration, threshold)
                    hill_inputs.append((gene_input, prob))
                    print(f"   {substance_name} ({concentration}) hill p={prob:.3f} "
                          f"vs per-cell ran -> {gene_input}")
                    continue
                is_on = concentration > threshold
                input_states[gene_input] = is_on
                status = "ON" if is_on else "OFF"
                print(f"   {substance_name} ({concentration}) > {threshold} -> {gene_input} = {status}")

            # Apply uniformly to all cells (hill inputs per-cell via cell randoms)
            for cell_id, cell_gn in gene_networks.items():
                for node_name, state in input_states.items():
                    if node_name in cell_gn.nodes:
                        cell_gn.nodes[node_name].current_state = state
                for gene_input, prob in hill_inputs:
                    if gene_input in cell_gn.nodes:
                        cell_gn.nodes[gene_input].current_state = \
                            prob > _cell_random(cell_gn, gene_input)

            # Old-pattern backward compatibility
            for cell_id, cell in population.state.cells.items():
                if hasattr(cell.state, 'gene_network') and cell.state.gene_network:
                    old_gn = cell.state.gene_network
                    for node_name, state in input_states.items():
                        if node_name in old_gn.nodes:
                            old_gn.nodes[node_name].current_state = state
                    for gene_input, prob in hill_inputs:
                        if gene_input in old_gn.nodes:
                            old_gn.nodes[gene_input].current_state = \
                                prob > _cell_random(old_gn, gene_input)

            env.raw_context['gene_network_inputs'] = input_states
        else:
            print("[WARNING] No population available")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to apply associations: {e}")
        import traceback
        traceback.print_exc()
        return False
