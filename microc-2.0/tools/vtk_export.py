#!/usr/bin/env python3
"""
Shared VTK Export Module for MicroC 2.0

This module provides VTK export functionality that can be used by both:
1. H5 generator (initial conditions with scalar 0)
2. MicroC simulation (runtime data with ATP scalars)

The VTK files contain cubic cell geometry with scalar data for visualization.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime

# Check if FiPy is available for substance field export
try:
    from fipy import CellVariable
    FIPY_AVAILABLE = True
except ImportError:
    FIPY_AVAILABLE = False


class VTKSubstanceFieldExporter:
    """VTK export functionality for substance concentration fields"""

    def __init__(self):
        """Initialize VTK substance field exporter"""
        pass

    def export_substance_fields(self, simulator, output_dir: str, step: int) -> List[str]:
        """
        Export all substance concentration fields to VTK structured grid format

        Args:
            simulator: Multi-substance simulator with FiPy variables
            output_dir: Output directory path
            step: Simulation step number

        Returns:
            List of exported VTK file paths
        """
        if not FIPY_AVAILABLE:
            print("[!] FiPy not available - cannot export substance fields")
            return []

        if not hasattr(simulator, 'fipy_variables') or not simulator.fipy_variables:
            print("[!] No FiPy variables found in simulator")
            return []

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        exported_files = []

        print(f"[VTK] Exporting {len(simulator.fipy_variables)} substance fields...")

        for substance_name, fipy_var in simulator.fipy_variables.items():
            try:
                # Generate output filename
                vtk_filename = output_path / f"{substance_name}_field_step_{step:06d}.vtk"

                # Export this substance field
                success = self._export_single_substance_field(
                    substance_name=substance_name,
                    fipy_var=fipy_var,
                    mesh=simulator.fipy_mesh,
                    output_path=str(vtk_filename),
                    step=step
                )

                if success:
                    exported_files.append(str(vtk_filename))
                    print(f"   [OK] {substance_name}: {vtk_filename.name}")
                else:
                    print(f"   [!] Failed to export {substance_name}")

            except Exception as e:
                print(f"   [!] Error exporting {substance_name}: {e}")

        print(f"[VTK] Exported {len(exported_files)} substance field files")
        return exported_files

    def _export_single_substance_field(self, substance_name: str, fipy_var, mesh,
                                     output_path: str, step: int) -> bool:
        """
        Export a single substance field to VTK structured grid format

        Args:
            substance_name: Name of the substance
            fipy_var: FiPy CellVariable containing concentration data
            mesh: FiPy mesh object
            output_path: Output file path
            step: Simulation step number

        Returns:
            True if export successful, False otherwise
        """
        try:
            # Get concentration values
            concentration_values = np.array(fipy_var.value)

            # Get mesh dimensions - improved detection
            total_cells = len(concentration_values)

            # Try to get dimensions from mesh attributes
            if hasattr(mesh, 'nx') and hasattr(mesh, 'ny') and hasattr(mesh, 'nz'):
                # 3D mesh
                nx, ny, nz = mesh.nx, mesh.ny, mesh.nz
                is_3d = True
                is_3d = True
            elif hasattr(mesh, 'nx') and hasattr(mesh, 'ny'):
                # 2D mesh
                nx, ny = mesh.nx, mesh.ny
                nz = 1
                is_3d = False
            elif hasattr(mesh, 'args') and len(mesh.args) >= 6:
                # 3D mesh - extract from args
                nx, ny, nz = mesh.args[3], mesh.args[4], mesh.args[5]
                is_3d = True
            else:
                # Try to infer from total cell count
                # Try 3D case first (cube root)
                cube_root = int(np.round(total_cells**(1/3)))
                if cube_root**3 == total_cells:
                    nx = ny = nz = cube_root
                    is_3d = True
                # Try 2D case (square root)
                elif total_cells == int(np.sqrt(total_cells))**2:
                    nx = ny = int(np.sqrt(total_cells))
                    nz = 1
                    is_3d = False
                else:
                    print(f"[!] Cannot determine mesh dimensions for {substance_name} with {total_cells} cells")
                    return False

            # Get mesh spacing
            if hasattr(mesh, 'dx'):
                dx = float(mesh.dx)
                dy = float(mesh.dy) if hasattr(mesh, 'dy') else dx
                dz = float(mesh.dz) if hasattr(mesh, 'dz') else dx
            else:
                # Default spacing
                dx = dy = dz = 1.0

            # Reshape concentration data to grid
            expected_size = nx * ny * nz if is_3d else nx * ny
            if len(concentration_values) != expected_size:
                print(f"[!] Size mismatch for {substance_name}: got {len(concentration_values)}, expected {expected_size}")
                return False

            if is_3d:
                concentrations_grid = concentration_values.reshape((nx, ny, nz))
            else:
                concentrations_grid = concentration_values.reshape((nx, ny))

            # Export to VTK
            self._write_vtk_structured_grid(
                concentrations=concentrations_grid,
                substance_name=substance_name,
                dx=dx, dy=dy, dz=dz,
                output_path=output_path,
                step=step,
                is_3d=is_3d
            )

            return True

        except Exception as e:
            print(f"[!] Error in _export_single_substance_field for {substance_name}: {e}")
            return False

    def _write_vtk_structured_grid(self, concentrations: np.ndarray, substance_name: str,
                                 dx: float, dy: float, dz: float, output_path: str,
                                 step: int, is_3d: bool = True):
        """
        Write concentration data to VTK structured grid format

        Args:
            concentrations: 2D or 3D array of concentration values
            substance_name: Name of the substance
            dx, dy, dz: Grid spacing in meters
            output_path: Output file path
            step: Simulation step number
            is_3d: Whether this is a 3D grid
        """
        if is_3d:
            nx, ny, nz = concentrations.shape
        else:
            nx, ny = concentrations.shape
            nz = 1
            # Add z dimension for VTK
            concentrations = concentrations.reshape((nx, ny, 1))

        with open(output_path, 'w') as f:
            # VTK header
            f.write("# vtk DataFile Version 3.0\n")
            f.write(f"{substance_name} concentration field - Step {step}\n")
            f.write("ASCII\n")
            f.write("DATASET STRUCTURED_POINTS\n")

            # Grid dimensions (number of points = cells + 1)
            f.write(f"DIMENSIONS {nx+1} {ny+1} {nz+1}\n")

            # Grid spacing
            f.write(f"SPACING {dx:.6e} {dy:.6e} {dz:.6e}\n")

            # Origin
            f.write("ORIGIN 0.0 0.0 0.0\n")

            # Cell data (concentration values)
            total_cells = nx * ny * nz
            f.write(f"CELL_DATA {total_cells}\n")

            # Scalar data
            f.write(f"SCALARS {substance_name}_concentration float 1\n")
            f.write("LOOKUP_TABLE default\n")

            # Write concentration values
            for k in range(nz):
                for j in range(ny):
                    for i in range(nx):
                        conc = concentrations[i, j, k] if is_3d else concentrations[i, j, 0]
                        f.write(f"{conc:.6e}\n")


class VTKDomainExporter:
    """Enhanced VTK export for complete domain description with gene networks and metadata"""

    def __init__(self, cell_size_um: float):
        """Initialize with cell size in micrometers"""
        self.cell_size_um = cell_size_um
        self.cell_size_m = cell_size_um * 1e-6  # Convert to meters

    def export_complete_domain(self, positions: np.ndarray, gene_states: Dict,
                             phenotypes: List[str], metadata: Dict, output_path: str) -> str:
        """
        Export complete domain description with cells, gene networks, phenotypes, and metadata

        Args:
            positions: Nx3 array of cell positions (biological grid coordinates)
            gene_states: Dict mapping cell_id -> {gene_name: bool} for each cell
            phenotypes: List of phenotype strings for each cell
            metadata: Dict with domain metadata (description, time, bounds, etc.)
            output_path: Path to save VTK file

        Returns:
            Path to exported VTK file
        """
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[*] Exporting complete VTK domain...")
        print(f"    Cell size: {self.cell_size_um} um")
        print(f"    Cell count: {len(positions)}")
        print(f"    Gene networks: {len(gene_states)} cells")
        print(f"    Phenotypes: {len(set(phenotypes))} unique types")

        # Get all gene node names from first cell
        gene_nodes = list(next(iter(gene_states.values())).keys()) if gene_states else []

        with open(output_path, 'w', encoding='utf-8') as f:
            # VTK header with embedded metadata in description line
            # Encode metadata as JSON-like string in the description
            metadata_str = (f"cells={len(positions)} "
                          f"size={metadata.get('biocell_grid_size_um', self.cell_size_um)}um "
                          f"genes={','.join(gene_nodes)} "
                          f"phenotypes={','.join(sorted(set(phenotypes)))} "
                          f"time={metadata.get('simulated_time', 0.0)} "
                          f"bounds={metadata.get('domain_bounds_um', 'auto')}")

            f.write("# vtk DataFile Version 3.0\n")
            f.write(f"MicroC Domain: {metadata.get('description', 'Generated domain')} | {metadata_str}\n")
            f.write("ASCII\n")
            f.write("DATASET UNSTRUCTURED_GRID\n")

            # Generate cube vertices for each cell (8 vertices per cube)
            total_points = len(positions) * 8
            f.write(f"POINTS {total_points} float\n")

            half_size = self.cell_size_m / 2.0  # Half cell size in meters

            for pos in positions:
                # Convert from biological grid coordinates to physical coordinates (meters)
                x_center = pos[0] * self.cell_size_m
                y_center = pos[1] * self.cell_size_m
                z_center = pos[2] * self.cell_size_m if len(pos) > 2 else 0.0

                # Generate 8 vertices of the cube around the center
                vertices = [
                    [x_center - half_size, y_center - half_size, z_center - half_size],  # 0
                    [x_center + half_size, y_center - half_size, z_center - half_size],  # 1
                    [x_center + half_size, y_center + half_size, z_center - half_size],  # 2
                    [x_center - half_size, y_center + half_size, z_center - half_size],  # 3
                    [x_center - half_size, y_center - half_size, z_center + half_size],  # 4
                    [x_center + half_size, y_center - half_size, z_center + half_size],  # 5
                    [x_center + half_size, y_center + half_size, z_center + half_size],  # 6
                    [x_center - half_size, y_center + half_size, z_center + half_size],  # 7
                ]

                for vertex in vertices:
                    f.write(f"{vertex[0]:.6e} {vertex[1]:.6e} {vertex[2]:.6e}\n")

            # Cell connectivity (hexahedrons)
            num_cells = len(positions)
            f.write(f"CELLS {num_cells} {num_cells * 9}\n")  # 9 = 8 vertices + 1 count

            for i in range(num_cells):
                base_idx = i * 8
                # Hexahedron connectivity (VTK_HEXAHEDRON = 12)
                f.write(f"8 {base_idx} {base_idx+1} {base_idx+2} {base_idx+3} "
                       f"{base_idx+4} {base_idx+5} {base_idx+6} {base_idx+7}\n")

            # Cell types (all hexahedrons)
            f.write(f"CELL_TYPES {num_cells}\n")
            for _ in range(num_cells):
                f.write("12\n")  # VTK_HEXAHEDRON = 12

            # Cell data section
            f.write(f"CELL_DATA {num_cells}\n")

            # Phenotype data
            phenotype_map = {p: i for i, p in enumerate(sorted(set(phenotypes)))}
            f.write(f"SCALARS Phenotype int 1\n")
            f.write("LOOKUP_TABLE default\n")
            for phenotype in phenotypes:
                f.write(f"{phenotype_map[phenotype]}\n")

            # Gene network data (each gene as separate scalar field)
            for gene_name in gene_nodes:
                f.write(f"SCALARS {gene_name} int 1\n")
                f.write("LOOKUP_TABLE default\n")
                for i in range(len(positions)):
                    cell_genes = gene_states.get(i, {})
                    activation = 1 if cell_genes.get(gene_name, False) else 0
                    f.write(f"{activation}\n")

        print(f"[+] Complete VTK domain exported: {Path(output_path).name}")
        print(f"    Format: Unstructured Grid (.vtk)")
        print(f"    Cell representation: 3D cubes (hexahedrons)")
        print(f"    Data: {len(positions)} cubes with {self.cell_size_um} um edge length")
        print(f"    Gene networks: {len(gene_nodes)} nodes per cell")
        print(f"    Phenotypes: {list(phenotype_map.keys())}")

        return output_path


class VTKDomainLoader:
    """Load complete domain description from enhanced VTK files"""

    def __init__(self):
        """Initialize VTK domain loader"""
        pass

    def load_complete_domain(self, vtk_path: str) -> Dict:
        """
        Load complete domain description from VTK file

        Args:
            vtk_path: Path to VTK domain file

        Returns:
            Dict containing positions, gene_states, phenotypes, metadata
        """
        print(f"[VTK] Loading complete domain from {vtk_path}")

        with open(vtk_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Parse metadata from description line
        metadata = {}
        gene_nodes = []
        phenotype_types = []

        # Look for description line (second line)
        if len(lines) >= 2:
            desc_line = lines[1].strip()
            if "|" in desc_line:
                # Extract metadata part after the "|"
                parts = desc_line.split("|", 1)
                if len(parts) == 2:
                    metadata_part = parts[1].strip()

                    # Parse key=value pairs
                    for item in metadata_part.split():
                        if "=" in item:
                            key, value = item.split("=", 1)
                            if key == "genes":
                                gene_nodes = value.split(",") if value else []
                            elif key == "phenotypes":
                                phenotype_types = value.split(",") if value else []
                            elif key == "cells":
                                metadata['cell_count'] = int(value)
                            elif key == "size":
                                # Extract numeric value from "20.0um" format
                                size_str = value.replace("um", "")
                                metadata['biocell_grid_size_um'] = float(size_str)
                            elif key == "time":
                                metadata['simulated_time'] = float(value)
                            elif key == "bounds":
                                metadata['domain_bounds_um'] = value
                            else:
                                metadata[key] = value

        # Parse cell positions from POINTS section
        positions = []
        points_section = False
        cell_data_section = False
        current_scalar = None
        scalar_data = {}

        for i, line in enumerate(lines):
            line = line.strip()

            if line.startswith("POINTS"):
                points_section = True
                total_points = int(line.split()[1])
                continue
            elif line.startswith("CELLS"):
                points_section = False
                continue
            elif line.startswith("CELL_DATA"):
                cell_data_section = True
                continue
            elif line.startswith("SCALARS"):
                if cell_data_section:
                    current_scalar = line.split()[1]
                    scalar_data[current_scalar] = []
                continue
            elif line.startswith("LOOKUP_TABLE"):
                continue

            if points_section and line and not line.startswith("#"):
                # Parse point coordinates (8 points per cell)
                coords = list(map(float, line.split()))
                if len(coords) == 3:
                    positions.append(coords)
            elif cell_data_section and current_scalar and line and not line.startswith("#") and not line.startswith("SCALARS"):
                # Parse scalar data
                try:
                    value = int(line)
                    scalar_data[current_scalar].append(value)
                except ValueError:
                    pass

        # Convert point coordinates to cell centers (every 8 points = 1 cell)
        cell_positions = []
        cell_size_m = metadata.get('biocell_grid_size_um', 20.0) * 1e-6

        for i in range(0, len(positions), 8):
            if i + 7 < len(positions):
                # Calculate cell center from cube vertices
                cube_points = positions[i:i+8]
                center_x = sum(p[0] for p in cube_points) / 8
                center_y = sum(p[1] for p in cube_points) / 8
                center_z = sum(p[2] for p in cube_points) / 8

                # Convert back to biological grid coordinates
                bio_x = center_x / cell_size_m
                bio_y = center_y / cell_size_m
                bio_z = center_z / cell_size_m

                cell_positions.append([bio_x, bio_y, bio_z])

        # Parse gene states and phenotypes
        gene_states = {}
        phenotypes = []

        # Get phenotype mapping
        phenotype_values = scalar_data.get('Phenotype', [])
        phenotype_map = {i: p for i, p in enumerate(phenotype_types)}

        for i in range(len(cell_positions)):
            # Gene states for this cell
            cell_genes = {}
            for gene_name in gene_nodes:
                if gene_name in scalar_data and i < len(scalar_data[gene_name]):
                    cell_genes[gene_name] = bool(scalar_data[gene_name][i])
            gene_states[i] = cell_genes

            # Phenotype for this cell
            if i < len(phenotype_values):
                phenotype_idx = phenotype_values[i]
                phenotype = phenotype_map.get(phenotype_idx, 'Unknown')
                phenotypes.append(phenotype)
            else:
                phenotypes.append('Unknown')

        result = {
            'positions': np.array(cell_positions),
            'gene_states': gene_states,
            'phenotypes': phenotypes,
            'metadata': metadata,
            'gene_nodes': gene_nodes,
            'phenotype_types': phenotype_types
        }

        print(f"[+] Loaded domain: {len(cell_positions)} cells")
        print(f"    Cell size: {metadata.get('biocell_grid_size_um', 'unknown')} um")
        print(f"    Gene nodes: {len(gene_nodes)}")
        print(f"    Phenotypes: {len(set(phenotypes))} types")

        return result


class VTKCellExporter:
    """Shared VTK export functionality for cubic cell geometry"""
    
    def __init__(self, cell_size_um: float = 5.0):
        """
        Initialize VTK exporter
        
        Args:
            cell_size_um: Cell size in micrometers
        """
        self.cell_size_um = cell_size_um
        self.cell_size_m = cell_size_um * 1e-6  # Convert to meters
    
    def export_cubic_cells(self, positions: np.ndarray, scalars: np.ndarray, 
                          output_path: str, scalar_name: str = "ATP_Type",
                          title: str = "Cubic Cells from MicroC"):
        """
        Export cell positions as cubic cells in VTK format
        
        Args:
            positions: Nx3 array of cell positions (biological grid coordinates)
            scalars: N array of scalar values for each cell
            output_path: Path to save VTK file
            scalar_name: Name of the scalar field
            title: Title for VTK file
        """
        
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[*] Exporting VTK cubic cells...")
        print(f"    Cell size: {self.cell_size_um} um")
        print(f"    Cell count: {len(positions)}")
        print(f"    Scalar field: {scalar_name}")
        
        with open(output_path, 'w') as f:
            # VTK header
            f.write("# vtk DataFile Version 3.0\n")
            f.write(f"{title}\n")
            f.write("ASCII\n")
            f.write("DATASET UNSTRUCTURED_GRID\n")
            
            # Generate cube vertices for each cell (8 vertices per cube)
            total_points = len(positions) * 8
            f.write(f"POINTS {total_points} float\n")
            
            half_size = self.cell_size_m / 2.0  # Half cell size in meters
            
            for pos in positions:
                # Convert from biological grid coordinates to physical coordinates (meters)
                x_center = pos[0] * self.cell_size_m
                y_center = pos[1] * self.cell_size_m
                z_center = pos[2] * self.cell_size_m if len(pos) > 2 else 0.0
                
                # Generate 8 vertices of the cube around the center
                vertices = [
                    [x_center - half_size, y_center - half_size, z_center - half_size],  # 0
                    [x_center + half_size, y_center - half_size, z_center - half_size],  # 1
                    [x_center + half_size, y_center + half_size, z_center - half_size],  # 2
                    [x_center - half_size, y_center + half_size, z_center - half_size],  # 3
                    [x_center - half_size, y_center - half_size, z_center + half_size],  # 4
                    [x_center + half_size, y_center - half_size, z_center + half_size],  # 5
                    [x_center + half_size, y_center + half_size, z_center + half_size],  # 6
                    [x_center - half_size, y_center + half_size, z_center + half_size],  # 7
                ]
                
                for vertex in vertices:
                    f.write(f"{vertex[0]:.6e} {vertex[1]:.6e} {vertex[2]:.6e}\n")
            
            # Cells (hexahedrons - one per cell)
            f.write(f"\nCELLS {len(positions)} {len(positions) * 9}\n")
            for i in range(len(positions)):
                base_idx = i * 8
                # VTK hexahedron connectivity (8 vertices per cube)
                f.write(f"8 {base_idx} {base_idx+1} {base_idx+2} {base_idx+3} {base_idx+4} {base_idx+5} {base_idx+6} {base_idx+7}\n")
            
            # Cell types (VTK_HEXAHEDRON = 12)
            f.write(f"\nCELL_TYPES {len(positions)}\n")
            for i in range(len(positions)):
                f.write("12\n")
            
            # Cell data (one value per cube)
            f.write(f"\nCELL_DATA {len(positions)}\n")
            
            # Scalar data
            f.write(f"SCALARS {scalar_name} int 1\n")
            f.write("LOOKUP_TABLE default\n")
            for scalar in scalars:
                f.write(f"{int(scalar)}\n")
        
        print(f"[+] VTK cubic cells exported: {output_path}")
        print(f"    Format: Unstructured Grid (.vtk)")
        print(f"    Cell representation: 3D cubes (hexahedrons)")
        print(f"    Data: {len(positions)} cubes with {self.cell_size_um} um edge length")
        
        return output_path
    
    def export_initial_conditions(self, positions: np.ndarray, output_prefix: str = "initial_cells"):
        """
        Export initial conditions with all scalars set to 0
        
        Args:
            positions: Nx3 array of cell positions
            output_prefix: Output file prefix
        """
        # Create output directory
        output_dir = Path("tools/generated_h5")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # All cells start with scalar 0 (no ATP production)
        scalars = np.zeros(len(positions), dtype=int)
        
        # Generate output filename
        vtk_filename = output_dir / f"{output_prefix}_cells.vtk"
        
        return self.export_cubic_cells(
            positions=positions,
            scalars=scalars,
            output_path=str(vtk_filename),
            scalar_name="ATP_Type",
            title="Initial Cubic Cells from MicroC H5 Generator"
        )
    
    def export_simulation_state(self, cell_data: List[Tuple], output_dir: str, 
                               step: int, scalar_name: str = "ATP_Type"):
        """
        Export simulation state with ATP production scalars
        
        Args:
            cell_data: List of (position, atp_type) tuples
            output_dir: Output directory path
            step: Simulation step number
            scalar_name: Name of scalar field
        """
        if not cell_data:
            print("[!] No cell data to export")
            return None
        
        # Extract positions and ATP types
        positions = np.array([pos for pos, _ in cell_data])
        atp_types = np.array([atp_type for _, atp_type in cell_data])
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        vtk_filename = output_path / f"cells_step_{step:06d}.vtk"
        
        return self.export_cubic_cells(
            positions=positions,
            scalars=atp_types,
            output_path=str(vtk_filename),
            scalar_name=scalar_name,
            title=f"MicroC Simulation Cells - Step {step}"
        )


def get_atp_type_from_gene_states(gene_states: Dict[str, bool]) -> int:
    """
    Convert gene network states to ATP type scalar
    
    Args:
        gene_states: Dictionary of gene name -> boolean state
        
    Returns:
        ATP type: 0=none, 1=mitoATP, 2=glycoATP, 3=both
    """
    mito_atp = gene_states.get('mitoATP', False)
    glyco_atp = gene_states.get('glycoATP', False)
    
    if mito_atp and glyco_atp:
        return 3  # Both
    elif mito_atp and not glyco_atp:
        return 1  # Mito only
    elif not mito_atp and glyco_atp:
        return 2  # Glyco only
    else:
        return 0  # None


def get_atp_type_from_phenotype(phenotype: str) -> int:
    """
    Convert phenotype to ATP type scalar (fallback method)
    
    Args:
        phenotype: Cell phenotype string
        
    Returns:
        ATP type: 0=none, 1=mitoATP, 2=glycoATP, 3=both
    """
    # Simple mapping based on phenotype
    # This is a fallback - gene states are preferred
    if phenotype == "Proliferation":
        return 3  # Both ATP types for high energy demand
    elif phenotype == "Growth_Arrest":
        return 1  # Mito only for maintenance
    elif phenotype == "Apoptosis":
        return 0  # No ATP production
    else:  # Quiescent
        return 2  # Glyco only for basic metabolism


# Example usage functions
def export_h5_initial_conditions(positions: np.ndarray, cell_size_um: float, 
                                output_prefix: str) -> str:
    """Export initial conditions for H5 generator"""
    exporter = VTKCellExporter(cell_size_um)
    return exporter.export_initial_conditions(positions, output_prefix)


def export_microc_simulation_state(population, output_dir: str, step: int,
                                  cell_size_um: float) -> Optional[str]:
    """Export simulation state for MicroC"""
    exporter = VTKCellExporter(cell_size_um)

    # Extract cell data with ATP types
    cell_data = []
    for cell in population.state.cells.values():
        position = cell.state.position

        # Get ATP type from gene states (preferred method)
        if hasattr(cell.state, 'gene_states') and cell.state.gene_states:
            atp_type = get_atp_type_from_gene_states(cell.state.gene_states)
        else:
            # Fallback to phenotype-based mapping
            atp_type = get_atp_type_from_phenotype(cell.state.phenotype)

        cell_data.append((position, atp_type))

    return exporter.export_simulation_state(cell_data, output_dir, step)


def export_microc_substance_fields(simulator, output_dir: str, step: int) -> List[str]:
    """Export substance concentration fields to VTK format for MicroC simulation"""
    exporter = VTKSubstanceFieldExporter()
    return exporter.export_substance_fields(simulator, output_dir, step)


def export_microc_gene_states(population, output_dir: str, step: int) -> Optional[str]:
    """Export gene network states to H5 format for MicroC simulation"""
    import h5py
    from datetime import datetime

    if not population.state.cells:
        print("[!] No cells to export gene states")
        return None

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    h5_filename = output_path / f"gene_states_step_{step:06d}.h5"

    print(f"[*] Exporting gene network states...")
    print(f"    Cell count: {len(population.state.cells)}")
    print(f"    Step: {step}")

    with h5py.File(h5_filename, 'w') as f:
        # Create main group
        main_group = f.create_group('gene_states')

        # Store gene states for each cell
        for cell_id, cell in population.state.cells.items():
            cell_group = main_group.create_group(cell_id)

            # Get gene states from cell
            if hasattr(cell.state, 'gene_states') and cell.state.gene_states:
                gene_states = cell.state.gene_states
            else:
                # If no gene states, create empty dict
                gene_states = {}

            # Store each gene state
            for gene_name, state in gene_states.items():
                cell_group.create_dataset(gene_name, data=bool(state))

        # Create metadata group
        metadata_group = f.create_group('metadata')
        metadata_group.attrs['timestamp'] = datetime.now().isoformat()
        metadata_group.attrs['version'] = "MicroC-Simulation-2.0"
        metadata_group.attrs['cell_count'] = len(population.state.cells)
        metadata_group.attrs['step'] = step
        metadata_group.attrs['simulation_step'] = step

    print(f"[+] Gene network states exported: {h5_filename}")
    return str(h5_filename)


# ATP type legend for reference
ATP_TYPE_LEGEND = {
    0: "No ATP production",
    1: "Mitochondrial ATP only", 
    2: "Glycolytic ATP only",
    3: "Both ATP types"
}
