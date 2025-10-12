#!/usr/bin/env python3

"""
Quick debug script to check if diffusion is actually working
"""

import sys
import os
from pathlib import Path

# Add src to path like run_sim.py does
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "config"))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from src.config.config import MicroCConfig
from src.core.domain import MeshManager
from src.simulation.multi_substance_simulator import MultiSubstanceSimulator

def debug_diffusion():
    """Test diffusion with a simple setup"""
    
    # Load config
    config_path = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    config = MicroCConfig.load_from_yaml(config_path)
    
    # Create mesh manager and simulator
    mesh_manager = MeshManager(config.domain)
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    
    print("[SEARCH] DEBUGGING DIFFUSION FIX")
    print("=" * 50)
    
    # Get initial concentrations
    initial_oxygen = simulator.state.substances['Oxygen'].concentrations.copy()
    initial_lactate = simulator.state.substances['Lactate'].concentrations.copy()
    
    print(f"Initial Oxygen - Min: {np.min(initial_oxygen):.6f}, Max: {np.max(initial_oxygen):.6f}, Mean: {np.mean(initial_oxygen):.6f}")
    print(f"Initial Lactate - Min: {np.min(initial_lactate):.6f}, Max: {np.max(initial_lactate):.6f}, Mean: {np.mean(initial_lactate):.6f}")
    
    # Create some dummy reactions (cells consuming oxygen, producing lactate)
    reactions = {}

    # Convert grid indices to physical coordinates (meters)
    # Domain is 500 um = 0.0005 m, grid is 25x25, so each cell is 20 um = 0.00002 m
    dx = config.domain.size_x.meters / config.domain.nx  # 0.00002 m per grid cell
    dy = config.domain.size_y.meters / config.domain.ny  # 0.00002 m per grid cell

    # Add some cells in the center that consume oxygen and produce lactate
    center_x, center_y = 12, 12  # Center of 25x25 grid
    for grid_dx in range(-2, 3):
        for grid_dy in range(-2, 3):
            grid_x, grid_y = center_x + grid_dx, center_y + grid_dy
            if 0 <= grid_x < 25 and 0 <= grid_y < 25:
                # Convert grid indices to physical coordinates (meters)
                x_meters = grid_x * dx
                y_meters = grid_y * dy
                reactions[(x_meters, y_meters)] = {
                    'Oxygen': -0.001,  # Consume oxygen
                    'Lactate': 0.0005  # Produce lactate
                }
    
    print(f"\n Added reactions at {len(reactions)} grid points around center ({center_x}, {center_y})")
    
    # Run diffusion update
    print("\n Running diffusion update...")
    simulator.update(reactions)
    
    # Get final concentrations
    final_oxygen = simulator.state.substances['Oxygen'].concentrations.copy()
    final_lactate = simulator.state.substances['Lactate'].concentrations.copy()
    
    print(f"\nFinal Oxygen - Min: {np.min(final_oxygen):.6f}, Max: {np.max(final_oxygen):.6f}, Mean: {np.mean(final_oxygen):.6f}")
    print(f"Final Lactate - Min: {np.min(final_lactate):.6f}, Max: {np.max(final_lactate):.6f}, Mean: {np.mean(final_lactate):.6f}")
    
    # Check if concentrations changed
    oxygen_changed = not np.allclose(initial_oxygen, final_oxygen, atol=1e-8)
    lactate_changed = not np.allclose(initial_lactate, final_lactate, atol=1e-8)
    
    print(f"\n[CHART] RESULTS:")
    print(f"Oxygen concentrations changed: {oxygen_changed}")
    print(f"Lactate concentrations changed: {lactate_changed}")
    
    if oxygen_changed:
        oxygen_diff = np.abs(final_oxygen - initial_oxygen)
        max_change_idx = np.unravel_index(np.argmax(oxygen_diff), oxygen_diff.shape)
        print(f"Max oxygen change: {np.max(oxygen_diff):.8f} at position {max_change_idx}")
        
        # Check center vs edges (handle 3D indexing)
        center_oxygen = final_oxygen[center_x, center_y, 0]  # z=0 for 3D
        edge_oxygen = final_oxygen[0, 0, 0]  # z=0 for 3D
        print(f"Center oxygen: {float(center_oxygen):.6f}, Edge oxygen: {float(edge_oxygen):.6f}")
        
    if lactate_changed:
        lactate_diff = np.abs(final_lactate - initial_lactate)
        max_change_idx = np.unravel_index(np.argmax(lactate_diff), lactate_diff.shape)
        print(f"Max lactate change: {np.max(lactate_diff):.8f} at position {max_change_idx}")
        
        # Check center vs edges (handle 3D indexing)
        center_lactate = final_lactate[center_x, center_y, 0]  # z=0 for 3D
        edge_lactate = final_lactate[0, 0, 0]  # z=0 for 3D
        print(f"Center lactate: {float(center_lactate):.6f}, Edge lactate: {float(edge_lactate):.6f}")
    
    # Overall assessment
    if oxygen_changed and lactate_changed:
        print("\n[+] DIFFUSION IS WORKING! Concentrations changed as expected.")
    else:
        print("\n[!] DIFFUSION IS NOT WORKING! Concentrations did not change.")
        
    return oxygen_changed and lactate_changed

if __name__ == "__main__":
    debug_diffusion()
