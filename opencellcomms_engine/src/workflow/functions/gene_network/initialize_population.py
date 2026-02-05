"""
Initialize Population - Create N cells for gene network testing.

This function creates a population with N cells (without gene networks yet).
Gene networks are attached separately by 'Initialize Gene Networks'.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function
from ._mock_helpers import (
    MockPopulation,
    MockPopulationState,
    MockCell,
    MockCellState,
    MockPosition,
    MockSimulator,
    MockConfig,
)


@register_function(
    display_name="Initialize Population",
    description="Create a population with N cells (without gene networks). Works for both testing and full simulation.",
    category="INITIALIZATION",
    parameters=[
        {"name": "num_cells", "type": "INT", "description": "Number of cells to create", "default": 100},
    ],
    outputs=["population"],
    cloneable=False
)
def initialize_population(
    context: Dict[str, Any],
    num_cells: int = 100,
    **kwargs
) -> bool:
    """
    Create a population with N cells.

    This is REUSABLE:
    - For testing: creates mock population
    - For full simulation: creates real CellPopulation (if simulator exists)

    Gene networks are attached separately by 'Initialize Gene Networks'.
    """
    print(f"[POPULATION] Initializing population with {num_cells} cells")

    try:
        # Check if we're in a full simulation context (has simulator)
        simulator = context.get('simulator')

        if simulator is not None and not isinstance(simulator, MockSimulator):
            # Full simulation mode - use real population
            print(f"   [!] Full simulation mode - population should be created via setup_population")
            return True

        # Testing mode - create mock population
        population = MockPopulation()
        cells = {}

        for i in range(num_cells):
            cell_id = f"cell_{i}"
            cell = MockCell(id=cell_id)
            cell.state = MockCellState(
                id=cell_id,
                position=MockPosition(x=float(i), y=0.0),
                # gene_network is stored in context['gene_networks'], not in cell state
                gene_states={}
            )
            cells[cell_id] = cell

        population.state = MockPopulationState(cells=cells)

        # Store in context
        context['population'] = population
        context['num_cells'] = num_cells

        # Initialize gene_networks dict in context (gene networks added by Initialize Gene Networks)
        if 'gene_networks' not in context:
            context['gene_networks'] = {}

        # Create mock simulator if not present (for testing)
        if 'simulator' not in context:
            context['simulator'] = MockSimulator(concentrations={})

        # Create mock config if not present (for testing)
        if 'config' not in context:
            context['config'] = MockConfig(associations={}, thresholds={})

        if 'helpers' not in context:
            context['helpers'] = {}

        print(f"   [+] Created {num_cells} cells (no gene networks yet)")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to initialize population: {e}")
        import traceback
        traceback.print_exc()
        return False

