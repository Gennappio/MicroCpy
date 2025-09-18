#!/usr/bin/env python3
"""
Fix all multitest configuration files to have biologically realistic concentrations.
"""

import os
import re
import glob

def fix_concentrations():
    """Fix concentration values in all multitest config files."""
    
    # Define correct concentration ranges based on biological thresholds
    # Optimal thresholds: glucose=0.04, lactate=0.04, oxygen=0.005
    concentrations = {
        'Gluclow': {'glucose': 0.01},    # Below optimal threshold
        'Gluchigh': {'glucose': 6.0},    # High, like original config
        'Laclow': {'lactate': 0.01},     # Below optimal threshold  
        'Lachigh': {'lactate': 1.0},     # High, like original boundary
        'O2low': {'oxygen': 0.01},       # Already correct
        'O2high': {'oxygen': 0.06},      # Already correct
        'TGFAlow': {'tgfa': 5.0e-07},    # Already correct
        'TGFAhigh': {'tgfa': 2.0e-06},   # Already correct
    }
    
    # Find all multitest config files
    config_files = glob.glob('tests/multitest/config_*.yaml')
    
    print(f"Found {len(config_files)} config files to fix")
    
    for config_file in config_files:
        print(f"\nFixing {config_file}")
        
        # Read the file
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Determine what concentrations this file should have based on filename
        filename = os.path.basename(config_file)
        
        # Fix glucose concentrations
        if 'Gluclow' in filename:
            target_glucose = concentrations['Gluclow']['glucose']
            content = re.sub(
                r'(Glucose:.*?initial_value: )[\d.]+',
                f'\\g<1>{target_glucose}',
                content, flags=re.DOTALL
            )
            content = re.sub(
                r'(Glucose:.*?boundary_value: )[\d.]+',
                f'\\g<1>{target_glucose}',
                content, flags=re.DOTALL
            )
            print(f"  Set glucose to {target_glucose} mM (low)")
            
        elif 'Gluchigh' in filename:
            target_glucose = concentrations['Gluchigh']['glucose']
            content = re.sub(
                r'(Glucose:.*?initial_value: )[\d.]+',
                f'\\g<1>{target_glucose}',
                content, flags=re.DOTALL
            )
            content = re.sub(
                r'(Glucose:.*?boundary_value: )[\d.]+',
                f'\\g<1>{target_glucose}',
                content, flags=re.DOTALL
            )
            print(f"  Set glucose to {target_glucose} mM (high)")
        
        # Fix lactate concentrations
        if 'Laclow' in filename:
            target_lactate = concentrations['Laclow']['lactate']
            content = re.sub(
                r'(Lactate:.*?initial_value: )[\d.]+',
                f'\\g<1>{target_lactate}',
                content, flags=re.DOTALL
            )
            content = re.sub(
                r'(Lactate:.*?boundary_value: )[\d.]+',
                f'\\g<1>{target_lactate}',
                content, flags=re.DOTALL
            )
            print(f"  Set lactate to {target_lactate} mM (low)")
            
        elif 'Lachigh' in filename:
            target_lactate = concentrations['Lachigh']['lactate']
            content = re.sub(
                r'(Lactate:.*?initial_value: )[\d.]+',
                f'\\g<1>{target_lactate}',
                content, flags=re.DOTALL
            )
            content = re.sub(
                r'(Lactate:.*?boundary_value: )[\d.]+',
                f'\\g<1>{target_lactate}',
                content, flags=re.DOTALL
            )
            print(f"  Set lactate to {target_lactate} mM (high)")
        
        # Write the fixed content back
        with open(config_file, 'w') as f:
            f.write(content)
    
    print(f"\n✅ Fixed {len(config_files)} configuration files")
    print("\nNew concentration ranges:")
    print("  Glucose: 0.01 mM (low) / 6.0 mM (high)")
    print("  Lactate: 0.01 mM (low) / 1.0 mM (high)")
    print("  Oxygen: 0.01 mM (low) / 0.06 mM (high)")
    print("  TGFA: 5.0e-07 mM (low) / 2.0e-06 mM (high)")

if __name__ == "__main__":
    fix_concentrations()
