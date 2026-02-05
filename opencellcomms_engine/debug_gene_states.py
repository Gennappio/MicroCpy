#!/usr/bin/env python
"""Debug script to verify gene_states flow in the workflow.

This script simulates the FULL workflow context to debug why cells show "none" metabolic state.
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from src.biology.gene_network import BooleanNetwork
from src.biology.cell import Cell
from src.biology.population import CellPopulation
from pathlib import Path

# Configuration classes to mimic real config
class GeneNetworkConfig:
    def __init__(self, bnd_path, random_init=True, propagation_steps=20):
        self.bnd_file = str(bnd_path)
        self.random_initialization = random_init
        self.propagation_steps = propagation_steps
        self.output_nodes = ["Proliferation", "Apoptosis", "Growth_Arrest", "Necrosis"]
        self.nodes = {}

class DomainConfig:
    def __init__(self):
        self.size_x = type('obj', (object,), {'micrometers': 3000})()
        self.size_y = type('obj', (object,), {'micrometers': 3000})()
        self.cell_height = type('obj', (object,), {'micrometers': 20})()
        self.dimensions = 2
        self.nx = 150
        self.ny = 150

class ThresholdConfig:
    def __init__(self, threshold):
        self.threshold = threshold

class MinimalConfig:
    def __init__(self):
        self.gene_network = None
        self.domain = DomainConfig()
        # These must match what the actual workflow uses - CAPITALIZED to match JSON!
        self.associations = {
            'Oxygen': 'Oxygen_supply',
            'Glucose': 'Glucose_supply',
            'Lactate': 'MCT1_stimulus',  # Match workflow JSON
        }
        self.thresholds = {
            'Oxygen_supply': ThresholdConfig(0.022),  # Match workflow JSON
            'Glucose_supply': ThresholdConfig(0.05),
            'MCT1_stimulus': ThresholdConfig(1.0),
        }


def test_real_simulator():
    """Test with the REAL MultiSubstanceSimulator to match actual workflow."""
    print("\n" + "="*60)
    print("TEST: Real Simulator Integration")
    print("="*60)

    try:
        from src.simulation.multi_substance_simulator import MultiSubstanceSimulator
        from src.simulation.mesh_manager import MeshManager
        from src.config.config import DomainConfig as RealDomainConfig

        # Create real domain config
        domain = RealDomainConfig(
            size_x=3000.0,
            size_y=3000.0,
            size_z=0.0,
            nx=150,
            ny=150,
            nz=1,
            cell_height=20.0,
            dimensions=2
        )

        # Create minimal config with domain
        class RealConfig:
            def __init__(self):
                self.domain = domain
                self.substances = {}
                self.associations = {
                    'Oxygen': 'Oxygen_supply',
                    'Glucose': 'Glucose_supply',
                    'Lactate': 'MCT1_stimulus',
                }
                self.thresholds = {
                    'Oxygen_supply': ThresholdConfig(0.022),
                    'Glucose_supply': ThresholdConfig(0.05),
                    'MCT1_stimulus': ThresholdConfig(1.0),
                }

        config = RealConfig()

        # Create mesh manager and simulator
        mesh_manager = MeshManager(domain)
        simulator = MultiSubstanceSimulator(config, mesh_manager, verbose=False)

        # Add substances with initial values
        from src.simulation.multi_substance_simulator import SubstanceConfig

        oxygen_config = SubstanceConfig(
            name="Oxygen",
            diffusion_coeff=100000.0,
            production_rate=0.0,
            uptake_rate=0.0,
            initial_value=0.07,  # Above threshold of 0.022
            boundary_value=0.07,
            boundary_type="fixed",
            unit="mM"
        )

        glucose_config = SubstanceConfig(
            name="Glucose",
            diffusion_coeff=100000.0,
            production_rate=0.0,
            uptake_rate=0.0,
            initial_value=0.1,  # Above threshold of 0.05
            boundary_value=0.1,
            boundary_type="fixed",
            unit="mM"
        )

        simulator.add_substance(oxygen_config)
        simulator.add_substance(glucose_config)

        print(f"[1] Created simulator with {len(simulator.state.substances)} substances")

        # Get substance concentrations
        concs = simulator.get_substance_concentrations()
        print(f"[2] Substance concentration keys: {list(concs.keys())}")

        for name, grid in concs.items():
            if grid:
                sample_pos = next(iter(grid.keys()))
                sample_val = grid[sample_pos]
                print(f"    {name}: {len(grid)} positions, sample at {sample_pos} = {sample_val:.6f}")
            else:
                print(f"    {name}: EMPTY!")

        # Test lookup at a specific position
        test_pos = (75, 75)
        print(f"\n[3] Testing lookup at position {test_pos}:")
        for name, grid in concs.items():
            if test_pos in grid:
                print(f"    {name}: {grid[test_pos]:.6f}")
            else:
                print(f"    {name}: NOT FOUND at {test_pos}")
                # Show what positions ARE available
                if grid:
                    sample_keys = list(grid.keys())[:5]
                    print(f"        Available positions (sample): {sample_keys}")

        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("DEBUG: Gene States Flow Test")
    print("="*60)

    # Setup config
    bnd_path = Path("tests/jayatilake_experiment/jaya_microc.bnd")
    config = MinimalConfig()
    config.gene_network = GeneNetworkConfig(bnd_path, random_init=True)

    # Create template gene network
    print("\n[1] Loading template gene network...")
    gn_template = BooleanNetwork(network_file=bnd_path)
    print(f"    Input nodes: {len(gn_template.input_nodes)}")
    print(f"    Total nodes: {len(gn_template.nodes)}")

    # Create context for gene network storage
    context = {}

    # Create population
    print("\n[2] Creating CellPopulation...")
    custom_funcs = "tests/jayatilake_experiment/jayatilake_experiment_cell_functions.py"
    population = CellPopulation(
        grid_size=(150, 150),
        gene_network=gn_template,
        custom_functions_module=custom_funcs,
        config=config,
        context=context  # Pass context for gene network storage
    )

    # Add cells
    print("\n[3] Initializing cells...")
    cell_data = [
        {'position': (50, 50), 'phenotype': 'Growth_Arrest'},
        {'position': (75, 75), 'phenotype': 'Proliferation'},
        {'position': (100, 100), 'phenotype': 'Growth_Arrest'},
    ]
    population.initialize_cells(cell_data)
    print(f"    Initialized {len(population.state.cells)} cells")

    # Check initial state (gene networks are now in context)
    print("\n[4] Checking initial gene network attachment...")
    gene_networks = context.get('gene_networks', {})
    for cell_id, cell in population.state.cells.items():
        has_gn = cell_id in gene_networks
        gs = cell.state.gene_states
        print(f"    {cell_id}: gene_network={has_gn}, gene_states keys={list(gs.keys())[:5]}...")

    # Create mock simulator with substance concentrations
    print("\n[5] Creating mock simulator with substance concentrations...")

    class MockSimulator:
        """Mock simulator with substance concentrations."""
        def get_concentration(self, substance, x, y):
            # Simulate: high oxygen and glucose everywhere
            if substance == 'Oxygen':
                return 0.2  # Above threshold of 0.022
            elif substance == 'Glucose':
                return 0.3  # Above threshold of 0.05
            elif substance == 'Lactate':
                return 2.0  # Above threshold of 1.0
            return 0.0

        def get_substance_concentrations(self):
            """Return substance concentrations at all positions - match real simulator."""
            # Return dict of substance -> {position: concentration}
            positions = [(50, 50), (75, 75), (100, 100)]
            return {
                'Oxygen': {pos: 0.2 for pos in positions},
                'Glucose': {pos: 0.3 for pos in positions},
                'Lactate': {pos: 2.0 for pos in positions},  # Above threshold=1.0
            }

    mock_sim = MockSimulator()

    # Simulate workflow context
    print("\n[6] Simulating update_gene_networks workflow function...")
    from src.workflow.functions.intracellular.update_gene_networks import update_gene_networks

    context = {
        'population': population,
        'config': config,
        'simulator': mock_sim,  # Provides substance concentrations!
    }

    # First, let's check what the _get_local_environment function returns
    from src.workflow.functions.intracellular.update_gene_networks import _get_local_environment

    # Create mock substance concentrations similar to what real simulator returns
    mock_substance_concentrations = {
        'Oxygen': {(50, 50): 0.2, (75, 75): 0.2, (100, 100): 0.2},
        'Glucose': {(50, 50): 0.3, (75, 75): 0.3, (100, 100): 0.3},
        'Lactate': {(50, 50): 0.1, (75, 75): 0.1, (100, 100): 0.1},
    }

    local_env = _get_local_environment((50, 50), mock_substance_concentrations)
    print(f"    Mock local_env keys: {list(local_env.keys())}")
    print(f"    Mock local_env: {local_env}")
    print(f"    Associations keys: {list(config.associations.keys())}")

    result = update_gene_networks(context)
    print(f"    update_gene_networks returned: {result}")

    # Check gene states after update
    print("\n[7] Gene states after workflow update:")
    for cell_id, cell in population.state.cells.items():
        gs = cell.state.gene_states
        mito = gs.get('mitoATP', 'NOT_SET')
        glyco = gs.get('glycoATP', 'NOT_SET')
        print(f"    {cell_id}: mitoATP={mito}, glycoATP={glyco}")

    # Check if get_cell_color would work
    print("\n[8] Testing get_cell_color function...")
    if population.custom_functions and hasattr(population.custom_functions, 'get_cell_color'):
        for cell_id, cell in population.state.cells.items():
            color = population.custom_functions.get_cell_color(
                cell=cell,
                gene_states=cell.state.gene_states,
                config=config
            )
            print(f"    {cell_id}: color = {color}")
    else:
        print("    ERROR: get_cell_color not found in custom_functions!")
        print(f"    custom_functions = {population.custom_functions}")

if __name__ == '__main__':
    main()

