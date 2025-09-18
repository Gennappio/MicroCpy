#!/usr/bin/env python3
"""
Script to find optimal input combinations for mitoATP and glycoATP activation
using the standalone gene network simulator.
"""

import subprocess
import tempfile
import os
from itertools import product

def create_input_file(inputs_dict, filename):
    """Create an input file with specified input states"""
    with open(filename, 'w') as f:
        for input_name, state in inputs_dict.items():
            f.write(f"{input_name}: {str(state).lower()}\n")

def run_gene_network(bnd_file, input_file, runs=100, steps=50):
    """Run the gene network simulator and parse results"""
    try:
        cmd = [
            'python', 'gene_network_standalone.py',
            bnd_file, input_file,
            '--runs', str(runs),
            '--steps', str(steps),
            '--target-nodes', 'mitoATP', 'glycoATP'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Error running simulator: {result.stderr}")
            return None
            
        # Parse the output to extract mitoATP and glycoATP percentages
        lines = result.stdout.split('\n')
        mito_atp_pct = 0
        glyco_atp_pct = 0
        
        for line in lines:
            if 'mitoATP' in line and 'ON:' in line:
                try:
                    mito_atp_pct = float(line.split('ON:')[1].split('%')[0].strip())
                except:
                    pass
            elif 'glycoATP' in line and 'ON:' in line:
                try:
                    glyco_atp_pct = float(line.split('ON:')[1].split('%')[0].strip())
                except:
                    pass
        
        return mito_atp_pct, glyco_atp_pct
        
    except subprocess.TimeoutExpired:
        print("Simulator timed out")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def find_optimal_inputs():
    """Find optimal input combinations for mitoATP and glycoATP"""
    
    print("🔍 Finding optimal input combinations for mitoATP and glycoATP")
    print("=" * 60)
    
    # Key input nodes that are likely to affect metabolism
    key_inputs = {
        'Oxygen_supply': [True, False],
        'Glucose_supply': [True, False], 
        'MCT1_stimulus': [True, False],
        'Proton_level': [True, False],
        'FGFR_stimulus': [True, False],
        'EGFR_stimulus': [True, False],
        'cMET_stimulus': [True, False],
        'Growth_Inhibitor': [True, False]
    }
    
    # Fixed inputs (set to false for simplicity)
    fixed_inputs = {
        'DNA_damage': False,
        'TGFBR_stimulus': False,
        'GLUT1I': False,
        'GLUT1D': False,
        'MCT1I': False,
        'MCT1D': False,
        'MCT4I': False,
        'MCT4D': False,
        'EGFRI': False,
        'EGFRD': False,
        'FGFRI': False,
        'FGFRD': False,
        'cMETI': False,
        'cMETD': False,
        'GI': False,
        'FGF': False,
        'HGF': False,
        'Glucose': False
    }
    
    best_mito = {'inputs': None, 'score': 0}
    best_glyco = {'inputs': None, 'score': 0}
    
    # Generate all combinations of key inputs
    input_names = list(key_inputs.keys())
    input_combinations = list(product(*[key_inputs[name] for name in input_names]))
    
    print(f"Testing {len(input_combinations)} input combinations...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_filename = temp_file.name
    
    try:
        for i, combination in enumerate(input_combinations):
            # Create input dictionary
            inputs_dict = fixed_inputs.copy()
            for j, input_name in enumerate(input_names):
                inputs_dict[input_name] = combination[j]
            
            # Create input file
            create_input_file(inputs_dict, temp_filename)
            
            # Run simulator
            result = run_gene_network('tests/jayatilake_experiment/jaya_microc.bnd', temp_filename)
            
            if result is None:
                continue
                
            mito_pct, glyco_pct = result
            
            # Track best results
            if mito_pct > best_mito['score']:
                best_mito['score'] = mito_pct
                best_mito['inputs'] = inputs_dict.copy()
            
            if glyco_pct > best_glyco['score']:
                best_glyco['score'] = glyco_pct
                best_glyco['inputs'] = inputs_dict.copy()
            
            # Print progress
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i+1}/{len(input_combinations)} combinations tested")
                print(f"    Best mitoATP: {best_mito['score']:.1f}%")
                print(f"    Best glycoATP: {best_glyco['score']:.1f}%")
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)
    
    return best_mito, best_glyco

def create_optimal_input_files(best_mito, best_glyco):
    """Create input files for optimal conditions"""
    
    print(f"\n📁 Creating optimal input files...")
    
    # Create mitoATP optimal file
    mito_filename = 'optimal_mitoATP_inputs.txt'
    create_input_file(best_mito['inputs'], mito_filename)
    print(f"✅ Created {mito_filename} (mitoATP: {best_mito['score']:.1f}%)")
    
    # Create glycoATP optimal file  
    glyco_filename = 'optimal_glycoATP_inputs.txt'
    create_input_file(best_glyco['inputs'], glyco_filename)
    print(f"✅ Created {glyco_filename} (glycoATP: {best_glyco['score']:.1f}%)")
    
    return mito_filename, glyco_filename

def print_results(best_mito, best_glyco):
    """Print detailed results"""
    
    print(f"\n🎯 OPTIMAL INPUT COMBINATIONS FOUND")
    print("=" * 60)
    
    print(f"\n🔋 BEST mitoATP ACTIVATION ({best_mito['score']:.1f}%):")
    for input_name, state in best_mito['inputs'].items():
        if state:  # Only show inputs that are ON
            print(f"  ✅ {input_name}: {state}")
    
    print(f"\n🍯 BEST glycoATP ACTIVATION ({best_glyco['score']:.1f}%):")
    for input_name, state in best_glyco['inputs'].items():
        if state:  # Only show inputs that are ON
            print(f"  ✅ {input_name}: {state}")

if __name__ == "__main__":
    # Find optimal combinations
    best_mito, best_glyco = find_optimal_inputs()
    
    # Create input files
    mito_file, glyco_file = create_optimal_input_files(best_mito, best_glyco)
    
    # Print results
    print_results(best_mito, best_glyco)
    
    print(f"\n📋 SUMMARY:")
    print(f"  mitoATP optimal file: {mito_file}")
    print(f"  glycoATP optimal file: {glyco_file}")
    print(f"  mitoATP activation: {best_mito['score']:.1f}%")
    print(f"  glycoATP activation: {best_glyco['score']:.1f}%")
