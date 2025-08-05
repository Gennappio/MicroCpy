#!/usr/bin/env python3
"""
Quick Inspector for MicroC Cell State Files

A lightweight tool for quick inspection of cell state and initial state files.
Provides essential information without detailed analysis.

Usage:
    python quick_inspect.py <file_path>
    python quick_inspect.py *.h5  # Inspect multiple files
"""

import h5py
import numpy as np
import json
import sys
from pathlib import Path
from typing import List

def inspect_file(file_path: str) -> None:
    """Quick inspection of a single file"""
    path = Path(file_path)
    
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"\n📁 {path.name}")
    print("─" * 50)
    
    try:
        with h5py.File(path, 'r') as f:
            # File size
            size_kb = path.stat().st_size / 1024
            print(f"📏 Size: {size_kb:.1f} KB")
            
            # Groups
            groups = list(f.keys())
            print(f"📊 Groups: {', '.join(groups)}")
            
            # Metadata
            if 'metadata' in f:
                meta = f['metadata']
                cell_count = meta.attrs.get('cell_count', 'unknown')
                timestamp = meta.attrs.get('timestamp', 'unknown')
                step = meta.attrs.get('step', 'unknown')
                
                print(f"🧬 Cells: {cell_count}")
                print(f"⏰ Created: {timestamp}")
                print(f"📈 Step: {step}")
                
                # Domain info
                if 'domain_info' in meta.attrs:
                    try:
                        domain = json.loads(meta.attrs['domain_info'])
                        dims = domain['dimensions']
                        grid = f"{domain['nx']}×{domain['ny']}"
                        if dims == 3:
                            grid += f"×{domain.get('nz', 1)}"
                        print(f"🌐 Domain: {dims}D, {grid}")
                    except:
                        pass
            
            # Gene data
            if 'gene_states' in f:
                gene_count = f['gene_states']['gene_names'].shape[0]
                print(f"🧬 Genes: {gene_count}")
                
                # Quick gene activation stats
                states = f['gene_states']['states'][:]
                avg_activation = states.mean()
                print(f"📊 Avg activation: {avg_activation:.3f}")
            
            # Cell positions
            if 'cells' in f:
                positions = f['cells']['positions'][:]
                dims = positions.shape[1]
                
                # Position ranges
                x_range = f"{positions[:, 0].min():.2e} - {positions[:, 0].max():.2e}"
                y_range = f"{positions[:, 1].min():.2e} - {positions[:, 1].max():.2e}"
                print(f"📍 X range: {x_range}")
                print(f"📍 Y range: {y_range}")
                
                if dims > 2:
                    z_range = f"{positions[:, 2].min():.2e} - {positions[:, 2].max():.2e}"
                    print(f"📍 Z range: {z_range}")
                
                # Phenotypes
                phenotypes = [p.decode('utf-8') for p in f['cells']['phenotypes'][:]]
                unique_phenotypes, counts = np.unique(phenotypes, return_counts=True)
                print(f"🎭 Phenotypes: {', '.join([f'{p}({c})' for p, c in zip(unique_phenotypes, counts)])}")
            
            print("✅ Valid file")
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_inspect.py <file_path> [file_path2] ...")
        print("       python quick_inspect.py *.h5")
        sys.exit(1)
    
    print("🔍 MicroC Cell State Quick Inspector")
    print("=" * 60)
    
    file_paths = sys.argv[1:]
    
    # Expand wildcards if needed
    expanded_paths = []
    for path_str in file_paths:
        path = Path(path_str)
        if '*' in path_str or '?' in path_str:
            # Handle wildcards
            parent = path.parent if path.parent != Path('.') else Path.cwd()
            pattern = path.name
            expanded_paths.extend(parent.glob(pattern))
        else:
            expanded_paths.append(path)
    
    # Remove duplicates and sort
    unique_paths = sorted(set(str(p) for p in expanded_paths))
    
    if not unique_paths:
        print("❌ No files found")
        sys.exit(1)
    
    print(f"📂 Found {len(unique_paths)} file(s)")
    
    for file_path in unique_paths:
        inspect_file(file_path)
    
    print(f"\n✅ Inspection completed for {len(unique_paths)} file(s)")

if __name__ == "__main__":
    main()
