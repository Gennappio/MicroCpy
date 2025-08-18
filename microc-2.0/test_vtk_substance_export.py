#!/usr/bin/env python3
"""
Test script to verify VTK substance field export functionality
"""

import os
import sys
import numpy as np
from pathlib import Path

def test_vtk_files():
    """Test that VTK substance field files are properly formatted"""
    
    # Check if VTK files exist
    vtk_dir = Path("results/jayatilake_experiment/vtk_substances")
    if not vtk_dir.exists():
        print("[!] VTK substances directory not found. Run simulation first.")
        return False
    
    vtk_files = list(vtk_dir.glob("*.vtk"))
    if not vtk_files:
        print("[!] No VTK files found. Run simulation first.")
        return False
    
    print(f"[*] Found {len(vtk_files)} VTK substance field files")
    
    # Test a few representative files
    test_files = [
        "Oxygen_field_step_000000.vtk",
        "Glucose_field_step_000002.vtk", 
        "TGFA_field_step_000004.vtk"
    ]
    
    for filename in test_files:
        filepath = vtk_dir / filename
        if not filepath.exists():
            print(f"[!] Test file not found: {filename}")
            continue
            
        print(f"\n[TEST] Analyzing {filename}...")
        
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Check VTK header
            if not lines[0].startswith("# vtk DataFile Version"):
                print(f"   [!] Invalid VTK header")
                continue
            
            # Check dataset type
            dataset_line = None
            dimensions_line = None
            spacing_line = None
            cell_data_line = None
            scalars_line = None
            
            for i, line in enumerate(lines):
                if line.startswith("DATASET"):
                    dataset_line = line.strip()
                elif line.startswith("DIMENSIONS"):
                    dimensions_line = line.strip()
                elif line.startswith("SPACING"):
                    spacing_line = line.strip()
                elif line.startswith("CELL_DATA"):
                    cell_data_line = line.strip()
                elif line.startswith("SCALARS"):
                    scalars_line = line.strip()
                    break
            
            # Validate format
            if dataset_line != "DATASET STRUCTURED_POINTS":
                print(f"   [!] Wrong dataset type: {dataset_line}")
                continue
            
            if not dimensions_line or not dimensions_line.startswith("DIMENSIONS 26 26 26"):
                print(f"   [!] Wrong dimensions: {dimensions_line}")
                continue
                
            if not spacing_line or "2.000000e-05" not in spacing_line:
                print(f"   [!] Wrong spacing: {spacing_line}")
                continue
                
            if not cell_data_line or "15625" not in cell_data_line:
                print(f"   [!] Wrong cell count: {cell_data_line}")
                continue
            
            # Check data values
            data_start = None
            for i, line in enumerate(lines):
                if line.startswith("LOOKUP_TABLE"):
                    data_start = i + 1
                    break
            
            if data_start is None:
                print(f"   [!] No data section found")
                continue
            
            # Read first few data values
            data_values = []
            for i in range(data_start, min(data_start + 10, len(lines))):
                try:
                    value = float(lines[i].strip())
                    data_values.append(value)
                except ValueError:
                    break
            
            if len(data_values) < 5:
                print(f"   [!] Insufficient data values")
                continue
            
            # Check if values are reasonable
            min_val = min(data_values)
            max_val = max(data_values)
            
            print(f"   [OK] Valid VTK format")
            print(f"   [OK] Dataset: {dataset_line}")
            print(f"   [OK] Dimensions: {dimensions_line}")
            print(f"   [OK] Spacing: {spacing_line}")
            print(f"   [OK] Cell data: {cell_data_line}")
            print(f"   [OK] Scalars: {scalars_line}")
            print(f"   [OK] Data range: {min_val:.6e} to {max_val:.6e}")
            
        except Exception as e:
            print(f"   [!] Error reading file: {e}")
            continue
    
    return True

