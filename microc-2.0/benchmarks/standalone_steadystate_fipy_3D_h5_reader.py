#!/usr/bin/env python3
"""
Standalone 3D FiPy H5 Reader - Load cell states from H5 files and run simulations

This script reads cell state and position data from MicroC H5 files and runs
FiPy diffusion simulations using the loaded cell data.

Features:
- Load cell positions and states from H5 files
- Extract gene network states and phenotypes
- Run FiPy diffusion simulations with loaded cell data
- Support for multiple substances (Oxygen, Lactate, Glucose)
- Phenotype-based reaction rates
- Visualization of results

Usage:
    python standalone_steadystate_fipy_3D_h5_reader.py <h5_file_path> [options]
"""

import argparse
import h5py
import numpy as np
import matplotlib.pyplot as plt
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
        print(f"[*] Loading H5 file: {self.file_path}")
        
        with h5py.File(self.file_path, 'r') as f:
            # Load metadata
            if 'metadata' in f:
                meta_group = f['metadata']
                for key in meta_group.attrs.keys():
                    value = meta_group.attrs[key]
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    self.metadata[key] = value
                
                # Parse domain info
                if 'domain_info' in self.metadata:
                    try:
                        self.domain_info = json.loads(self.metadata['domain_info'])
                    except:
                        print("[!] Could not parse domain info")
            
            # Load cell data
            if 'cells' in f:
                cells_group = f['cells']
                self.cell_data = {
                    'ids': [s.decode('utf-8') for s in cells_group['ids'][:]],
                    'positions': cells_group['positions'][:],
                    'phenotypes': [s.decode('utf-8') for s in cells_group['phenotypes'][:]],
                    'ages': cells_group['ages'][:],
                    'division_counts': cells_group['division_counts'][:],
                    'tq_wait_times': cells_group['tq_wait_times'][:]
                }
            
            # Load gene states
            if 'gene_states' in f:
                gene_group = f['gene_states']
                self.gene_data = {
                    'gene_names': [s.decode('utf-8') for s in gene_group['gene_names'][:]],
                    'states': gene_group['states'][:]
                }
        
        print(f"[+] Loaded {len(self.cell_data.get('ids', []))} cells")
        print(f"[+] Loaded {len(self.gene_data.get('gene_names', []))} genes")
    
    def get_cell_summary(self):
        """Get summary of loaded cell data"""
        if not self.cell_data:
            return {}
        
        phenotypes = self.cell_data['phenotypes']
        unique_phenotypes, counts = np.unique(phenotypes, return_counts=True)
        
        # Convert biological grid coordinates to physical coordinates
        positions = self.cell_data['positions']
        cell_height = self.domain_info.get('cell_height', 20e-6)

        # Convert to meters (biological grid coordinates × cell height)
        x_meters = (positions[:, 0]-10) * cell_height  # X bio coords × 5μm
        y_meters = positions[:, 1] * cell_height  # Y bio coords × 5μm
        z_meters = positions[:, 2] * cell_height  # Z bio coords × 5μm

        return {
            'total_cells': len(self.cell_data['ids']),
            'phenotype_distribution': {p: int(c) for p, c in zip(unique_phenotypes, counts)},
            'position_range': {
                'x': (float(x_meters.min()), float(x_meters.max())),
                'y': (float(y_meters.min()), float(y_meters.max())),
                'z': (float(z_meters.min()), float(z_meters.max()))
            },
            'position_range_grid': {
                'x': (float(positions[:, 0].min()), float(positions[:, 0].max())),
                'y': (float(positions[:, 1].min()), float(positions[:, 1].max())),
                'z': (float(positions[:, 2].min()), float(positions[:, 2].max())) if positions.shape[1] > 2 else (0, 0)
            },
            'age_range': (float(self.cell_data['ages'].min()),
                         float(self.cell_data['ages'].max()))
        }


