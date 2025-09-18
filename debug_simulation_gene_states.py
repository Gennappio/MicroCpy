#!/usr/bin/env python3
"""
Debug script to trace gene states during actual MicroC simulation.
"""

import sys
sys.path.append('src')

from config.config import MicroCConfig
from pathlib import Path
from simulation.orchestrator import TimescaleOrchestrator

def debug_simulation_gene_states():
    """Debug gene states during actual simulation"""
    
    print("🔍 DEBUGGING GENE STATES DURING SIMULATION")
    print("="*60)
    
    # Load config
    config_path = "tests/multitest/config_O2high_Lachigh_Gluchigh_TGFAhigh.yaml"
    config = MicroCConfig.load_from_yaml(Path(config_path))
    
    print(f"📁 Loaded config: {config_path}")
    
    # Create orchestrator
    orchestrator = TimescaleOrchestrator(config)
    
    print(f"🚀 Created orchestrator")
    
    # Get initial cell states
    print(f"\n📊 INITIAL CELL STATES:")
    for cell_id, cell in orchestrator.population.state.cells.items():
        gene_states = cell.state.gene_states
        print(f"  Cell {cell_id[:8]}:")
        print(f"    Position: {cell.state.position}")
        print(f"    Phenotype: {cell.state.phenotype}")
        if gene_states:
            for gene in ['glycoATP', 'mitoATP', 'Apoptosis', 'Necrosis', 'Proliferation', 'Growth_Arrest']:
                if gene in gene_states:
                    print(f"    {gene}: {gene_states[gene]}")
        else:
            print(f"    Gene states: None")
    
    # Run one step
    print(f"\n🔄 RUNNING ONE SIMULATION STEP...")
    orchestrator.step()
    
    # Get updated cell states
    print(f"\n📊 UPDATED CELL STATES:")
    for cell_id, cell in orchestrator.population.state.cells.items():
        gene_states = cell.state.gene_states
        print(f"  Cell {cell_id[:8]}:")
        print(f"    Position: {cell.state.position}")
        print(f"    Phenotype: {cell.state.phenotype}")
        if gene_states:
            for gene in ['glycoATP', 'mitoATP', 'Apoptosis', 'Necrosis', 'Proliferation', 'Growth_Arrest']:
                if gene in gene_states:
                    print(f"    {gene}: {gene_states[gene]}")
        else:
            print(f"    Gene states: None")
    
    # Check cell colors
    print(f"\n🎨 CELL COLORS:")
    for cell_id, cell in orchestrator.population.state.cells.items():
        gene_states = cell.state.gene_states or {}
        
        # Use the same coloring logic as the custom function
        if gene_states.get('Necrosis', False):
            color = "black"
        elif gene_states.get('Apoptosis', False):
            color = "red"
        else:
            glyco_active = gene_states.get('glycoATP', False)
            mito_active = gene_states.get('mitoATP', False)
            
            if glyco_active and not mito_active:
                color = "green"      # Glycolysis only
            elif not glyco_active and mito_active:
                color = "blue"       # OXPHOS only
            elif glyco_active and mito_active:
                color = "violet"     # Mixed metabolism
            else:
                color = "gray"       # Quiescent
        
        print(f"  Cell {cell_id[:8]}: {color} (glycoATP={gene_states.get('glycoATP', False)}, mitoATP={gene_states.get('mitoATP', False)})")

if __name__ == "__main__":
    debug_simulation_gene_states()