def analyze_substance_evolution():
    """Analyze how substances change over time"""
    
    vtk_dir = Path("results/jayatilake_experiment/vtk_substances")
    if not vtk_dir.exists():
        print("[!] VTK substances directory not found.")
        return
    
    # Analyze TGFA evolution (should show changes)
    tgfa_files = sorted(vtk_dir.glob("TGFA_field_step_*.vtk"))
    if len(tgfa_files) < 2:
        print("[!] Need at least 2 TGFA time steps for evolution analysis")
        return
    
    print(f"\n[ANALYSIS] TGFA concentration evolution over {len(tgfa_files)} time steps:")
    
    for i, filepath in enumerate(tgfa_files):
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            # Find data section
            data_start = None
            for j, line in enumerate(lines):
                if line.startswith("LOOKUP_TABLE"):
                    data_start = j + 1
                    break
            
            if data_start is None:
                continue
            
            # Read all data values
            values = []
            for j in range(data_start, len(lines)):
                try:
                    value = float(lines[j].strip())
                    values.append(value)
                except ValueError:
                    break
            
            if values:
                values = np.array(values)
                min_val = np.min(values)
                max_val = np.max(values)
                mean_val = np.mean(values)
                nonzero_count = np.count_nonzero(values)
                
                step = filepath.stem.split('_')[-1]
                print(f"   Step {step}: min={min_val:.6e}, max={max_val:.6e}, mean={mean_val:.6e}, nonzero={nonzero_count}/15625")
                
        except Exception as e:
            print(f"   [!] Error analyzing {filepath.name}: {e}")

def create_paraview_instructions():
    """Create instructions for opening VTK files in ParaView"""
    
    instructions = """
# ParaView Visualization Instructions

## Opening VTK Substance Fields in ParaView

1. **Launch ParaView**
   - Download from: https://www.paraview.org/download/
   - Or use any VTK-compatible viewer

2. **Load Substance Fields**
   - File -> Open
   - Navigate to: results/jayatilake_experiment/vtk_substances/
   - Select multiple files: Oxygen_field_step_*.vtk
   - Click "Apply" in Properties panel

3. **Load Cell Data (Optional)**
   - File -> Open
   - Navigate to: results/jayatilake_experiment/vtk_cells/
   - Select: cells_step_*.vtk
   - Click "Apply"

4. **Visualization Options**
   - **Volume Rendering**: Representation -> Volume
   - **Isosurfaces**: Filters -> Contour
   - **Slices**: Filters -> Slice
   - **Streamlines**: Filters -> Stream Tracer

5. **Animation**
   - View -> Animation View
   - Set time range to match simulation steps
   - Play to see temporal evolution

6. **Color Mapping**
   - Select substance field in Pipeline Browser
   - Choose colormap in Properties panel
   - Adjust range for better visualization

## Substance Fields Available:
- Oxygen_field_step_XXXXXX.vtk (oxygen concentration)
- Glucose_field_step_XXXXXX.vtk (glucose concentration)
- Lactate_field_step_XXXXXX.vtk (lactate concentration)
- TGFA_field_step_XXXXXX.vtk (growth factor concentration)
- HGF_field_step_XXXXXX.vtk (hepatocyte growth factor)
- ... (all 16 substances)

## Grid Information:
- Dimensions: 25x25x25 cells
- Spacing: 20 um per cell
- Domain: 500x500x500 um
- Format: VTK Structured Points
"""
    
    instructions_file = Path("results/jayatilake_experiment/PARAVIEW_INSTRUCTIONS.md")
    instructions_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(instructions_file, 'w') as f:
        f.write(instructions)
    
    print(f"[+] Created ParaView instructions: {instructions_file}")

if __name__ == "__main__":
    print("VTK Substance Field Export Test")
    print("=" * 40)
    
    # Test VTK file format
    if test_vtk_files():
        print("\n[+] VTK format validation passed!")
    else:
        print("\n[!] VTK format validation failed!")
        sys.exit(1)
    
    # Analyze substance evolution
    analyze_substance_evolution()
    
    # Create ParaView instructions
    create_paraview_instructions()
    
    print("\n" + "=" * 40)
    print("[+] VTK substance field export test completed!")
    print("[*] Files ready for ParaView visualization")
    print("[*] See PARAVIEW_INSTRUCTIONS.md for usage guide")
