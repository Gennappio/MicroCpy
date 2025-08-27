#!/usr/bin/env python3
"""
Debug script to check oxygen concentrations and Oxygen_supply threshold application.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np
from src.config.config import MicroCConfig
from src.simulation.multi_substance_simulator import MultiSubstanceSimulator
from src.core.domain import MeshManager
from pathlib import Path

def main():
    # Load config
    config_path = "tests/jayatilake_experiment/jayatilake_experiment_config.yaml"
    config = MicroCConfig.load_from_yaml(Path(config_path))
    
    print("=== OXYGEN THRESHOLD DEBUG ===")
    print(f"Config: {config_path}")
    print()
    
    # Check threshold configuration
    print(" OXYGEN THRESHOLD CONFIGURATION:")
    if 'Oxygen_supply' in config.thresholds:
        threshold_config = config.thresholds['Oxygen_supply']
        print(f"  Oxygen_supply threshold: {threshold_config.threshold} mM")
    else:
        print("  [!] Oxygen_supply threshold NOT FOUND!")
        return
    
    # Check association
    print("\n ASSOCIATION CONFIGURATION:")
    if 'Oxygen' in config.associations:
        association = config.associations['Oxygen']
        print(f"  Oxygen -> {association}")
    else:
        print("  [!] Oxygen association NOT FOUND!")
        return
    
    # Initialize simulator
    print("\n[RUN] INITIALIZING SIMULATOR...")
    mesh_manager = MeshManager(config.domain)
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    
    # Get initial oxygen concentrations
    oxygen_concentrations = simulator.state.substances['Oxygen'].concentrations
    print(f"  Oxygen range: {np.min(oxygen_concentrations):.6f} - {np.max(oxygen_concentrations):.6f} mM")
    
    # Test threshold application at different positions
    print("\n TESTING OXYGEN THRESHOLD APPLICATION:")
    
    threshold = config.thresholds['Oxygen_supply'].threshold
    print(f"  Threshold: {threshold} mM")
    
    # Test center position (should have high oxygen)
    center_x = config.domain.nx // 2
    center_y = config.domain.ny // 2
    center_pos = (center_x, center_y)
    
    # Test edge position (should have low oxygen)
    edge_x = 5
    edge_y = 5
    edge_pos = (edge_x, edge_y)
    
    positions = [
        ("Center", center_pos),
        ("Edge", edge_pos)
    ]
    
    for pos_name, (x, y) in positions:
        print(f"\n  {pos_name} position ({x}, {y}):")
        
        # Get oxygen concentration
        oxygen_conc = oxygen_concentrations[y, x]  # Note: y,x order for numpy arrays
        print(f"    Oxygen concentration: {oxygen_conc:.6f} mM")
        
        # Apply threshold manually
        oxygen_supply_manual = oxygen_conc > threshold
        print(f"    Manual threshold check: {oxygen_conc:.6f} > {threshold} = {oxygen_supply_manual}")
        
        # Get gene inputs from simulator
        gene_inputs = simulator.get_gene_network_inputs_for_position((x, y))
        if 'Oxygen_supply' in gene_inputs:
            oxygen_supply_sim = gene_inputs['Oxygen_supply']
            print(f"    Simulator result: {oxygen_supply_sim}")
            
            if oxygen_supply_manual != oxygen_supply_sim:
                print(f"    [!] MISMATCH! Manual: {oxygen_supply_manual}, Simulator: {oxygen_supply_sim}")
            else:
                print(f"    [+] MATCH!")
        else:
            print(f"    [!] Oxygen_supply not found in gene inputs!")
    
    # Check distribution of oxygen values vs threshold
    print(f"\n[CHART] OXYGEN DISTRIBUTION ANALYSIS:")
    above_threshold = np.sum(oxygen_concentrations > threshold)
    below_threshold = np.sum(oxygen_concentrations <= threshold)
    total_cells = oxygen_concentrations.size
    
    print(f"  Total grid cells: {total_cells}")
    print(f"  Above threshold ({threshold} mM): {above_threshold} cells ({above_threshold/total_cells*100:.1f}%)")
    print(f"  Below threshold ({threshold} mM): {below_threshold} cells ({below_threshold/total_cells*100:.1f}%)")
    
    # Show some sample values
    print(f"\n SAMPLE OXYGEN VALUES:")
    flat_oxygen = oxygen_concentrations.flatten()
    sample_indices = np.linspace(0, len(flat_oxygen)-1, 10, dtype=int)
    for i, idx in enumerate(sample_indices):
        oxygen_val = flat_oxygen[idx]
        above = oxygen_val > threshold
        print(f"  Sample {i+1}: {oxygen_val:.6f} mM -> Oxygen_supply = {above}")

if __name__ == "__main__":
    main()