class FiPyH5Simulator:
    """FiPy simulator that uses H5 cell data"""
    
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
        """Setup domain parameters from user input or defaults"""
        # Use user-provided parameters or defaults
        print(f"[*] Using domain parameters:")
        print(f"    Domain size: {self.user_domain_size*1e6:.0f} μm")
        print(f"    Grid size: {self.user_grid_size}x{self.user_grid_size}x{self.user_grid_size}")

        self.domain_size = self.user_domain_size  # User-specified domain size
        self.grid_size = (self.user_grid_size, self.user_grid_size, self.user_grid_size)  # User-specified grid
        self.cell_height = 5e-6  # 5 μm (standard cell height)

        nx, ny, nz = self.grid_size

        # Calculate mesh spacing
        dx = self.domain_size / nx
        dy = self.domain_size / ny
        dz = self.domain_size / nz

        print(f"[*] Domain setup:")
        print(f"    Size: {self.domain_size*1e6:.0f} x {self.domain_size*1e6:.0f} x {self.domain_size*1e6:.0f} um")
        print(f"    Grid: {nx} x {ny} x {nz}")
        print(f"    Spacing: {dx*1e6:.1f} x {dy*1e6:.1f} x {dz*1e6:.1f} um")
        print(f"    Cell height: {self.cell_height*1e6:.1f} um")
        
        # Create FiPy mesh (starts at 0,0,0 by default)
        self.mesh = Grid3D(dx=dx, dy=dy, dz=dz, nx=nx, ny=ny, nz=nz)

        # Shift mesh coordinates to center at origin
        # FiPy mesh goes from 0 to domain_size, we want -domain_size/2 to +domain_size/2
        self.mesh = self.mesh + ((-self.domain_size/2,) * 3)

        print(f"[+] Created 3D mesh with {self.mesh.numberOfCells} cells")
        print(f"    Domain bounds: {-self.domain_size/2*1e6:.0f} to {+self.domain_size/2*1e6:.0f} μm")
    
    def add_substance(self, name: str, diffusion_coeff: float, initial_value: float, 
                     boundary_value: float):
        """Add a substance to simulate"""
        substance = CellVariable(mesh=self.mesh, value=initial_value)
        substance.constrain(boundary_value, self.mesh.exteriorFaces)
        
        self.substances[name] = {
            'variable': substance,
            'diffusion_coeff': diffusion_coeff,
            'initial_value': initial_value,
            'boundary_value': boundary_value,
            'source_field': np.zeros(self.mesh.numberOfCells)
        }
        
        print(f"[+] Added substance: {name}")
        print(f"    Diffusion coeff: {diffusion_coeff:.2e} m²/s")
        print(f"    Initial/boundary: {initial_value}/{boundary_value} mM")
    
    def map_cells_to_grid(self, substance_name: str):
        """Map cells from H5 file to FiPy grid with hardcoded lactate production"""
        if substance_name not in self.substances:
            print(f"[!] Substance {substance_name} not found")
            return
        
        source_field = self.substances[substance_name]['source_field']
        source_field.fill(0)  # Reset
        
        # Get cell data - APPLY SAME MODIFICATIONS AS SUMMARY
        positions = self.loader.cell_data['positions'].copy()
        positions[:, 0] = positions[:, 0] - 10  # Apply the same -10 offset as in summary

        # DEBUG: Verify we're using MODIFIED cells
        print(f"[DEBUG] Using {len(positions)} cells from H5 file (MODIFIED)")
        print(f"[DEBUG] Position range: X={positions[:, 0].min():.0f}-{positions[:, 0].max():.0f}, Y={positions[:, 1].min():.0f}-{positions[:, 1].max():.0f}")

        # Simple hardcoded lactate production rate (same as working standalone)
        lactate_production_rate = 2.8e-2  # mM/s (same as standalone_steadystate_fipy.py)
        
        # Map cells to FiPy grid
        nx, ny, nz = self.grid_size
        dx = self.domain_size / nx
        dy = self.domain_size / ny
        dz = self.domain_size / nz
        
        cells_mapped = 0

        # Track cells per grid position for averaging
        grid_cell_counts = np.zeros(self.mesh.numberOfCells)

        for pos in positions:
            # Convert biological grid coordinates to physical coordinates
            # Positions in H5 are stored as biological grid indices
            x_meters = pos[0] * self.cell_height
            y_meters = pos[1] * self.cell_height
            z_meters = pos[2] * self.cell_height if len(pos) > 2 else 0

            # Convert physical coordinates to FiPy grid indices
            # Since mesh is centered at origin, shift coordinates to positive range
            x_idx = int((x_meters + self.domain_size/2) / dx)
            y_idx = int((y_meters + self.domain_size/2) / dy)
            z_idx = int((z_meters + self.domain_size/2) / dz)

            # Check bounds
            if 0 <= x_idx < nx and 0 <= y_idx < ny and 0 <= z_idx < nz:
                # Convert to FiPy index (column-major order)
                fipy_idx = x_idx * ny * nz + y_idx * nz + z_idx

                # Use hardcoded lactate production rate (already in mM/s)
                source_field[fipy_idx] += lactate_production_rate
                grid_cell_counts[fipy_idx] += 1
                cells_mapped += 1
        
        # Average the rates for grid cells with multiple biological cells
        overlapping_cells = np.sum(grid_cell_counts > 1)
        if overlapping_cells > 0:
            print(f"[!] Found {overlapping_cells} grid cells with multiple biological cells")
            # Average the consumption rates
            mask = grid_cell_counts > 0
            source_field[mask] = source_field[mask] / grid_cell_counts[mask]

        print(f"[+] Mapped {cells_mapped}/{len(positions)} cells for {substance_name}")

        # DEBUG: Show which FiPy grid cells have consumption
        active_cells = np.where(source_field != 0)[0]
        print(f"[DEBUG] {len(active_cells)} FiPy grid cells have consumption/production")
        if len(active_cells) > 0:
            print(f"[DEBUG] Source field range: {source_field.min():.2e} to {source_field.max():.2e} mM/s")

        # Update source field
        self.substances[substance_name]['source_field'] = source_field
    

    def solve_substance(self, substance_name: str, max_iterations: int = 1000, 
                       tolerance: float = 1e-6):
        """Solve diffusion equation for a substance"""
        if substance_name not in self.substances:
            print(f"[!] Substance {substance_name} not found")
            return None
        
        substance_data = self.substances[substance_name]
        substance_var = substance_data['variable']
        diffusion_coeff = substance_data['diffusion_coeff']
        source_field = substance_data['source_field']
        
        # Create source variable
        source_var = CellVariable(mesh=self.mesh, value=source_field)
        
        # Create equation: DiffusionTerm(D) == -source_var
        equation = DiffusionTerm(coeff=diffusion_coeff) == -source_var
        
        print(f"[*] Solving {substance_name} diffusion...")
        
        # Solve
        solver = Solver(iterations=max_iterations, tolerance=tolerance)
        
        try:
            res = equation.solve(var=substance_var, solver=solver)
            if res is not None:
                print(f"[+] Solver finished. Final residual: {res:.2e}")
            else:
                print(f"[+] Solver finished.")
        except Exception as e:
            print(f"[!] Error during solve: {e}")
            return None
        
        # Analyze results
        final_min = float(np.min(substance_var.value))
        final_max = float(np.max(substance_var.value))
        final_mean = float(np.mean(substance_var.value))
        
        print(f"[+] {substance_name} results:")
        print(f"    Min: {final_min:.6f} mM")
        print(f"    Max: {final_max:.6f} mM") 
        print(f"    Mean: {final_mean:.6f} mM")
        
        return substance_var
    
    def plot_results(self, substance_name: str, save_path: str = None, z_slice: int = None):
        """Plot simulation results"""
        if substance_name not in self.substances:
            print(f"[!] Substance {substance_name} not found")
            return
        
        substance_var = self.substances[substance_name]['variable']
        nx, ny, nz = self.grid_size
        
        # Determine Z slice to visualize
        if z_slice is not None:
            # User specified Z slice
            middle_z = z_slice
            print(f"[*] Using user-specified Z slice {middle_z}")

            # Validate slice is within bounds
            if middle_z < 0 or middle_z >= nz:
                print(f"[!] Warning: Z slice {middle_z} is outside valid range [0, {nz-1}]")
                middle_z = max(0, min(middle_z, nz-1))
                print(f"[*] Clamped to Z slice {middle_z}")
        else:
            # Auto-select slice with most cells
            if self.loader.cell_data:
                positions = self.loader.cell_data['positions'].copy()
                positions[:, 0] = positions[:, 0] - 10  # Apply the same -10 offset
                # Convert biological grid coordinates to FiPy grid indices
                z_coords = []
                for pos in positions:
                    z_meters = pos[2] * self.cell_height if len(pos) > 2 else 0
                    # Use same coordinate system as cell plotting (centered domain)
                    z_idx = int((z_meters + self.domain_size/2) / (self.domain_size / nz))
                    z_coords.append(z_idx)

                # Find the Z slice with most cells
                if z_coords:
                    unique_z, counts = np.unique(z_coords, return_counts=True)
                    middle_z = unique_z[np.argmax(counts)]
                    print(f"[*] Cell distribution by Z slice:")
                    for z, count in zip(unique_z, counts):
                        print(f"    Z={z}: {count} cells")
                    print(f"[*] Auto-selected Z slice {middle_z} (contains {np.max(counts)} cells)")
                else:
                    middle_z = nz // 2
            else:
                middle_z = nz // 2

        slice_data = np.zeros((nx, ny))
        
        for x in range(nx):
            for y in range(ny):
                idx = x * ny * nz + y * nz + middle_z
                slice_data[x, y] = substance_var.value[idx]
        
        # Plot with correct coordinate system (centered domain)
        plt.figure(figsize=(12, 10))

        # Calculate extent for centered domain: -domain_size/2 to +domain_size/2
        half_domain = self.domain_size / 2
        extent = [-half_domain*1e6, half_domain*1e6, -half_domain*1e6, half_domain*1e6]  # Convert to μm

        plt.imshow(slice_data.T, origin='lower', cmap='viridis', aspect='equal', extent=extent)
        plt.colorbar(label=f'{substance_name} Concentration (mM)')
        plt.title(f'3D FiPy H5 Reader - {substance_name} (Z={middle_z} slice)\n'
                  f'File: {self.loader.file_path.name}, '
                  f'Grid: {nx}×{ny}×{nz}, Cells: {len(self.loader.cell_data.get("ids", []))}')
        plt.xlabel('X Coordinate (μm)')
        plt.ylabel('Y Coordinate (μm)')
        
        # Mark cell positions on the slice
        if self.loader.cell_data:
            positions = self.loader.cell_data['positions'].copy()
            positions[:, 0] = positions[:, 0] - 10  # Apply the same -10 offset

            print(f"[*] Plotting cells on slice Z={middle_z}")

            cell_x_coords = []
            cell_y_coords = []

            for pos in positions:
                # Convert biological grid coordinates to physical coordinates (meters)
                # The biological coordinates are already roughly centered around 0
                pos_physical = pos * self.cell_height  # Convert to meters

                # Convert to μm for plotting - coordinates should already be centered
                x_um = pos_physical[0] * 1e6  # Convert to μm
                y_um = pos_physical[1] * 1e6  # Convert to μm
                z_meters = pos_physical[2] if len(pos_physical) > 2 else 0

                # Convert Z to grid index for slice selection
                # Z coordinates need to be shifted to grid indices (0 to nz-1)
                z_idx = int((z_meters + self.domain_size/2) / (self.domain_size / nz))

                # Show cells in the selected slice (±1 for visibility)
                if abs(z_idx - middle_z) <= 1:
                    cell_x_coords.append(x_um)
                    cell_y_coords.append(y_um)

            if cell_x_coords:
                plt.scatter(cell_x_coords, cell_y_coords,
                          c='red', s=15, alpha=0.8,
                          label=f'Cells ({len(cell_x_coords)})',
                          edgecolors='black', linewidth=0.5)
                print(f"[*] Plotted {len(cell_x_coords)} cells")
                plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            else:
                print(f"[!] No cells found in slice {middle_z} ± 1")
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[+] Saved plot: {save_path}")
        else:
            plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Standalone 3D FiPy H5 Reader - Load and simulate cell states from H5 files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic lactate simulation from initial state
  python standalone_steadystate_fipy_3D_h5_reader.py initial_state_3D_S.h5

  # Simulate specific substance
  python standalone_steadystate_fipy_3D_h5_reader.py cell_state.h5 --substance Oxygen

  # Simulate all substances and save plots
  python standalone_steadystate_fipy_3D_h5_reader.py state.h5 --all-substances --save-plots

  # Analyze temporal evolution
  python standalone_steadystate_fipy_3D_h5_reader.py "results/*/cell_states/cell_state_step*.h5" --substance Lactate --save-plots

  # Compare initial vs evolved state
  python standalone_steadystate_fipy_3D_h5_reader.py initial_state_3D_S.h5
  python standalone_steadystate_fipy_3D_h5_reader.py cell_state_step000005.h5

  # Custom domain size for large cell populations
  python standalone_steadystate_fipy_3D_h5_reader.py tumor_core.h5 --domain-size 1000e-6 --grid-size 50

  # Visualize specific Z slice
  python standalone_steadystate_fipy_3D_h5_reader.py initial_state_3D_S.h5 --z-slice 15
        """
    )
    
    parser.add_argument('h5_file', help='Path to the H5 cell state file')
    parser.add_argument('--domain-size', type=float, default=500e-6,
                       help='Domain size in meters (default: 500e-6 = 500 μm)')
    parser.add_argument('--grid-size', type=int, default=25,
                       help='Grid size (NxNxN) (default: 25)')
    parser.add_argument('--z-slice', type=int, default=None,
                       help='Z slice index to visualize (default: auto-select slice with most cells)')

    args = parser.parse_args()
    
    try:
        print("=" * 60)
        print("3D FiPy H5 Reader - Cell State Simulation")
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
        
        # Create simulator with user-specified domain parameters
        simulator = FiPyH5Simulator(loader, args.domain_size, args.grid_size)
        
        # Setup output directory (create in same folder as script)
        script_dir = Path(__file__).parent
        output_path = script_dir / "fipy_h5_simulation_results"
        output_path.mkdir(exist_ok=True)
        print(f"[*] Output directory: {output_path}")

        # Hardcoded lactate simulation
        print(f"\n{'='*40}")
        print(f"Simulating Lactate")
        print(f"{'='*40}")

        # Add lactate with hardcoded parameters (same as working standalone)
        simulator.add_substance(
            "Lactate",
            1.8e-10,  # diffusion_coeff m²/s (correct value from standalone)
            1.0,      # initial_value mM
            1.0       # boundary_value mM
        )

        # Map cells to grid
        simulator.map_cells_to_grid("Lactate")

        # Solve
        result = simulator.solve_substance("Lactate")

        if result is not None:
            # Plot results
            save_path = output_path / f"{Path(args.h5_file).stem}_Lactate_simulation.png"
            simulator.plot_results("Lactate", str(save_path), args.z_slice)
        
        print(f"\n{'='*60}")
        print("[+] H5 simulation completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
