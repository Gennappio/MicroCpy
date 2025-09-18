#!/usr/bin/env python3
"""
Debug script to investigate why lactate is not being produced.
Check gene states, metabolism function calls, and reaction terms.
"""

import sys
import os
sys.path.append('src')

import yaml
from pathlib import Path

def check_gene_network_file():
    """Check if gene network file has correct lactate-related genes"""
    
    print("🧬 CHECKING GENE NETWORK CONFIGURATION")
    print("=" * 50)
    
    # Check if gene network file exists
    gene_file = Path("tests/jayatilake_experiment/jayatilake_experiment.bnd")
    if not gene_file.exists():
        print(f"❌ Gene network file not found: {gene_file}")
        return
    
    print(f"✅ Gene network file found: {gene_file}")
    
    # Read gene network file
    with open(gene_file, 'r') as f:
        content = f.read()
    
    # Check for key genes
    key_genes = ['glycoATP', 'mitoATP', 'Oxygen_supply', 'Glucose_supply']
    
    print(f"\n📊 KEY GENE PRESENCE:")
    for gene in key_genes:
        if gene in content:
            print(f"   ✅ {gene}: Found")
        else:
            print(f"   ❌ {gene}: Missing")
    
    # Check glycoATP definition
    if 'glycoATP' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'glycoATP' in line and ('logic' in line or 'rate_up' in line):
                print(f"\n🔍 GLYCOATP DEFINITION (line {i+1}):")
                # Show context around glycoATP definition
                start = max(0, i-2)
                end = min(len(lines), i+5)
                for j in range(start, end):
                    marker = ">>> " if j == i else "    "
                    print(f"{marker}{j+1:3d}: {lines[j]}")
                break

def check_config_parameters():
    """Check configuration parameters that affect lactate production"""
    
    print(f"\n⚙️  CHECKING CONFIGURATION PARAMETERS")
    print("=" * 50)
    
    config_file = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Check key parameters
    key_params = [
        ('custom_parameters', 'glucose_vmax'),
        ('custom_parameters', 'oxygen_vmax'),
        ('custom_parameters', 'the_optimal_glucose'),
        ('custom_parameters', 'the_optimal_lactate'),
        ('custom_parameters', 'proton_coefficient')
    ]
    
    print(f"📊 KEY METABOLISM PARAMETERS:")
    for section, param in key_params:
        try:
            value = config[section][param]
            print(f"   ✅ {param}: {value}")
        except KeyError:
            print(f"   ❌ {param}: Missing from {section}")
    
    # Check initial conditions
    substances = ['Oxygen', 'Glucose', 'Lactate']
    print(f"\n📊 INITIAL CONDITIONS:")
    for substance in substances:
        try:
            if 'substances' in config and substance in config['substances']:
                initial = config['substances'][substance]['initial_value']
                boundary = config['substances'][substance]['boundary_value']
                print(f"   ✅ {substance}: initial={initial}, boundary={boundary}")
            else:
                print(f"   ❌ {substance}: Not found in substances")
        except KeyError as e:
            print(f"   ❌ {substance}: Missing key {e}")

def create_debug_metabolism_test():
    """Create a test to debug metabolism function directly"""
    
    print(f"\n🔬 CREATING METABOLISM DEBUG TEST")
    print("=" * 50)
    
    debug_code = '''
import sys
sys.path.append('tests/jayatilake_experiment')
from jayatilake_experiment_custom_functions import calculate_metabolism

# Test metabolism function directly
cell_state = {'atp_rate': 0.0}

# Test environment with good conditions for glycolysis
local_environment = {
    'Oxygen': 0.01,    # Low oxygen (should favor glycolysis)
    'Glucose': 5.0,    # High glucose
    'Lactate': 1.0,    # Some lactate
    'H': 1e-7,         # Neutral pH
    'TGFA': 4e-5, 'HGF': 0.0, 'FGF': 0.0, 'GI': 0.0,
    'EGFRD': 0.0, 'FGFRD': 0.0, 'cMETD': 0.0, 'MCT1D': 0.0, 'GLUT1D': 0.0
}

# Test different gene states
test_cases = [
    {'name': 'Glycolysis Only', 'genes': {'glycoATP': 1.0, 'mitoATP': 0.0}},
    {'name': 'OXPHOS Only', 'genes': {'glycoATP': 0.0, 'mitoATP': 1.0}},
    {'name': 'Both Pathways', 'genes': {'glycoATP': 1.0, 'mitoATP': 1.0}},
    {'name': 'No ATP', 'genes': {'glycoATP': 0.0, 'mitoATP': 0.0}},
]

print("🧪 METABOLISM FUNCTION TEST")
print("=" * 40)

for case in test_cases:
    print(f"\\n📊 {case['name']}:")
    print(f"   Gene states: {case['genes']}")
    
    try:
        reactions = calculate_metabolism(cell_state, local_environment, case['genes'])
        
        # Show key reactions
        key_substances = ['Glucose', 'Lactate', 'Oxygen', 'H']
        for substance in key_substances:
            rate = reactions.get(substance, 0.0)
            direction = "production" if rate > 0 else "consumption" if rate < 0 else "no change"
            print(f"   {substance}: {rate:.2e} ({direction})")
            
        atp_rate = cell_state.get('atp_rate', 0.0)
        print(f"   ATP rate: {atp_rate:.2e}")
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

print("\\n💡 EXPECTED RESULTS:")
print("   - Glycolysis Only: Glucose consumption, Lactate production")
print("   - OXPHOS Only: Oxygen consumption, minimal Lactate")
print("   - Both Pathways: Mixed metabolism")
print("   - No ATP: Minimal reactions")
'''
    
    # Write debug test file
    with open('debug_metabolism_direct.py', 'w') as f:
        f.write(debug_code)
    
    print(f"✅ Created debug_metabolism_direct.py")
    print(f"   Run with: python debug_metabolism_direct.py")

def check_simulation_output():
    """Check if simulation is producing any output"""
    
    print(f"\n📊 CHECKING SIMULATION OUTPUT")
    print("=" * 50)
    
    # Check for recent result files
    results_dir = Path("results/jayatilake_experiment")
    if results_dir.exists():
        files = list(results_dir.glob("*.csv"))
        if files:
            latest_file = max(files, key=lambda f: f.stat().st_mtime)
            print(f"✅ Latest result file: {latest_file}")
            
            # Check file size
            size = latest_file.stat().st_size
            print(f"   File size: {size} bytes")
            
            if size > 0:
                # Read first few lines
                with open(latest_file, 'r') as f:
                    lines = f.readlines()[:10]
                print(f"   First few lines:")
                for i, line in enumerate(lines):
                    print(f"   {i+1}: {line.strip()}")
            else:
                print(f"   ❌ File is empty")
        else:
            print(f"❌ No CSV files found in {results_dir}")
    else:
        print(f"❌ Results directory not found: {results_dir}")

if __name__ == "__main__":
    print("🔍 LACTATE PRODUCTION DEBUG ANALYSIS")
    print("=" * 60)
    
    check_gene_network_file()
    check_config_parameters()
    create_debug_metabolism_test()
    check_simulation_output()
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"   1. Run: python debug_metabolism_direct.py")
    print(f"   2. Check gene network initialization")
    print(f"   3. Verify cell placement and gene states")
    print(f"   4. Check if metabolism function is being called")
