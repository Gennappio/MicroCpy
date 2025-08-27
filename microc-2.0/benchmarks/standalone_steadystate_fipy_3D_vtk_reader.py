#!/usr/bin/env python3
"""
Standalone 3D FiPy VTK Reader - Load cell states from H5 files and output VTK volumetric files

This script reads cell state and position data from MicroC H5 files, runs
FiPy diffusion simulations, and outputs the 3D substance field as VTK files
for visualization in ParaView, VisIt, or other VTK-compatible software.

Features:
- Load cell positions and states from H5 files
- Run FiPy diffusion simulations with loaded cell data
- Export 3D volumetric substance fields to VTK format
- Support for multiple substances (Oxygen, Lactate, Glucose)
- Structured grid VTK output with cell data

Usage:
    python standalone_steadystate_fipy_3D_vtk_reader.py <h5_file_path> [options]
"""

import argparse
import h5py
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Import FiPy
try:
    from fipy import Grid3D, CellVariable, DiffusionTerm
    from fipy.solvers.scipy import LinearGMRESSolver as Solver
    print("[+] FiPy available")
except ImportError:
    print("[!] FiPy not available")
    exit(1)

# Import VTK for output
try:
    import vtk
    from vtk.util import numpy_support
    print("[+] VTK available")
    VTK_AVAILABLE = True
except ImportError:
    print("[!] VTK not available - will use simple VTK writer")
    VTK_AVAILABLE = False


