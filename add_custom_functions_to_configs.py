#!/usr/bin/env python3
"""
Add custom_functions section to all multitest config files
"""

import os
import glob

def add_custom_functions_to_config(config_file):
    """Add custom_functions section to a config file if it doesn't exist"""
    
    # Read the file
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Check if custom_functions section already exists
    if 'custom_functions:' in content:
        print(f"✅ {config_file} already has custom_functions section")
        return
    
    # Add custom_functions section before the output_dir line
    custom_functions_section = """custom_functions: ../tests/multitest/custom_functions.py
"""
    
    # Find the output_dir line and insert before it
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if line.startswith('output_dir:'):
            # Insert custom_functions section before output_dir
            new_lines.append(custom_functions_section.rstrip())
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Write back to file
    new_content = '\n'.join(new_lines)
    with open(config_file, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Added custom_functions to {config_file}")

def main():
    """Add custom_functions to all multitest config files"""
    print("🔧 Adding custom_functions section to all multitest config files...")
    
    # Find all config files
    config_files = glob.glob('tests/multitest/config_*.yaml')
    config_files.sort()
    
    print(f"📁 Found {len(config_files)} config files")
    
    for config_file in config_files:
        add_custom_functions_to_config(config_file)
    
    print(f"\n🎉 Processed {len(config_files)} config files!")
    print("Now all configs will use metabolic state visualization!")

if __name__ == "__main__":
    main()
