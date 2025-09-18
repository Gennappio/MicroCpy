#!/usr/bin/env python3
"""
Focused search for optimal mitoATP and glycoATP input combinations
"""

import subprocess
import tempfile
import os

def create_input_file(inputs_dict, filename):
    """Create an input file with specified input states"""
    with open(filename, 'w') as f:
        for input_name, state in inputs_dict.items():
            f.write(f"{input_name}: {str(state).lower()}\n")

def run_gene_network(input_file):
    """Run the gene network simulator and parse results"""
    try:
        cmd = [
            'python', 'gene_network_standalone.py',
            'tests/jayatilake_experiment/jaya_microc.bnd', input_file,
            '--runs', '100',
            '--steps', '50',
            '--target-nodes', 'mitoATP', 'glycoATP'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return None, None
            
        # Parse the output to extract mitoATP and glycoATP percentages
        lines = result.stdout.split('\n')
        mito_atp_pct = 0
        glyco_atp_pct = 0
        
        for line in lines:
            if 'mitoATP: ON' in line:
                try:
                    # Extract percentage from "mitoATP: ON 37/100 (37.0%)"
                    pct_str = line.split('(')[1].split('%')[0]
                    mito_atp_pct = float(pct_str)
                except:
                    pass
            elif 'glycoATP: ON' in line:
                try:
                    # Extract percentage from "glycoATP: ON 40/100 (40.0%)"
                    pct_str = line.split('(')[1].split('%')[0]
                    glyco_atp_pct = float(pct_str)
                except:
                    pass
        
        return mito_atp_pct, glyco_atp_pct
        
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def test_metabolic_conditions():
    """Test specific metabolic conditions"""
    
    print("🔍 Testing specific metabolic conditions for mitoATP and glycoATP")
    print("=" * 70)
    
    # Base inputs (all false except what we specify)
    base_inputs = {
        'Oxygen_supply': False,
        'Glucose_supply': False,
        'MCT1_stimulus': False,
        'Proton_level': False,
        'FGFR_stimulus': False,
        'EGFR_stimulus': False,
        'cMET_stimulus': False,
        'Growth_Inhibitor': False,
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
    
    # Test conditions based on biological knowledge
    test_conditions = [
        {
            'name': 'OXPHOS Only (O2+MCT1)',
            'inputs': {'Oxygen_supply': True, 'MCT1_stimulus': True},
            'expected': 'High mitoATP, Low glycoATP'
        },
        {
            'name': 'Glycolysis Only (Glucose+EGFR)',
            'inputs': {'Glucose_supply': True, 'EGFR_stimulus': True, 'Glucose': True},
            'expected': 'Low mitoATP, High glycoATP'
        },
        {
            'name': 'Both Pathways (O2+Glucose)',
            'inputs': {'Oxygen_supply': True, 'Glucose_supply': True, 'Glucose': True},
            'expected': 'High mitoATP, High glycoATP'
        },
        {
            'name': 'Hypoxic Glycolysis (Glucose only)',
            'inputs': {'Glucose_supply': True, 'Glucose': True},
            'expected': 'Low mitoATP, High glycoATP'
        },
        {
            'name': 'Growth Factor Stimulation',
            'inputs': {'Glucose_supply': True, 'EGFR_stimulus': True, 'FGFR_stimulus': True, 'Glucose': True},
            'expected': 'Variable mitoATP, High glycoATP'
        },
        {
            'name': 'Lactate Consumption (O2+MCT1)',
            'inputs': {'Oxygen_supply': True, 'MCT1_stimulus': True},
            'expected': 'High mitoATP, Low glycoATP'
        },
        {
            'name': 'Stressed Conditions (Growth Inhibitor)',
            'inputs': {'Glucose_supply': True, 'Growth_Inhibitor': True, 'Glucose': True},
            'expected': 'Low mitoATP, Variable glycoATP'
        },
        {
            'name': 'Optimal OXPHOS',
            'inputs': {'Oxygen_supply': True, 'MCT1_stimulus': True, 'FGFR_stimulus': True},
            'expected': 'Highest mitoATP'
        },
        {
            'name': 'Optimal Glycolysis',
            'inputs': {'Glucose_supply': True, 'EGFR_stimulus': True, 'cMET_stimulus': True, 'Glucose': True},
            'expected': 'Highest glycoATP'
        }
    ]
    
    results = []
    best_mito = {'name': '', 'score': 0, 'inputs': {}}
    best_glyco = {'name': '', 'score': 0, 'inputs': {}}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_filename = temp_file.name
    
    try:
        for condition in test_conditions:
            # Create input dictionary
            inputs_dict = base_inputs.copy()
            inputs_dict.update(condition['inputs'])
            
            # Create input file
            create_input_file(inputs_dict, temp_filename)
            
            # Run simulator
            mito_pct, glyco_pct = run_gene_network(temp_filename)
            
            if mito_pct is None:
                continue
            
            # Store results
            result = {
                'name': condition['name'],
                'mito_pct': mito_pct,
                'glyco_pct': glyco_pct,
                'expected': condition['expected'],
                'inputs': condition['inputs']
            }
            results.append(result)
            
            # Track best results
            if mito_pct > best_mito['score']:
                best_mito = {'name': condition['name'], 'score': mito_pct, 'inputs': inputs_dict.copy()}
            
            if glyco_pct > best_glyco['score']:
                best_glyco = {'name': condition['name'], 'score': glyco_pct, 'inputs': inputs_dict.copy()}
            
            # Print results
            print(f"\n{condition['name']}:")
            print(f"  mitoATP: {mito_pct:.1f}%")
            print(f"  glycoATP: {glyco_pct:.1f}%")
            print(f"  Expected: {condition['expected']}")
            print(f"  Active inputs: {[k for k, v in condition['inputs'].items() if v]}")
    
    finally:
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)
    
    return results, best_mito, best_glyco

def create_optimal_files(best_mito, best_glyco):
    """Create optimal input files"""
    
    print(f"\n📁 Creating optimal input files...")
    
    # Create mitoATP optimal file
    mito_filename = 'optimal_mitoATP_inputs.txt'
    create_input_file(best_mito['inputs'], mito_filename)
    print(f"✅ Created {mito_filename}")
    print(f"   Condition: {best_mito['name']}")
    print(f"   mitoATP activation: {best_mito['score']:.1f}%")
    
    # Create glycoATP optimal file  
    glyco_filename = 'optimal_glycoATP_inputs.txt'
    create_input_file(best_glyco['inputs'], glyco_filename)
    print(f"✅ Created {glyco_filename}")
    print(f"   Condition: {best_glyco['name']}")
    print(f"   glycoATP activation: {best_glyco['score']:.1f}%")
    
    return mito_filename, glyco_filename

if __name__ == "__main__":
    # Test metabolic conditions
    results, best_mito, best_glyco = test_metabolic_conditions()
    
    # Create optimal files
    mito_file, glyco_file = create_optimal_files(best_mito, best_glyco)
    
    # Summary
    print(f"\n🎯 SUMMARY:")
    print(f"=" * 50)
    print(f"Best mitoATP: {best_mito['name']} ({best_mito['score']:.1f}%)")
    print(f"Best glycoATP: {best_glyco['name']} ({best_glyco['score']:.1f}%)")
    print(f"\nFiles created:")
    print(f"  {mito_file}")
    print(f"  {glyco_file}")
