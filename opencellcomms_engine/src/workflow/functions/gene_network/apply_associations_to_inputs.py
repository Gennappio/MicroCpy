"""
Apply Associations to Inputs - Set gene inputs based on substance concentrations.

For each association (substance -> gene_input):
- Read substance concentration
- Compare to threshold
- Set gene_input = ON if concentration > threshold, else OFF
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation, IConfig


@register_function(
    display_name="Apply Associations to Inputs",
    description="Set gene input states based on substance concentrations and association thresholds",
    category="INITIALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def apply_associations_to_inputs(
    context: Dict[str, Any],
    **kwargs
) -> bool:
    """
    Apply substance-to-gene associations.

    For each association (substance -> gene_input):
    - Read substance concentration
    - Compare to threshold
    - Set gene_input = ON if concentration > threshold, else OFF

    This is for use after add_substance and add_association.
    """
    try:
        population: Optional[ICellPopulation] = context.get('population')
        config: Optional[IConfig] = context.get('config')

        # Get substances from context
        substances = context.get('substances', {})

        # Get associations and thresholds from either context or config
        associations = context.get('associations', {})
        thresholds = context.get('thresholds', {})

        # If not in context directly, try config object
        if not associations and config:
            associations = getattr(config, 'associations', {}) or {}
            thresholds_config = getattr(config, 'thresholds', {}) or {}
            # Convert config thresholds to simple dict
            for gene_input, threshold_obj in thresholds_config.items():
                if hasattr(threshold_obj, 'threshold'):
                    thresholds[gene_input] = threshold_obj.threshold
                else:
                    thresholds[gene_input] = threshold_obj

        if not associations:
            print("[WARNING] No associations defined")
            return True

        # Build input states based on associations
        input_states = {}

        print(f"[ASSOCIATIONS] Applying {len(associations)} associations:")
        for substance_name, gene_input in associations.items():
            concentration = substances.get(substance_name, 0.0)
            threshold = thresholds.get(gene_input, 0.0)

            # Compare concentration to threshold
            is_on = concentration > threshold
            input_states[gene_input] = is_on

            status = "ON" if is_on else "OFF"
            print(f"   {substance_name} ({concentration}) > {threshold} -> {gene_input} = {status}")

        # Apply to all cells
        if population:
            cells = population.state.cells
            for cell_id, cell in cells.items():
                if cell.state.gene_network:
                    cell.state.gene_network.set_input_states(input_states)
            print(f"   [+] Applied input states to {len(cells)} cells")
        else:
            print(f"   [!] No population yet")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to apply associations: {e}")
        import traceback
        traceback.print_exc()
        return False

