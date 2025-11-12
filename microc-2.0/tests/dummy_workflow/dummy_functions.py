"""
Dummy workflow functions for testing custom function nodes in GUI.

These functions demonstrate how to write custom workflow functions
that can be used in the workflow system.
"""

import numpy as np


def initialize_dummy_cells(context, num_cells=10, initial_energy=100.0):
    """
    Initialize dummy cells with random positions and energy.
    
    Parameters:
    - num_cells: Number of cells to create
    - initial_energy: Starting energy for each cell
    """
    print(f"[DUMMY] Initializing {num_cells} cells with energy={initial_energy}")
    
    # Access population from context
    population = context['population']
    
    # Create dummy cells
    for i in range(num_cells):
        x = np.random.uniform(0, 100)
        y = np.random.uniform(0, 100)
        z = np.random.uniform(0, 100)
        
        print(f"  Cell {i}: position=({x:.1f}, {y:.1f}, {z:.1f}), energy={initial_energy}")
    
    print(f"[DUMMY] Initialization complete!")
    return True


def update_cell_metabolism(context, glucose_rate=1.5, oxygen_threshold=0.5, enable_warburg=True):
    """
    Update cell metabolism based on glucose and oxygen availability.
    
    Parameters:
    - glucose_rate: Rate of glucose consumption
    - oxygen_threshold: Oxygen level threshold for aerobic metabolism
    - enable_warburg: Enable Warburg effect (aerobic glycolysis)
    """
    print(f"[DUMMY] Updating cell metabolism:")
    print(f"  glucose_rate={glucose_rate}")
    print(f"  oxygen_threshold={oxygen_threshold}")
    print(f"  enable_warburg={enable_warburg}")
    
    population = context['population']
    timestep = context.get('timestep', 0)
    
    print(f"  Timestep: {timestep}")
    print(f"  Processing metabolism for cells...")
    
    # Simulate metabolism calculation
    energy_produced = glucose_rate * 2.0
    if enable_warburg:
        energy_produced *= 1.5
        print(f"  Warburg effect active! Energy boost: {energy_produced}")
    
    print(f"[DUMMY] Metabolism update complete!")
    return True


def calculate_cell_division(context, division_threshold=200.0, division_probability=0.8):
    """
    Calculate which cells should divide based on energy threshold.
    
    Parameters:
    - division_threshold: Energy threshold for division
    - division_probability: Probability of division when threshold is met
    """
    print(f"[DUMMY] Calculating cell division:")
    print(f"  division_threshold={division_threshold}")
    print(f"  division_probability={division_probability}")
    
    population = context['population']
    timestep = context.get('timestep', 0)
    
    # Simulate division
    num_divisions = np.random.randint(0, 3)
    print(f"  {num_divisions} cells ready to divide")
    
    for i in range(num_divisions):
        print(f"    Cell {i} dividing...")
    
    print(f"[DUMMY] Division calculation complete!")
    return True


def diffuse_nutrients(context, diffusion_coefficient=0.1, decay_rate=0.01):
    """
    Simulate nutrient diffusion in the environment.
    
    Parameters:
    - diffusion_coefficient: Rate of nutrient diffusion
    - decay_rate: Rate of nutrient decay
    """
    print(f"[DUMMY] Diffusing nutrients:")
    print(f"  diffusion_coefficient={diffusion_coefficient}")
    print(f"  decay_rate={decay_rate}")
    
    mesh = context.get('mesh')
    timestep = context.get('timestep', 0)
    
    print(f"  Timestep: {timestep}")
    print(f"  Applying diffusion equation...")
    print(f"  Applying decay...")
    
    print(f"[DUMMY] Nutrient diffusion complete!")
    return True


def cell_cell_signaling(context, signal_range=10.0, signal_strength=1.0, enable_quorum=False):
    """
    Simulate cell-cell signaling and communication.
    
    Parameters:
    - signal_range: Maximum distance for signaling
    - signal_strength: Strength of the signal
    - enable_quorum: Enable quorum sensing behavior
    """
    print(f"[DUMMY] Processing cell-cell signaling:")
    print(f"  signal_range={signal_range}")
    print(f"  signal_strength={signal_strength}")
    print(f"  enable_quorum={enable_quorum}")
    
    population = context['population']
    
    # Simulate signaling
    num_signals = np.random.randint(5, 15)
    print(f"  {num_signals} signaling events detected")
    
    if enable_quorum:
        print(f"  Quorum sensing active!")
        print(f"  Collective behavior triggered")
    
    print(f"[DUMMY] Cell-cell signaling complete!")
    return True


def export_dummy_data(context, output_format="csv", include_positions=True, include_energy=True):
    """
    Export simulation data to file.
    
    Parameters:
    - output_format: Format for export (csv, json, vtk)
    - include_positions: Include cell positions in export
    - include_energy: Include cell energy levels in export
    """
    print(f"[DUMMY] Exporting data:")
    print(f"  output_format={output_format}")
    print(f"  include_positions={include_positions}")
    print(f"  include_energy={include_energy}")
    
    timestep = context.get('timestep', 0)
    output_dir = context.get('output_dir', 'results')
    
    print(f"  Timestep: {timestep}")
    print(f"  Output directory: {output_dir}")
    print(f"  Writing data to file...")
    
    print(f"[DUMMY] Data export complete!")
    return True


def custom_gene_regulation(context, gene_expression_rate=0.5, protein_degradation=0.1):
    """
    Custom gene regulatory network update.
    
    Parameters:
    - gene_expression_rate: Rate of gene expression
    - protein_degradation: Rate of protein degradation
    """
    print(f"[DUMMY] Updating gene regulation:")
    print(f"  gene_expression_rate={gene_expression_rate}")
    print(f"  protein_degradation={protein_degradation}")
    
    population = context['population']
    
    print(f"  Updating gene networks for all cells...")
    print(f"  Calculating protein levels...")
    
    print(f"[DUMMY] Gene regulation update complete!")
    return True

