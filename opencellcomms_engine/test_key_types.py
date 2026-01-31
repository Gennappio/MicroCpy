#!/usr/bin/env python
"""Test concentration grid key types vs cell position types"""
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
    size_x=Length(1500.0, "um"),
    size_y=Length(1500.0, "um"),
    size_z=None,
    nx=50,
    ny=50,
    nz=None,
    cell_height=Length(20.0, "um")
)

# Add substances with initial values
oxygen_config = SubstanceConfig(
    name='Oxygen',
    diffusion_coeff=1.0e-9,
    production_rate=0.0,
    uptake_rate=0.0,
    initial_value=Concentration(0.07, "mM"),
    boundary_value=Concentration(0.07, "mM"),
    boundary_type='fixed'
)

class MinimalConfig:
    def __init__(self):
        self.domain = domain
        self.substances = {'Oxygen': oxygen_config}

config = MinimalConfig()

# Create mesh manager and simulator
mesh_manager = MeshManager(domain)
simulator = MultiSubstanceSimulator(config, mesh_manager, verbose=False)

concs = simulator.get_substance_concentrations()

if concs and 'Oxygen' in concs:
    oxygen_grid = concs['Oxygen']
    sample_keys = list(oxygen_grid.keys())[:5]
    print("Sample concentration grid keys:", sample_keys)
    print("First key element type:", type(sample_keys[0][0]).__name__)

    # Test float vs int key match
    k = sample_keys[0]
    float_key = (float(k[0]), float(k[1]))
    int_key = (int(k[0]), int(k[1]))

    print()
    print(f"Original key {k} in grid: {k in oxygen_grid}")
    print(f"Float key {float_key} in grid: {float_key in oxygen_grid}")
    print(f"Int key {int_key} in grid: {int_key in oxygen_grid}")

    # Test cell position (38.0, 23.0) which we saw in debug
    test_pos = (38.0, 23.0)
    test_pos_int = (38, 23)
    print()
    print(f"Cell position {test_pos} in grid: {test_pos in oxygen_grid}")
    print(f"Cell position {test_pos_int} in grid: {test_pos_int in oxygen_grid}")

