#!/usr/bin/env python
"""Test simulator concentration lookup to debug the 'all none' issue."""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from src.simulation.multi_substance_simulator import MultiSubstanceSimulator
from src.core.domain import MeshManager
from src.core.units import Length, Concentration
from src.config.config import DomainConfig, SubstanceConfig

# Create real domain config - must use Length objects
domain = DomainConfig(
    dimensions=2,
    size_x=Length(3000.0, "um"),
    size_y=Length(3000.0, "um"),
    size_z=None,
    nx=150,
    ny=150,
    nz=None,
    cell_height=Length(20.0, "um")
)

# Add substances with initial values
oxygen_config = SubstanceConfig(
    name='Oxygen',
    diffusion_coeff=100000.0,
    production_rate=0.0,
    uptake_rate=0.0,
    initial_value=Concentration(0.07, "mM"),
    boundary_value=Concentration(0.07, "mM"),
    boundary_type='fixed'
)

glucose_config = SubstanceConfig(
    name='Glucose',
    diffusion_coeff=100000.0,
    production_rate=0.0,
    uptake_rate=0.0,
    initial_value=Concentration(0.1, "mM"),
    boundary_value=Concentration(0.1, "mM"),
    boundary_type='fixed'
)

class MinimalConfig:
    def __init__(self):
        self.domain = domain
        self.substances = {
            'Oxygen': oxygen_config,
            'Glucose': glucose_config
        }

config = MinimalConfig()

# Create mesh manager and simulator
mesh_manager = MeshManager(domain)
simulator = MultiSubstanceSimulator(config, mesh_manager, verbose=False)

print(f"Created simulator with {len(simulator.state.substances)} substances")

# Get substance concentrations
concs = simulator.get_substance_concentrations()
print(f"Substance concentration keys: {list(concs.keys())}")

for name, grid in concs.items():
    if grid:
        sample_pos = next(iter(grid.keys()))
        sample_val = grid[sample_pos]
        print(f"  {name}: {len(grid)} positions, sample at {sample_pos} = {sample_val:.6f}")
    else:
        print(f"  {name}: EMPTY!")

# Test lookup at a specific position - use cell position format (x, y)
test_pos = (75, 75)
print(f"\nTesting lookup at position {test_pos}:")
for name, grid in concs.items():
    if test_pos in grid:
        print(f"  {name}: {grid[test_pos]:.6f}")
    else:
        print(f"  {name}: NOT FOUND at {test_pos}")
        if grid:
            sample_keys = list(grid.keys())[:5]
            print(f"    Available positions (sample): {sample_keys}")

# Now test what a cell lookup would see
print("\n" + "="*60)
print("SIMULATING CELL LOOKUP")
print("="*60)

# Simulate what _get_local_environment does
def get_local_env(position, substance_concentrations):
    local_env = {}
    for substance_name, conc_grid in substance_concentrations.items():
        if position in conc_grid:
            local_env[substance_name] = conc_grid[position]
        else:
            local_env[substance_name] = 0.0
    return local_env

# Test with a few different positions
test_positions = [(75, 75), (0, 0), (100, 100), (50, 75)]
for pos in test_positions:
    local_env = get_local_env(pos, concs)
    print(f"Position {pos}: {local_env}")

# Check thresholds
print("\n" + "="*60)
print("CHECKING AGAINST THRESHOLDS")
print("="*60)

thresholds = {
    'Oxygen_supply': 0.022,
    'Glucose_supply': 0.05,
}
associations = {
    'Oxygen': 'Oxygen_supply',
    'Glucose': 'Glucose_supply',
}

for pos in test_positions:
    local_env = get_local_env(pos, concs)
    print(f"\nPosition {pos}:")
    for substance, gene in associations.items():
        conc = local_env.get(substance, 0.0)
        threshold = thresholds.get(gene, 0.0)
        gene_on = conc > threshold
        print(f"  {substance}: {conc:.4f} > {threshold:.4f} = {gene_on} -> {gene}={gene_on}")

