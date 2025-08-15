#!/usr/bin/env python3
"""
Simple test script to verify VTK loading functionality
"""

import sys
import os
sys.path.append('src')

from src.io.initial_state import VTKCellLoader
from src.config.config import MicroCConfig

def test_vtk_loading():
    """Test VTK loading functionality"""
    
    # Test VTK file path
    vtk_file = "tools/generated_h5/tumor_core4_cells.vtk"
    
    if not os.path.exists(vtk_file):
        print(f"[ERROR] VTK file not found: {vtk_file}")
        return
    
    print(f"[TEST] Testing VTK loading with: {vtk_file}")
    
    try:
        # Load VTK file
        loader = VTKCellLoader(vtk_file)
        
        # Get results
        positions = loader.get_cell_positions()
        cell_size = loader.get_cell_size_um()
        cell_count = loader.get_cell_count()
        
        print(f"[OK] VTK loading successful!")
        print(f"  Cell count: {cell_count}")
        print(f"  Cell size: {cell_size:.2f} um")
        print(f"  Position count: {len(positions)}")
        
        # Print first few positions
        print(f"[DEBUG] First 5 positions:")
        for i, pos in enumerate(positions[:5]):
            print(f"  Cell {i}: {pos} (dimensions: {len(pos)})")
        
        # Check position dimensions
        if positions:
            pos_dims = len(positions[0])
            print(f"[INFO] All positions are {pos_dims}D")
            
            # Verify all positions have same dimensions
            all_same_dim = all(len(pos) == pos_dims for pos in positions)
            print(f"[INFO] All positions have consistent dimensions: {all_same_dim}")
        
    except Exception as e:
        print(f"[ERROR] VTK loading failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vtk_loading()
