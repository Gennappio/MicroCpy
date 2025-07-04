#!/usr/bin/env python3
"""
Simple test script for a single combination.
Uses minimal imports to avoid path issues.
"""

import os
import sys
import yaml
from pathlib import Path

def test_combination(combination_id):
    """Test a single combination by loading and validating the config."""
    config_file = f"tests/multitest/config_{combination_id:02d}.yaml"
    
    print(f"Testing Combination {combination_id:02d}")
    print("=" * 40)
    print(f"Config file: {config_file}")
    
    if not Path(config_file).exists():
        print(f"ERROR: Config file not found: {config_file}")
        return False
    
    try:
        # Load and validate config
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        print("✓ Config file loaded successfully")
        
        # Extract substance concentrations
        substances = config_data.get('substances', {})
        
        oxygen_conc = substances.get('Oxygen', {}).get('initial_value', 0)
        lactate_conc = substances.get('Lactate', {}).get('initial_value', 0)
        glucose_conc = substances.get('Glucose', {}).get('initial_value', 0)
        tgfa_conc = substances.get('TGFA', {}).get('initial_value', 0)
        
        print(f"\nSubstance concentrations:")
        print(f"  Oxygen:  {oxygen_conc:.3f} mM ({'HIGH' if oxygen_conc > 0.03 else 'LOW'})")
        print(f"  Lactate: {lactate_conc:.1f} mM ({'HIGH' if lactate_conc > 2.0 else 'LOW'})")
        print(f"  Glucose: {glucose_conc:.1f} mM ({'HIGH' if glucose_conc > 4.0 else 'LOW'})")
        print(f"  TGFA:    {tgfa_conc:.1e} mM ({'HIGH' if tgfa_conc > 1.0e-6 else 'LOW'})")
        
        # Validate key configuration sections
        required_sections = ['domain', 'time', 'substances', 'associations', 'thresholds', 'gene_network']
        missing_sections = []
        
        for section in required_sections:
            if section not in config_data:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"\nERROR: Missing required sections: {missing_sections}")
            return False
        
        print("✓ All required config sections present")
        
        # Check domain configuration
        domain = config_data['domain']
        if domain.get('nx') != 1 or domain.get('ny') != 1:
            print(f"ERROR: Expected 1x1 grid, got {domain.get('nx')}x{domain.get('ny')}")
            return False
        
        print("✓ Domain configured for single cell (1x1 grid)")
        
        # Check that diffusion is disabled
        diffusion_disabled = True
        for substance_name, substance_config in substances.items():
            if substance_config.get('diffusion_coeff', 1.0) != 0.0:
                print(f"WARNING: {substance_name} has non-zero diffusion coefficient")
                diffusion_disabled = False
        
        if diffusion_disabled:
            print("✓ Diffusion disabled for all substances")
        
        # Check output directories
        output_dir = config_data.get('output_dir', '')
        plots_dir = config_data.get('plots_dir', '')
        
        if f"combination_{combination_id:02d}" in output_dir and f"combination_{combination_id:02d}" in plots_dir:
            print("✓ Output directories configured correctly")
        else:
            print(f"WARNING: Output directories may not be unique for this combination")
        
        print(f"\nConfiguration validation PASSED for combination {combination_id:02d}")
        print(f"This combination represents: O2={'HIGH' if oxygen_conc > 0.03 else 'LOW'}, "
              f"Lac={'HIGH' if lactate_conc > 2.0 else 'LOW'}, "
              f"Gluc={'HIGH' if glucose_conc > 4.0 else 'LOW'}, "
              f"TGFA={'HIGH' if tgfa_conc > 1.0e-6 else 'LOW'}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to load/validate config: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python test_combination.py <combination_id>")
        print("   combination_id: 0-15 for individual test, 'all' for all tests")
        return
    
    arg = sys.argv[1]
    
    if arg.lower() == 'all':
        print("Testing All 16 Combinations")
        print("=" * 40)
        
        results = []
        for i in range(16):
            success = test_combination(i)
            results.append(success)
            print()  # Add spacing
        
        print("SUMMARY")
        print("=" * 40)
        print(f"Total combinations: 16")
        print(f"Successful: {sum(results)}")
        print(f"Failed: {16 - sum(results)}")
        
        if all(results):
            print("\n✓ All combinations configured correctly!")
            print("You can now run individual simulations using:")
            print("  python tests/multitest/test_combination.py <0-15>")
        else:
            failed = [i for i, success in enumerate(results) if not success]
            print(f"\nFailed combinations: {failed}")
    
    else:
        try:
            combination_id = int(arg)
            if 0 <= combination_id <= 15:
                test_combination(combination_id)
            else:
                print("ERROR: Combination ID must be between 0 and 15")
        except ValueError:
            print("ERROR: Invalid combination ID. Must be a number between 0-15 or 'all'")

if __name__ == "__main__":
    main()