class H5CellStateLoader:
    """Load cell state data from MicroC H5 files"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.metadata = {}
        self.cell_data = {}
        self.gene_data = {}
        self.domain_info = {}
        
        self._load_file()
    
    def _load_file(self):
        """Load data from H5 file"""
        with h5py.File(self.file_path, 'r') as f:
            # Load metadata
            if 'metadata' in f:
                # Load metadata attributes
                for key in f['metadata'].attrs.keys():
                    self.metadata[key] = f['metadata'].attrs[key]

                # Also load metadata datasets (for backward compatibility)
                for key in f['metadata'].keys():
                    self.metadata[key] = f['metadata'][key][()]
            
            # Load cell data
            if 'cells' in f:
                cells_group = f['cells']
                
                # Load positions
                if 'positions' in cells_group:
                    self.cell_data['positions'] = cells_group['positions'][:]
                
                # Load phenotypes
                if 'phenotypes' in cells_group:
                    phenotypes = cells_group['phenotypes'][:]
                    # Convert bytes to strings if needed
                    if phenotypes.dtype.kind in ['S', 'U']:
                        phenotypes = [p.decode() if isinstance(p, bytes) else str(p) for p in phenotypes]
                    self.cell_data['phenotypes'] = phenotypes
                
                # Load gene network states
                if 'gene_network_states' in cells_group:
                    self.cell_data['gene_states'] = cells_group['gene_network_states'][:]
            
            # Load gene information
            if 'genes' in f:
                genes_group = f['genes']
                if 'names' in genes_group:
                    gene_names = genes_group['names'][:]
                    # Convert bytes to strings if needed
                    if gene_names.dtype.kind in ['S', 'U']:
                        gene_names = [g.decode() if isinstance(g, bytes) else str(g) for g in gene_names]
                    self.gene_data['names'] = gene_names
    
    def get_cell_summary(self) -> Dict:
        """Get summary statistics of loaded cell data"""
        summary = {}
        
        if 'positions' in self.cell_data:
            positions = self.cell_data['positions']
            summary['total_cells'] = len(positions)
            
            # Position ranges
            if len(positions) > 0:
                summary['position_range'] = {
                    'x': (positions[:, 0].min(), positions[:, 0].max()),
                    'y': (positions[:, 1].min(), positions[:, 1].max()),
                }
                if positions.shape[1] > 2:
                    summary['position_range']['z'] = (positions[:, 2].min(), positions[:, 2].max())
        
        if 'phenotypes' in self.cell_data:
            phenotypes = self.cell_data['phenotypes']
            unique, counts = np.unique(phenotypes, return_counts=True)
            summary['phenotype_distribution'] = dict(zip(unique, counts))
        
        return summary


class FiPyVTKSimulator:
    """FiPy simulator that outputs VTK volumetric files"""
    
    def __init__(self, h5_loader: H5CellStateLoader, domain_size: float = 500e-6, grid_size: int = 25):
        self.loader = h5_loader
        self.substances = {}
        self.mesh = None
        self.grid_size = None
        self.domain_size = None
        self.cell_height = None

        # Store user-provided parameters
        self.user_domain_size = domain_size
        self.user_grid_size = grid_size

        self._setup_domain()
    
    def _setup_domain(self):
        """Setup the 3D domain and mesh"""
        # Use user-provided parameters
        self.domain_size = self.user_domain_size
        nx = ny = nz = self.user_grid_size
        self.grid_size = (nx, ny, nz)
        
        # Cell height for coordinate conversion (read from H5 metadata if available)
        if 'cell_size_um' in self.loader.metadata:
            self.cell_height = self.loader.metadata['cell_size_um'] * 1e-6  # Convert μm to meters
            print(f"[*] Using cell size from H5 metadata: {self.loader.metadata['cell_size_um']} μm")
        else:
            self.cell_height = 5e-6  # Default: 5 μm
            print(f"[*] Using default cell size: {self.cell_height*1e6} μm")
        
        print(f"[*] Using domain parameters:")
        print(f"    Domain size: {self.domain_size*1e6:.0f} μm")
        print(f"    Grid size: {nx}x{ny}x{nz}")
        
        print(f"[*] Domain setup:")
        print(f"    Size: {self.domain_size*1e6:.0f} x {self.domain_size*1e6:.0f} x {self.domain_size*1e6:.0f} um")
        print(f"    Grid: {nx} x {ny} x {nz}")
        print(f"    Spacing: {self.domain_size/nx*1e6:.1f} x {self.domain_size/ny*1e6:.1f} x {self.domain_size/nz*1e6:.1f} um")
        print(f"    Cell height: {self.cell_height*1e6:.1f} um")
        
        # Create 3D mesh centered at origin
        dx = dy = dz = self.domain_size / nx
        self.mesh = Grid3D(nx=nx, ny=ny, nz=nz, dx=dx, dy=dy, dz=dz)
        
        # Shift mesh to center at origin
        self.mesh = self.mesh + ((-self.domain_size/2, -self.domain_size/2, -self.domain_size/2))
        
        print(f"[+] Created 3D mesh with {self.mesh.numberOfCells} cells")
        print(f"    Domain bounds: {-self.domain_size/2*1e6:.0f} to {self.domain_size/2*1e6:.0f} μm")
    
    def add_substance(self, name: str, diffusion_coeff: float, initial_conc: float, boundary_conc: float):
        """Add a substance to simulate"""
        substance_var = CellVariable(name=name, mesh=self.mesh, value=initial_conc)
        substance_var.constrain(boundary_conc, self.mesh.exteriorFaces)
        
        self.substances[name] = {
            'variable': substance_var,
            'diffusion_coeff': diffusion_coeff,
            'initial_conc': initial_conc,
            'boundary_conc': boundary_conc,
            'source_field': CellVariable(name=f"{name}_source", mesh=self.mesh, value=0.0)
        }
        
        print(f"[+] Added substance: {name}")
        print(f"    Diffusion coeff: {diffusion_coeff:.2e} m²/s")
        print(f"    Initial/boundary: {initial_conc}/{boundary_conc} mM")
        
        return substance_var
    
    def map_cells_to_grid(self, substance_name: str):
        """Map cell data to FiPy grid for the specified substance"""
        if substance_name not in self.substances:
            print(f"[!] Substance {substance_name} not found")
            return
        
        if not self.loader.cell_data:
            print("[!] No cell data loaded")
            return
        
        positions = self.loader.cell_data.get('positions')
        phenotypes = self.loader.cell_data.get('phenotypes')
        
        if positions is None:
            print("[!] No cell positions found")
            return
        
        print(f"[DEBUG] Using {len(positions)} cells from H5 file (MODIFIED)")
        
        # Apply the -10 offset to X coordinates (matching H5 reader)
        positions = positions.copy()
        positions[:, 0] = positions[:, 0] - 10
        
        # Convert biological coordinates to physical coordinates
        positions_physical = positions * self.cell_height
        
        print(f"[DEBUG] Position range: X={positions[:, 0].min():.0f}-{positions[:, 0].max():.0f}, Y={positions[:, 1].min():.0f}-{positions[:, 1].max():.0f}")
        
        # Get grid parameters
        nx, ny, nz = self.grid_size
        dx = dy = dz = self.domain_size / nx
        
        # Map cells to grid indices
        source_field = self.substances[substance_name]['source_field']
        source_field.setValue(0.0)  # Reset
        
        mapped_cells = 0
        grid_cells_with_sources = set()
        
        for i, pos_phys in enumerate(positions_physical):
            # Convert physical coordinates to grid indices (centered domain)
            x_idx = int((pos_phys[0] + self.domain_size/2) / dx)
            y_idx = int((pos_phys[1] + self.domain_size/2) / dy)
            z_idx = int((pos_phys[2] + self.domain_size/2) / dz) if len(pos_phys) > 2 else nz//2
            
            # Check bounds
            if 0 <= x_idx < nx and 0 <= y_idx < ny and 0 <= z_idx < nz:
                # Convert to linear index
                linear_idx = x_idx * ny * nz + y_idx * nz + z_idx
                
                # Get phenotype-based reaction rate
                phenotype = phenotypes[i] if phenotypes is not None else "Quiescent"
                reaction_rate = self._get_reaction_rate(substance_name, phenotype)
                
                # Add to source field
                current_value = source_field.value[linear_idx]
                source_field.value[linear_idx] = current_value + reaction_rate
                
                mapped_cells += 1
                grid_cells_with_sources.add(linear_idx)
        
        print(f"[+] Mapped {mapped_cells}/{len(positions)} cells for {substance_name}")
        print(f"[DEBUG] {len(grid_cells_with_sources)} FiPy grid cells have consumption/production")
        print(f"[DEBUG] Source field range: {source_field.value.min():.2e} to {source_field.value.max():.2e} mM/s")
    
    def _get_reaction_rate(self, substance_name: str, phenotype: str) -> float:
        """Get reaction rate based on substance and phenotype"""
        # Lactate production rates (mM/s)
        if substance_name == "Lactate":
            rates = {
                "Proliferation": 2.8e-2,
                "Growth_Arrest": 1.4e-2,
                "Apoptosis": 0.7e-2,
                "Quiescent": 0.35e-2
            }
            return rates.get(phenotype, 0.35e-2)
        
        # Oxygen consumption rates (negative for consumption)
        elif substance_name == "Oxygen":
            rates = {
                "Proliferation": -1.4e-2,
                "Growth_Arrest": -0.7e-2,
                "Apoptosis": -0.35e-2,
                "Quiescent": -0.175e-2
            }
            return rates.get(phenotype, -0.175e-2)
        
        return 0.0
    
    def solve_substance(self, substance_name: str) -> Optional[CellVariable]:
        """Solve diffusion equation for the specified substance"""
        if substance_name not in self.substances:
            print(f"[!] Substance {substance_name} not found")
            return None
        
        substance_data = self.substances[substance_name]
        substance_var = substance_data['variable']
        diffusion_coeff = substance_data['diffusion_coeff']
        source_field = substance_data['source_field']
        
        print(f"[*] Solving {substance_name} diffusion...")
        
        # Create diffusion equation with source term
        eq = DiffusionTerm(coeff=diffusion_coeff) + source_field
        
        # Solve
        solver = Solver()
        eq.solve(var=substance_var, solver=solver)
        
        print(f"[+] Solver finished.")
        
        # Print results
        values = substance_var.value
        print(f"[+] {substance_name} results:")
        print(f"    Min: {values.min():.6f} mM")
        print(f"    Max: {values.max():.6f} mM")
        print(f"    Mean: {values.mean():.6f} mM")
        
        return substance_var

    def export_vtk_volumetric(self, substance_name: str, output_path: str):
        """Export 3D volumetric substance field to VTK format"""
        if substance_name not in self.substances:
            print(f"[!] Substance {substance_name} not found")
            return

        substance_var = self.substances[substance_name]['variable']
        nx, ny, nz = self.grid_size

        # Get concentration values
        concentration_values = np.array(substance_var.value)

        if VTK_AVAILABLE:
            # Use VTK library for structured grid output
            self._export_vtk_structured_grid(substance_name, concentration_values, output_path)
        else:
            # Use simple VTK writer
            self._export_vtk_simple(substance_name, concentration_values, output_path)

    def _export_vtk_structured_grid(self, substance_name: str, values: np.ndarray, output_path: str):
        """Export using VTK library (structured grid format)"""
        nx, ny, nz = self.grid_size

        # Create structured grid
        grid = vtk.vtkStructuredGrid()
        grid.SetDimensions(nx+1, ny+1, nz+1)  # Points, not cells

        # Create points
        points = vtk.vtkPoints()
        dx = dy = dz = self.domain_size / nx

        for k in range(nz+1):
            for j in range(ny+1):
                for i in range(nx+1):
                    x = -self.domain_size/2 + i * dx
                    y = -self.domain_size/2 + j * dy
                    z = -self.domain_size/2 + k * dz
                    points.InsertNextPoint(x, y, z)

        grid.SetPoints(points)

        # Add concentration data as cell data
        concentration_array = numpy_support.numpy_to_vtk(values)
        concentration_array.SetName(f"{substance_name}_Concentration_mM")
        grid.GetCellData().SetScalars(concentration_array)

        # Write to file
        writer = vtk.vtkStructuredGridWriter()
        writer.SetFileName(output_path)
        writer.SetInputData(grid)
        writer.Write()

        print(f"[+] VTK structured grid exported: {output_path}")
        print(f"    Format: Structured Grid (.vtk)")
        print(f"    Dimensions: {nx}x{ny}x{nz} cells")
        print(f"    Data: {substance_name} concentration field")

    def _export_vtk_simple(self, substance_name: str, values: np.ndarray, output_path: str):
        """Export using simple VTK ASCII format (no VTK library required)"""
        nx, ny, nz = self.grid_size
        dx = dy = dz = self.domain_size / nx

        with open(output_path, 'w') as f:
            # VTK header
            f.write("# vtk DataFile Version 3.0\n")
            f.write(f"3D {substance_name} Concentration Field from MicroC H5 Data\n")
            f.write("ASCII\n")
            f.write("DATASET STRUCTURED_GRID\n")
            f.write(f"DIMENSIONS {nx+1} {ny+1} {nz+1}\n")
            f.write(f"POINTS {(nx+1)*(ny+1)*(nz+1)} float\n")

            # Write points (grid vertices)
            for k in range(nz+1):
                for j in range(ny+1):
                    for i in range(nx+1):
                        x = -self.domain_size/2 + i * dx
                        y = -self.domain_size/2 + j * dy
                        z = -self.domain_size/2 + k * dz
                        f.write(f"{x:.6e} {y:.6e} {z:.6e}\n")

            # Write cell data
            f.write(f"\nCELL_DATA {nx*ny*nz}\n")
            f.write(f"SCALARS {substance_name}_Concentration_mM float 1\n")
            f.write("LOOKUP_TABLE default\n")

            # Write concentration values
            for value in values:
                f.write(f"{value:.6e}\n")

        print(f"[+] VTK ASCII file exported: {output_path}")
        print(f"    Format: Structured Grid ASCII (.vtk)")
        print(f"    Dimensions: {nx}x{ny}x{nz} cells")
        print(f"    Data: {substance_name} concentration field")


def main():
    parser = argparse.ArgumentParser(
        description="Standalone 3D FiPy VTK Reader - Load cell states from H5 files and export VTK volumetric files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic lactate simulation and VTK export
  python standalone_steadystate_fipy_3D_vtk_reader.py initial_state_3D_S.h5

  # Custom domain size and grid resolution
  python standalone_steadystate_fipy_3D_vtk_reader.py tumor_core.h5 --domain-size 1000e-6 --grid-size 50

  # High resolution for detailed visualization
  python standalone_steadystate_fipy_3D_vtk_reader.py cell_state.h5 --domain-size 2000e-6 --grid-size 80

  # Multiple substances (when implemented)
  python standalone_steadystate_fipy_3D_vtk_reader.py state.h5 --substance Oxygen
        """
    )

    parser.add_argument('h5_file', help='Path to the H5 cell state file')
    parser.add_argument('--domain-size', type=float, default=500e-6,
                       help='Domain size in meters (default: 500e-6 = 500 μm)')
    parser.add_argument('--grid-size', type=int, default=25,
                       help='Grid size (NxNxN) (default: 25)')
    parser.add_argument('--substance', type=str, default='Lactate',
                       help='Substance to simulate (default: Lactate)')

    args = parser.parse_args()

    try:
        print("=" * 60)
        print("3D FiPy VTK Reader - Cell State to VTK Volumetric Export")
        print("=" * 60)

        # Load H5 data
        loader = H5CellStateLoader(args.h5_file)

        # Print summary
        summary = loader.get_cell_summary()
        print(f"\n[*] Cell Data Summary:")
        print(f"    Total cells: {summary.get('total_cells', 0)}")
        print(f"    Phenotypes: {summary.get('phenotype_distribution', {})}")
        print(f"    Position range:")
        pos_range = summary.get('position_range', {})
        print(f"      X: {pos_range.get('x', (0,0))[0]:.2e} - {pos_range.get('x', (0,0))[1]:.2e} m")
        print(f"      Y: {pos_range.get('y', (0,0))[0]:.2e} - {pos_range.get('y', (0,0))[1]:.2e} m")
        print(f"      Z: {pos_range.get('z', (0,0))[0]:.2e} - {pos_range.get('z', (0,0))[1]:.2e} m")

        # Create output directory
        output_path = Path("benchmarks") / "vtk_simulation_results"
        output_path.mkdir(exist_ok=True)
        print(f"[*] Output directory: {output_path.absolute()}")

        # Create simulator with user-specified domain parameters
        simulator = FiPyVTKSimulator(loader, args.domain_size, args.grid_size)

        print(f"\n{'='*40}")
        print(f"Simulating {args.substance}")
        print("=" * 40)

        # Add substance (currently only Lactate implemented)
        if args.substance == "Lactate":
            simulator.add_substance("Lactate", 1.8e-10, 1.0, 1.0)
        elif args.substance == "Oxygen":
            simulator.add_substance("Oxygen", 2.1e-9, 0.21, 0.21)
        else:
            print(f"[!] Substance {args.substance} not implemented yet")
            return 1

        # Map cells to grid
        simulator.map_cells_to_grid(args.substance)

        # Solve
        result = simulator.solve_substance(args.substance)

        if result is not None:
            # Export VTK volumetric file
            vtk_filename = f"{Path(args.h5_file).stem}_{args.substance}_3D_field.vtk"
            vtk_path = output_path / vtk_filename
            simulator.export_vtk_volumetric(args.substance, str(vtk_path))

        print(f"\n{'='*60}")
        print("[+] VTK export completed successfully!")
        print(f"[*] Open the .vtk file in ParaView, VisIt, or other VTK viewer")
        print("=" * 60)

    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
