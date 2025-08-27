#!/usr/bin/env python3
"""
Test script for gradient boundary conditions in FiPy

This demonstrates:
1. Default gradient: 0 on left, 1 on right, linear gradients on top/bottom
2. Custom gradients: various patterns using custom functions

Usage:
    python test_gradient_boundaries.py
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from fipy import Grid2D, CellVariable, DiffusionTerm
    FIPY_AVAILABLE = True
except ImportError:
    FIPY_AVAILABLE = False
    print("[!] FiPy not available. Please install FiPy to run this test.")
    sys.exit(1)

def test_default_gradient():
    """Test the default gradient boundary conditions"""
    print(" Testing default gradient boundary conditions")
    print("   Left: 0, Right: 1, Top/Bottom: linear gradients")
    
    # Create mesh
    nx, ny = 20, 20
    domain_size = 400e-6  # 400 um in meters
    dx = dy = domain_size / nx
    
    mesh = Grid2D(dx=dx, dy=dy, nx=nx, ny=ny)
    
    # Create variable
    var = CellVariable(name="test", mesh=mesh, value=0.5)
    
    # Apply default gradient boundary conditions
    apply_default_gradient_boundaries(var, mesh, domain_size)
    
    # Solve steady state (no sources, just diffusion with boundary conditions)
    equation = DiffusionTerm(coeff=1.0e-9) == 0
    
    # Solve iteratively
    for iteration in range(100):
        old_values = var.value.copy()
        equation.solve(var=var)
        
        # Check convergence
        max_change = np.max(np.abs(var.value - old_values))
        if max_change < 1e-6:
            print(f"   [+] Converged in {iteration+1} iterations")
            break
    
    # Extract solution
    solution = np.array(var.value).reshape((ny, nx), order='F')
    
    # Plot
    plt.figure(figsize=(10, 8))
    
    x_coords = np.array(mesh.cellCenters[0]).reshape((ny, nx), order='F')
    y_coords = np.array(mesh.cellCenters[1]).reshape((ny, nx), order='F')
    
    plt.subplot(2, 2, 1)
    plt.contourf(x_coords*1e6, y_coords*1e6, solution, levels=20, cmap='viridis')
    plt.colorbar(label='Concentration')
    plt.title('Default Gradient\n(0 left, 1 right, gradients top/bottom)')
    plt.xlabel('X (um)')
    plt.ylabel('Y (um)')
    
    return solution

def apply_default_gradient_boundaries(var, mesh, domain_width):
    """Apply the default gradient boundary conditions"""
    
    # Left side: 0
    var.constrain(0.0, mesh.facesLeft)
    
    # Right side: 1  
    var.constrain(1.0, mesh.facesRight)
    
    # Top and bottom: create linear gradients
    # Get face centers for all boundary faces
    face_centers_x = mesh.faceCenters[0]
    face_centers_y = mesh.faceCenters[1]
    
    # Apply gradients to top and bottom faces individually
    for face_id in range(mesh.numberOfFaces):
        face_center_x = face_centers_x[face_id]
        face_center_y = face_centers_y[face_id]
        
        # Check if this is a top or bottom face (not left or right)
        is_top_face = mesh.facesTop[face_id]
        is_bottom_face = mesh.facesBottom[face_id]
        
        if is_top_face or is_bottom_face:
            # Create linear gradient based on x position
            normalized_x = face_center_x / domain_width
            gradient_value = max(0.0, min(1.0, normalized_x))  # Clamp to [0,1]
            
            # Create a mask for this specific face
            face_mask = (mesh.exteriorFaces == 1) & (mesh.faceCenters[0] == face_center_x) & (mesh.faceCenters[1] == face_center_y)
            if face_mask.any():
                var.constrain(gradient_value, where=face_mask)

def test_custom_gradients():
    """Test various custom gradient patterns"""
    print(" Testing custom gradient patterns")
    
    # Create mesh
    nx, ny = 20, 20
    domain_size = 400e-6  # 400 um in meters
    dx = dy = domain_size / nx
    
    mesh = Grid2D(dx=dx, dy=dy, nx=nx, ny=ny)
    
    # Test different gradient patterns
    patterns = [
        ("Sinusoidal", lambda x, y: 0.5 + 0.5 * np.sin(2 * np.pi * x / domain_size)),
        ("Radial", lambda x, y: np.sqrt((x - domain_size/2)**2 + (y - domain_size/2)**2) / (domain_size/2)),
        ("Parabolic", lambda x, y: 4 * (x / domain_size - 0.5)**2)
    ]
    
    plt.figure(figsize=(15, 5))
    
    for i, (name, gradient_func) in enumerate(patterns):
        # Create variable
        var = CellVariable(name=name, mesh=mesh, value=0.5)
        
        # Apply custom boundary conditions
        apply_custom_gradient_boundaries(var, mesh, gradient_func)
        
        # Solve steady state
        equation = DiffusionTerm(coeff=1.0e-9) == 0
        
        for iteration in range(100):
            old_values = var.value.copy()
            equation.solve(var=var)
            
            max_change = np.max(np.abs(var.value - old_values))
            if max_change < 1e-6:
                break
        
        # Extract and plot solution
        solution = np.array(var.value).reshape((ny, nx), order='F')
        x_coords = np.array(mesh.cellCenters[0]).reshape((ny, nx), order='F')
        y_coords = np.array(mesh.cellCenters[1]).reshape((ny, nx), order='F')
        
        plt.subplot(1, 3, i+1)
        plt.contourf(x_coords*1e6, y_coords*1e6, solution, levels=20, cmap='viridis')
        plt.colorbar(label='Concentration')
        plt.title(f'{name} Gradient')
        plt.xlabel('X (um)')
        plt.ylabel('Y (um)')
        
        print(f"   [+] {name} gradient completed")

def apply_custom_gradient_boundaries(var, mesh, gradient_func):
    """Apply custom gradient boundary conditions using a function"""
    
    # Apply boundary conditions to all exterior faces
    face_centers_x = mesh.faceCenters[0]
    face_centers_y = mesh.faceCenters[1]
    
    # Create array for boundary values
    boundary_values = []
    
    for face_id in range(mesh.numberOfFaces):
        if mesh.exteriorFaces[face_id]:
            # Get face center coordinates
            face_center_x = float(face_centers_x[face_id])
            face_center_y = float(face_centers_y[face_id])
            
            # Calculate boundary value using custom function
            boundary_value = gradient_func(face_center_x, face_center_y)
            boundary_value = max(0.0, min(1.0, boundary_value))  # Clamp to [0,1]
            
            # Apply constraint to this face
            face_mask = (mesh.exteriorFaces == 1) & (mesh.faceCenters[0] == face_center_x) & (mesh.faceCenters[1] == face_center_y)
            if face_mask.any():
                var.constrain(boundary_value, where=face_mask)

def visualize_boundary_conditions():
    """Visualize the boundary conditions without solving diffusion"""
    print(" Visualizing boundary conditions")
    
    # Create mesh
    nx, ny = 20, 20
    domain_size = 400e-6
    dx = dy = domain_size / nx
    
    mesh = Grid2D(dx=dx, dy=dy, nx=nx, ny=ny)
    
    # Create boundary value arrays for visualization
    x_coords = np.array(mesh.cellCenters[0]).reshape((ny, nx), order='F')
    y_coords = np.array(mesh.cellCenters[1]).reshape((ny, nx), order='F')
    
    # Different boundary patterns
    patterns = {
        'Linear (Default)': x_coords / domain_size,
        'Sinusoidal': 0.5 + 0.5 * np.sin(2 * np.pi * x_coords / domain_size),
        'Radial': np.sqrt((x_coords - domain_size/2)**2 + (y_coords - domain_size/2)**2) / (domain_size/2),
        'Parabolic': 4 * (x_coords / domain_size - 0.5)**2
    }
    
    plt.figure(figsize=(15, 10))
    
    for i, (name, pattern) in enumerate(patterns.items()):
        plt.subplot(2, 2, i+1)
        plt.contourf(x_coords*1e6, y_coords*1e6, pattern, levels=20, cmap='viridis')
        plt.colorbar(label='Boundary Value')
        plt.title(f'{name} Boundary Pattern')
        plt.xlabel('X (um)')
        plt.ylabel('Y (um)')
        
        # Add contour lines
        plt.contour(x_coords*1e6, y_coords*1e6, pattern, levels=10, colors='white', alpha=0.3, linewidths=0.5)

def main():
    """Main test function"""
    print("[RUN] Testing FiPy Gradient Boundary Conditions")
    print("=" * 50)
    
    if not FIPY_AVAILABLE:
        print("[!] FiPy not available")
        return
    
    # Test 1: Default gradient boundaries
    solution1 = test_default_gradient()
    
    # Test 2: Custom gradient patterns
    test_custom_gradients()
    
    # Test 3: Visualize boundary patterns
    visualize_boundary_conditions()
    
    plt.tight_layout()
    plt.show()
    
    print("\n[+] All tests completed!")
    print("\nBoundary condition summary:")
    print("  * Default gradient: 0 (left) -> 1 (right), linear gradients on top/bottom")
    print("  * Custom gradients: Use custom_calculate_boundary_conditions() function")
    print("  * Configuration: Set boundary_type to 'fixed' or 'gradient'")

if __name__ == "__main__":
    main() 