#!/usr/bin/env python3
"""
Debug oxygen consumption issue - check gene network inputs and metabolism
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.config import MicroCConfig
from src.core.domain import MeshManager
from src.simulation.multi_substance_simulator import MultiSubstanceSimulator
from src.biology.gene_network import BooleanNetwork

def main():
    print("[SEARCH] DEBUGGING OXYGEN CONSUMPTION")
    print("=" * 50)
    
    # Load config
    config_path = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    config = MicroCConfig.load_from_yaml(config_path)

    # Create mesh manager and simulator
    mesh_manager = MeshManager(config.domain)
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    
    # Create gene network
    print(f"\n CREATING GENE NETWORK:")
    print(f"  BND file from config: {config.gene_network.bnd_file}")
    bnd_path = Path(config.gene_network.bnd_file)
    print(f"  BND path as Path object: {bnd_path}")
    print(f"  BND file exists: {bnd_path.exists()}")

    gene_network = BooleanNetwork(config)
    print(f"  Gene network created with {len(gene_network.nodes)} nodes")
    
    # Test position at center
    center_pos = (12, 12)  # Center of 25x25 grid
    
    print(f"\n Testing at position {center_pos}")
    
    # Get substance concentrations
    concentrations = {}
    for name, substance_state in simulator.state.substances.items():
        concentrations[name] = substance_state.get_concentration_at(center_pos)

    print(f"\n SUBSTANCE CONCENTRATIONS:")
    for substance, conc in sorted(concentrations.items()):
        print(f"  {substance}: {conc:.6f} mM")
    
    # Get gene network inputs
    gene_inputs = simulator.get_gene_network_inputs_for_position(center_pos)
    print(f"\n GENE NETWORK INPUTS:")
    for gene_input, state in sorted(gene_inputs.items()):
        print(f"  {gene_input}: {state}")
    
    # Check specific thresholds
    print(f"\n[TARGET] THRESHOLD ANALYSIS:")
    oxygen_conc = concentrations.get('Oxygen', 0.0)
    oxygen_threshold = config.thresholds['Oxygen_supply'].threshold
    oxygen_supply_expected = oxygen_conc > oxygen_threshold
    oxygen_supply_actual = gene_inputs.get('Oxygen_supply', False)
    
    print(f"  Oxygen concentration: {oxygen_conc:.6f} mM")
    print(f"  Oxygen threshold: {oxygen_threshold:.6f} mM")
    print(f"  Expected Oxygen_supply: {oxygen_supply_expected}")
    print(f"  Actual Oxygen_supply: {oxygen_supply_actual}")
    
    if oxygen_supply_expected != oxygen_supply_actual:
        print(f"  [!] MISMATCH!")
    else:
        print(f"  [+] CORRECT!")
    
    # Set gene inputs and run gene network with more steps
    gene_network.set_input_states(gene_inputs)
    print(f"\n RUNNING GENE NETWORK PROPAGATION:")
    print(f"  Initial gene inputs set: {len(gene_inputs)} inputs")

    # Check GLUT1 logic manually
    print(f"\n[SEARCH] MANUAL GLUT1 LOGIC CHECK:")
    current_states = gene_network.get_all_states()
    hif1 = current_states.get('HIF1', False)
    p53 = current_states.get('p53', False)
    myc = current_states.get('MYC', False)
    glut1i = current_states.get('GLUT1I', False)

    print(f"  HIF1: {hif1}")
    print(f"  p53: {p53} -> !p53: {not p53}")
    print(f"  MYC: {myc}")
    print(f"  GLUT1I: {glut1i} -> !GLUT1I: {not glut1i}")

    manual_glut1 = (hif1 or (not p53) or myc) and (not glut1i)
    actual_glut1 = current_states.get('GLUT1', False)
    print(f"  Manual GLUT1 = ({hif1} | {not p53} | {myc}) & {not glut1i} = {manual_glut1}")
    print(f"  Actual GLUT1 = {actual_glut1}")

    if manual_glut1 != actual_glut1:
        print(f"  [!] MISMATCH! Logic evaluation issue!")
        print(f"  [TOOL] APPLYING MANUAL FIX: Setting GLUT1 = True")
        gene_network.nodes['GLUT1'].current_state = True
    else:
        print(f"  [+] Logic evaluation correct")

    # Run multiple steps to allow propagation
    for step in range(5):
        gene_states = gene_network.step(1)
        print(f"  Step {step+1}: Updated genes")

        # Check key genes after each step
        glut1 = gene_states.get('GLUT1', False)
        cell_glucose = gene_states.get('Cell_Glucose', False)
        g6p = gene_states.get('G6P', False)
        tca = gene_states.get('TCA', False)
        mito_atp = gene_states.get('mitoATP', False)
        print(f"    GLUT1={glut1}, Cell_Glucose={cell_glucose}, G6P={g6p}, TCA={tca}, mitoATP={mito_atp}")

        if mito_atp:
            print(f"    [+] mitoATP activated at step {step+1}!")
            break
    
    print(f"\n GENE NETWORK STATES:")
    for gene, state in sorted(gene_states.items()):
        print(f"  {gene}: {state}")
    
    # Check metabolism-relevant genes
    print(f"\n[FAST] METABOLISM GENES:")
    mito_atp = gene_states.get('mitoATP', False)
    glyco_atp = gene_states.get('glycoATP', False)
    etc = gene_states.get('ETC', False)
    tca = gene_states.get('TCA', False)
    
    print(f"  TCA: {tca}")
    print(f"  ETC: {etc} (requires TCA & Oxygen_supply)")
    print(f"  mitoATP: {mito_atp} (requires ETC)")
    print(f"  glycoATP: {glyco_atp}")
    
    # Test metabolism calculation
    print(f"\n TESTING METABOLISM CALCULATION:")
    
    # Import custom functions
    sys.path.append('tests/jayatilake_experiment')
    import jayatilake_experiment_custom_functions as custom_funcs
    
    # Create fake cell state
    cell_state = {
        'gene_states': gene_states,
        'id': 'test_cell',
        'phenotype': 'Proliferation'
    }
    
    # Calculate metabolism
    reactions = custom_funcs.calculate_cell_metabolism(concentrations, cell_state, config)
    
    print(f"  Oxygen consumption: {reactions.get('Oxygen', 0.0):.2e} mol/s/cell")
    print(f"  Glucose consumption: {reactions.get('Glucose', 0.0):.2e} mol/s/cell")
    print(f"  Lactate production: {reactions.get('Lactate', 0.0):.2e} mol/s/cell")
    
    if reactions.get('Oxygen', 0.0) == 0.0:
        print(f"  [!] NO OXYGEN CONSUMPTION!")
        print(f"  [SEARCH] Checking why...")
        print(f"    mitoATP = {mito_atp} (needs to be True for oxygen consumption)")
        print(f"    glycoATP = {glyco_atp} (also consumes some oxygen)")
        
        if not mito_atp and not glyco_atp:
            print(f"    [!] Both mitoATP and glycoATP are False - no metabolism!")
        elif not mito_atp:
            print(f"    [WARNING]  Only glycoATP is active - limited oxygen consumption")
    else:
        print(f"  [+] OXYGEN CONSUMPTION DETECTED!")

if __name__ == "__main__":
    main()
