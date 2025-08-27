#!/usr/bin/env python3
"""
Debug script to check MCT1_stimulus threshold application in the simulation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np
from config.config import MicroCConfig
from simulation.multi_substance_simulator import MultiSubstanceSimulator
from biology.population import CellPopulation
from pathlib import Path

def main():
    # Load config
    config_path = "tests/jayatilake_experiment/jayatilake_experiment_config.yaml"
    config = MicroCConfig.load_from_yaml(Path(config_path))
    
    print("=== MCT1_stimulus Threshold Debug ===")
    print(f"Config: {config_path}")
    print()
    
    # Check threshold configuration
    print(" THRESHOLD CONFIGURATION:")
    if 'MCT1_stimulus' in config.thresholds:
        threshold_config = config.thresholds['MCT1_stimulus']
        print(f"  MCT1_stimulus threshold: {threshold_config.threshold}")
    else:
        print("  [!] MCT1_stimulus threshold NOT FOUND!")
        return
    
    # Check association
    print("\n ASSOCIATION CONFIGURATION:")
    if 'Lactate' in config.associations:
        association = config.associations['Lactate']
        print(f"  Lactate -> {association}")
    else:
        print("  [!] Lactate association NOT FOUND!")
        return
    
    # Initialize simulator
    print("\n[RUN] INITIALIZING SIMULATOR...")
    simulator = MultiSubstanceSimulator(config)
    
    # Get initial lactate concentrations
    lactate_concentrations = simulator.state.substances['Lactate'].concentrations
    print(f"  Lactate range: {np.min(lactate_concentrations):.6f} - {np.max(lactate_concentrations):.6f} mM")
    
    # Test threshold application at different positions
    print("\n TESTING THRESHOLD APPLICATION:")
    
    # Test center position (should have high lactate)
    center_x = config.domain.nx // 2
    center_y = config.domain.ny // 2
    center_pos = (center_x, center_y)
    
    # Test edge position (should have low lactate)
    edge_x = 5
    edge_y = 5
    edge_pos = (edge_x, edge_y)
    
    positions = [
        ("Center", center_pos),
        ("Edge", edge_pos)
    ]
    
    for pos_name, (x, y) in positions:
        print(f"\n  {pos_name} position ({x}, {y}):")
        
        # Get lactate concentration
        lactate_conc = lactate_concentrations[y, x]  # Note: y,x order for numpy arrays
        print(f"    Lactate concentration: {lactate_conc:.6f} mM")
        
        # Apply threshold manually
        threshold = config.thresholds['MCT1_stimulus'].threshold
        mct1_stimulus_manual = lactate_conc > threshold
        print(f"    Manual threshold check: {lactate_conc:.6f} > {threshold} = {mct1_stimulus_manual}")
        
        # Get gene inputs from simulator
        gene_inputs = simulator.get_gene_inputs_at_position((x, y))
        if 'MCT1_stimulus' in gene_inputs:
            mct1_stimulus_sim = gene_inputs['MCT1_stimulus']
            print(f"    Simulator result: {mct1_stimulus_sim}")
            
            if mct1_stimulus_manual != mct1_stimulus_sim:
                print(f"    [!] MISMATCH! Manual: {mct1_stimulus_manual}, Simulator: {mct1_stimulus_sim}")
            else:
                print(f"    [+] MATCH!")
        else:
            print(f"    [!] MCT1_stimulus not found in gene inputs!")
    
    # Test with population
    print("\n TESTING WITH POPULATION:")
    population = CellPopulation(config)
    
    # Add a few test cells
    test_positions = [center_pos, edge_pos]
    
    for i, (pos_name, (x, y)) in enumerate(zip(["Center", "Edge"], test_positions)):
        print(f"\n  Adding cell at {pos_name} ({x}, {y}):")
        
        # Convert to physical coordinates
        dx = config.domain.size_x.meters / config.domain.nx
        dy = config.domain.size_y.meters / config.domain.ny
        phys_x = x * dx
        phys_y = y * dy
        
        # Add cell
        cell_id = population.add_cell(phys_x, phys_y)
        cell = population.cells[cell_id]
        
        print(f"    Cell ID: {cell_id}")
        print(f"    Physical position: ({phys_x:.6f}, {phys_y:.6f}) m")
        print(f"    Grid position: ({x}, {y})")
        
        # Get gene inputs for this cell
        gene_inputs = simulator.get_gene_inputs_at_position((x, y))
        print(f"    Gene inputs: {gene_inputs}")
        
        # Check MCT1_stimulus specifically
        if 'MCT1_stimulus' in gene_inputs:
            mct1_value = gene_inputs['MCT1_stimulus']
            print(f"    MCT1_stimulus: {mct1_value}")
            
            # Get lactate concentration
            lactate_conc = simulator.state.substances['Lactate'].get_concentration_at((x, y))
            print(f"    Lactate at position: {lactate_conc:.6f} mM")
            print(f"    Expected MCT1_stimulus: {lactate_conc > threshold}")

if __name__ == "__main__":
    main()
