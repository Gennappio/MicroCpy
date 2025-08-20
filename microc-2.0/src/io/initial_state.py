#!/usr/bin/env python3
"""
Initial State Generator and Loader for MicroC 3D Simulations

Handles saving and loading of:
1. Cell positions (3D coordinates)
2. Gene network activation states for each cell

Uses HDF5 format for efficient storage of structured scientific data.
"""

import h5py  # Only for loading existing H5 files
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional, Any
from dataclasses import dataclass
import uuid
import json
from datetime import datetime
import re

from ..biology.cell import CellState
from ..config.config import MicroCConfig


@dataclass
class CellStateData:
    """Simplified cell state data for serialization"""
    id: str
    position: Tuple[float, float, float]  # Always 3D coordinates
    phenotype: str
    age: float
    division_count: int
    gene_states: Dict[str, bool]
    metabolic_state: Dict[str, float]
    tq_wait_time: float = 0.0


class VTKCellLoader:
    """Load cell positions and biological cell size from VTK cubic cell files"""

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"VTK file not found: {file_path}")

        self.cell_positions = []
        self.cell_size_um = None
        self.cell_count = 0

        self._load_vtk_file()

    def _load_vtk_file(self):
        """Parse VTK file to extract cell positions and size"""
        print(f"[VTK] Loading VTK cell positions from {self.file_path}")

        with open(self.file_path, 'r') as f:
            lines = f.readlines()

        # Parse VTK file structure
        points_section = False
        cells_section = False
        cell_data_section = False

        points = []
        cell_connectivity = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Find POINTS section
            if line.startswith('POINTS'):
                points_section = True
                num_points = int(line.split()[1])
                print(f"[*] Found {num_points} points in VTK file")
                i += 1
                continue

            # Find CELLS section
            elif line.startswith('CELLS'):
                points_section = False
                cells_section = True
                num_cells = int(line.split()[1])
                self.cell_count = num_cells
                print(f"[*] Found {num_cells} cells in VTK file")
                i += 1
                continue

            # Find CELL_DATA section
            elif line.startswith('CELL_DATA'):
                cells_section = False
                cell_data_section = True
                i += 1
                continue

            # Parse points
            elif points_section and line and not line.startswith('CELLS'):
                coords = list(map(float, line.split()))
                # Group coordinates into (x,y,z) triplets
                for j in range(0, len(coords), 3):
                    if j + 2 < len(coords):
                        points.append((coords[j], coords[j+1], coords[j+2]))

            # Parse cell connectivity (hexahedrons or points)
            elif cells_section and line and not line.startswith('CELL_TYPES'):
                parts = line.split()
                if len(parts) >= 9 and parts[0] == '8':  # Hexahedron with 8 vertices
                    vertex_indices = [int(x) for x in parts[1:9]]
                    cell_connectivity.append(('hexahedron', vertex_indices))
                elif len(parts) == 2 and parts[0] == '1':  # Point cell with 1 vertex
                    vertex_index = int(parts[1])
                    cell_connectivity.append(('point', [vertex_index]))

            i += 1

        # Calculate cell centers and size from hexahedron vertices
        self._calculate_cell_centers_and_size(points, cell_connectivity)

    def _calculate_cell_centers_and_size(self, points: List[Tuple[float, float, float]],
                                       connectivity: List[Tuple[str, List[int]]]):
        """Calculate cell centers and biological cell size from cell connectivity"""

        if not connectivity:
            raise ValueError("No valid cells found in VTK file")

        cell_centers = []
        edge_lengths = []

        # Check cell type
        cell_type, first_vertices = connectivity[0]

        if cell_type == 'hexahedron':
            # Handle cubic cells (8 vertices each)
            for cell_type, cell_vertices in connectivity:
                if cell_type != 'hexahedron':
                    continue

                # Get the 8 vertices of the hexahedron
                vertices = [points[i] for i in cell_vertices]

                # Calculate center as average of all vertices
                center_x = sum(v[0] for v in vertices) / 8
                center_y = sum(v[1] for v in vertices) / 8
                center_z = sum(v[2] for v in vertices) / 8

                cell_centers.append((center_x, center_y, center_z))

                # Calculate edge length (assuming cubic cells)
                # Use distance between first two vertices as edge length
                v0, v1 = vertices[0], vertices[1]
                edge_length = ((v1[0] - v0[0])**2 + (v1[1] - v0[1])**2 + (v1[2] - v0[2])**2)**0.5
                edge_lengths.append(edge_length)

        elif cell_type == 'point':
            # Handle point cells (1 vertex each) - assume spherical cells
            print(f"[*] Detected point cells (spherical), estimating cell size from point distribution")

            for cell_type, cell_vertices in connectivity:
                if cell_type != 'point':
                    continue

                # Get the single point
                vertex_index = cell_vertices[0]
                point = points[vertex_index]
                cell_centers.append(point)

            # Estimate cell size from nearest neighbor distances
            if len(cell_centers) >= 2:
                import numpy as np
                centers_array = np.array(cell_centers)

                # Calculate distances between all pairs of points
                distances = []
                for i in range(len(centers_array)):
                    for j in range(i+1, len(centers_array)):
                        dist = np.linalg.norm(centers_array[i] - centers_array[j])
                        if dist > 0:  # Avoid zero distances
                            distances.append(dist)

                if distances:
                    # Use median distance as cell size estimate
                    median_distance = np.median(distances)
                    edge_lengths = [median_distance] * len(cell_centers)
                    print(f"[*] Estimated cell size from point spacing: {median_distance*1e6:.2f} um")
                else:
                    # Fallback: assume 10 um cells
                    edge_lengths = [10e-6] * len(cell_centers)
                    print(f"[*] Using fallback cell size: 10.0 um")
            else:
                # Single cell or no cells - use fallback
                edge_lengths = [10e-6] * len(cell_centers)
                print(f"[*] Using fallback cell size: 10.0 um")
        else:
            raise ValueError(f"Unsupported cell type: {cell_type}")

        # Convert positions from meters to biological grid coordinates
        # Assuming VTK coordinates are in meters
        if edge_lengths:
            avg_edge_length_m = sum(edge_lengths) / len(edge_lengths)
            self.cell_size_um = avg_edge_length_m * 1e6  # Convert to micrometers

            print(f"[*] Detected biological cell size: {self.cell_size_um:.2f} um")

            # Convert cell centers to biological grid coordinates
            # First, find the bounding box to normalize coordinates to positive values
            min_x = min(center[0] for center in cell_centers)
            min_y = min(center[1] for center in cell_centers)
            min_z = min(center[2] for center in cell_centers)

            cell_size_m = avg_edge_length_m

            for center in cell_centers:
                # Shift coordinates to make them positive, then convert to grid coordinates
                bio_x = (center[0] - min_x) / cell_size_m
                bio_y = (center[1] - min_y) / cell_size_m
                bio_z = (center[2] - min_z) / cell_size_m
                self.cell_positions.append((bio_x, bio_y, bio_z))

        print(f"[+] Loaded {len(self.cell_positions)} cell positions")
        print(f"[+] Biological cell size: {self.cell_size_um:.2f} um")

    def get_cell_positions(self) -> List[Tuple[float, float, float]]:
        """Get cell positions in biological grid coordinates"""
        return self.cell_positions

    def get_cell_size_um(self) -> float:
        """Get biological cell size in micrometers"""
        return self.cell_size_um

    def get_cell_count(self) -> int:
        """Get number of cells"""
        return len(self.cell_positions)


class InitialStateManager:
    """
    Manages loading of initial cell states for MicroC simulations.

    NOTE: H5 file generation has been moved to external tools.
    Use: python run_microc.py --generate --cells 1000 --radius 50

    File format: HDF5 with the following structure:
    /metadata/
        - config_hash: str (hash of config for validation)
        - timestamp: str (creation time)
        - version: str (MicroC version)
        - cell_count: int (number of cells)
        - domain_info: dict (domain configuration)
    /cells/
        - ids: array of cell IDs
        - positions: Nx3 array of (x,y,z) coordinates in meters
        - phenotypes: array of phenotype strings
        - ages: array of cell ages
        - division_counts: array of division counts
        - tq_wait_times: array of TQ wait times
    /gene_states/
        - gene_names: array of gene names
        - states: NxM boolean array (N cells, M genes)
    /metabolic_states/
        - metabolite_names: array of metabolite names  
        - values: NxK float array (N cells, K metabolites)
    """
    
    def __init__(self, config: MicroCConfig):
        self.config = config
        
    def save_initial_state(self, cells: Dict[str, Any], file_path: Union[str, Path], 
                          step: int = 0) -> None:
        """
        DEPRECATED: H5 file generation has been moved to external tools.

        This method is no longer supported. Use the external H5 generator tool instead:
        python run_microc.py --generate --cells 1000 --radius 50

        Args:
            cells: Dictionary of cell_id -> Cell objects
            file_path: Path to save the HDF5 file
            step: Simulation step (for periodic saves)
        """
        print("⚠️  H5 file generation has been removed from the core MicroC system.")
        print("   Use the external H5 generator tool instead:")
        print("   python run_microc.py --generate --cells 1000 --radius 50")
        print(f"   Skipping H5 save to {file_path}")
        return
    
    def load_initial_state(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Load initial cell states from HDF5 file.
        
        Returns:
            List of cell initialization dictionaries compatible with CellPopulation.initialize_cells()
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Initial state file not found: {file_path}")
        
        print(f"[LOAD] Loading initial state from {file_path}")
        
        cell_init_data = []
        
        with h5py.File(file_path, 'r') as f:
            # Validate metadata
            if 'metadata' not in f:
                raise ValueError("Invalid initial state file: missing metadata")
            
            meta = f['metadata']
            cell_count = meta.attrs['cell_count']
            timestamp = meta.attrs['timestamp']
            version = meta.attrs.get('version', 'unknown')
            step = meta.attrs.get('step', 0)
            
            print(f"📊 File info: {cell_count} cells, created {timestamp}, version {version}, step {step}")
            
            # Validate domain compatibility
            if 'domain_info' in meta.attrs:
                domain_info = json.loads(meta.attrs['domain_info'])
                self._validate_domain_compatibility(domain_info)
            
            if cell_count == 0:
                print("⚠️  No cells in file")
                return []
            
            # Load cell data
            cells_group = f['cells']
            
            ids = [s.decode('utf-8') for s in cells_group['ids'][:]]
            positions = cells_group['positions'][:]
            phenotypes = [s.decode('utf-8') for s in cells_group['phenotypes'][:]]
            ages = cells_group['ages'][:]
            division_counts = cells_group['division_counts'][:]
            tq_wait_times = cells_group['tq_wait_times'][:]
            
            # Load gene states if available
            gene_states_dict = {}
            if 'gene_states' in f:
                gene_group = f['gene_states']
                gene_names = [s.decode('utf-8') for s in gene_group['gene_names'][:]]
                gene_matrix = gene_group['states'][:]
                
                # Convert matrix back to per-cell dictionaries
                for i in range(len(ids)):
                    gene_states_dict[ids[i]] = {
                        gene_names[j]: bool(gene_matrix[i, j]) 
                        for j in range(len(gene_names))
                    }
                
                print(f"[OK] Loaded gene states: {len(gene_names)} genes")
            
            # Load metabolic states if available
            metabolic_states_dict = {}
            if 'metabolic_states' in f:
                metab_group = f['metabolic_states']
                metabolite_names = [s.decode('utf-8') for s in metab_group['metabolite_names'][:]]
                metab_matrix = metab_group['values'][:]
                
                # Convert matrix back to per-cell dictionaries
                for i in range(len(ids)):
                    metabolic_states_dict[ids[i]] = {
                        metabolite_names[j]: float(metab_matrix[i, j])
                        for j in range(len(metabolite_names))
                    }
                
                print(f"[OK] Loaded metabolic states: {len(metabolite_names)} metabolites")
            
            # Create cell initialization data
            for i in range(len(ids)):
                # Convert 3D position back to 2D if needed for 2D simulations
                pos = tuple(positions[i])
                if self.config.domain.dimensions == 2:
                    pos = (pos[0], pos[1])  # Drop z coordinate
                
                cell_init_data.append({
                    'id': ids[i],
                    'position': pos,
                    'phenotype': phenotypes[i],
                    'age': float(ages[i]),
                    'division_count': int(division_counts[i]),
                    'gene_states': gene_states_dict.get(ids[i], {}),
                    'metabolic_state': metabolic_states_dict.get(ids[i], {}),
                    'tq_wait_time': float(tq_wait_times[i])
                })
        
        print(f"[OK] Successfully loaded {len(cell_init_data)} cells from {file_path}")
        return cell_init_data

    def load_initial_state_from_vtk(self, file_path: Union[str, Path]) -> Tuple[List[Dict[str, Any]], float]:
        """
        Load initial cell state from VTK domain file (enhanced format with gene networks and phenotypes).
        Falls back to basic VTK loading if enhanced format is not detected.

        Returns:
            Tuple of (cell_init_data, cell_size_um)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"VTK file not found: {file_path}")

        # Try to load as enhanced VTK domain file first
        try:
            # Check if this is an enhanced VTK domain file
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Check if description line contains metadata (genes= and phenotypes=)
                if len(lines) >= 2 and "|" in lines[1] and "genes=" in lines[1] and "phenotypes=" in lines[1]:
                    # This is an enhanced VTK domain file
                    print(f"[VTK] Detected enhanced VTK domain file")
                    return self._load_enhanced_vtk_domain(file_path)
        except Exception as e:
            print(f"[DEBUG] Enhanced VTK loading failed: {e}")

        # Fall back to basic VTK loading
        print(f"[VTK] Using basic VTK loading (legacy format)")
        return self._load_basic_vtk_file(file_path)

    def _load_enhanced_vtk_domain(self, file_path: Path) -> Tuple[List[Dict[str, Any]], float]:
        """Load enhanced VTK domain file with gene networks and phenotypes"""
        # Import VTK domain loader
        import sys
        sys.path.append('tools')
        from vtk_export import VTKDomainLoader

        # Load complete domain
        loader = VTKDomainLoader()
        domain_data = loader.load_complete_domain(str(file_path))

        positions = domain_data['positions']
        gene_states = domain_data['gene_states']
        phenotypes = domain_data['phenotypes']
        metabolism = domain_data.get('metabolism', [])
        metadata = domain_data['metadata']
        gene_nodes = domain_data.get('gene_nodes', [])

        # Use cell size from YAML config, not VTK metadata
        vtk_cell_size_um = metadata.get('biocell_grid_size_um', 20.0)

        # Get YAML cell height and convert to float if it's a Length object
        yaml_cell_height = getattr(self.config.domain, 'cell_height', 20.0)
        if hasattr(yaml_cell_height, 'value'):
            # It's a Length object, get the value in micrometers
            # The value is already in the correct unit (micrometers), just extract it
            yaml_cell_size_um = float(yaml_cell_height.value)
        else:
            # It's already a float in micrometers
            yaml_cell_size_um = float(yaml_cell_height)

        # Warning if VTK cube size differs from YAML cell height
        if abs(vtk_cell_size_um - yaml_cell_size_um) > 0.1:  # Allow small floating point differences
            print(f"[WARNING] VTK cube size ({vtk_cell_size_um:.2f} um) differs from YAML cell height ({yaml_cell_size_um:.2f} um)")
            print(f"[WARNING] Using YAML cell height: {yaml_cell_size_um:.2f} um")

        cell_size_um = yaml_cell_size_um

        print(f"[INFO] Enhanced VTK file info: {len(positions)} cells, VTK cube size: {vtk_cell_size_um:.2f} um, using YAML cell size: {cell_size_um:.2f} um")

        if len(positions) == 0:
            print("[!] No cells in VTK file")
            return [], cell_size_um

        # Create cell initialization data with loaded gene states and phenotypes
        cell_init_data = []

        for i, pos in enumerate(positions):
            # Convert 3D position to 2D if needed for 2D simulations
            if self.config.domain.dimensions == 2:
                pos = (pos[0], pos[1])  # Drop z coordinate

            # Generate unique cell ID
            cell_id = f"cell_{i:06d}"

            # Get gene states, phenotype, and metabolism for this cell
            vtk_gene_states = gene_states.get(i, {})
            cell_phenotype = phenotypes[i] if i < len(phenotypes) else 'Quiescent'
            cell_metabolism = metabolism[i] if i < len(metabolism) else 0

            # Initialize ALL gene network nodes for this cell
            # Ensure every gene node from VTK is properly initialized
            complete_gene_states = {}
            for gene_name in gene_nodes:
                # Use VTK gene state if available, otherwise default to False
                complete_gene_states[gene_name] = vtk_gene_states.get(gene_name, False)

            # Add any additional gene states from VTK that might not be in gene_nodes list
            for gene_name, state in vtk_gene_states.items():
                if gene_name not in complete_gene_states:
                    complete_gene_states[gene_name] = state

            # Create cell with loaded data
            cell_init_data.append({
                'id': cell_id,
                'position': pos,
                'phenotype': cell_phenotype,
                'age': 0.0,  # Default age (could be added to VTK format later)
                'division_count': 0,  # Default division count
                'gene_states': complete_gene_states,  # Complete gene network initialization
                'metabolic_state': {'metabolism': cell_metabolism},  # Store metabolism value
                'tq_wait_time': 0.0  # Default wait time
            })

        print(f"[OK] Successfully loaded {len(cell_init_data)} cells from enhanced VTK domain file")
        print(f"[OK] Using biological cell size: {cell_size_um:.2f} um (from YAML config)")
        print(f"[OK] Initialized gene networks: {len(gene_nodes)} nodes per cell")
        print(f"[OK] Loaded phenotypes: {len(set(phenotypes))} unique types")

        # Debug: Show first cell's gene states to verify initialization
        if cell_init_data and gene_nodes:
            first_cell_genes = cell_init_data[0]['gene_states']
            active_genes = sum(1 for state in first_cell_genes.values() if state)
            print(f"[DEBUG] First cell has {active_genes}/{len(first_cell_genes)} active genes")

        return cell_init_data, cell_size_um

    def _load_basic_vtk_file(self, file_path: Path) -> Tuple[List[Dict[str, Any]], float]:
        """Load basic VTK file (legacy format) with only positions"""
        # Load VTK file using existing loader
        vtk_loader = VTKCellLoader(file_path)
        positions = vtk_loader.get_cell_positions()
        cell_size_um = vtk_loader.get_cell_size_um()

        print(f"[INFO] Basic VTK file info: {len(positions)} cells, {cell_size_um:.2f} um cell size")

        if not positions:
            print("[!] No cells in VTK file")
            return [], cell_size_um

        # Create cell initialization data with default values
        cell_init_data = []

        for i, pos in enumerate(positions):
            # Convert 3D position to 2D if needed for 2D simulations
            if self.config.domain.dimensions == 2:
                pos = (pos[0], pos[1])  # Drop z coordinate

            # Generate unique cell ID
            cell_id = f"cell_{i:06d}"

            # Create cell with default values
            cell_init_data.append({
                'id': cell_id,
                'position': pos,
                'phenotype': 'Quiescent',  # Default phenotype
                'age': 0.0,  # Default age
                'division_count': 0,  # Default division count
                'gene_states': {},  # Empty gene states (will be initialized by gene network)
                'metabolic_state': {},  # Empty metabolic state
                'tq_wait_time': 0.0  # Default wait time
            })

        print(f"[OK] Successfully loaded {len(cell_init_data)} cells from basic VTK file")
        print(f"[OK] Detected biological cell size: {cell_size_um:.2f} um")

        return cell_init_data, cell_size_um
    
    def _compute_config_hash(self) -> str:
        """Compute a hash of the configuration for validation"""
        # Simple hash based on key domain parameters
        domain_str = f"{self.config.domain.dimensions}_{self.config.domain.nx}_{self.config.domain.ny}_{self.config.domain.nz}"
        return str(hash(domain_str))
    
    def _validate_domain_compatibility(self, saved_domain_info: Dict[str, Any]) -> None:
        """Validate that saved domain is compatible with current config"""
        current_domain = self.config.domain
        
        # Check dimensions
        if saved_domain_info['dimensions'] != current_domain.dimensions:
            raise ValueError(f"Domain dimension mismatch: saved {saved_domain_info['dimensions']}D, "
                           f"current {current_domain.dimensions}D")
        
        # Check grid size
        if (saved_domain_info['nx'] != current_domain.nx or 
            saved_domain_info['ny'] != current_domain.ny):
            print(f"⚠️  Grid size mismatch: saved ({saved_domain_info['nx']}, {saved_domain_info['ny']}), "
                  f"current ({current_domain.nx}, {current_domain.ny})")
        
        # Check domain size
        size_tolerance = 1e-6  # 1 um tolerance
        if (abs(saved_domain_info['size_x'] - current_domain.size_x.meters) > size_tolerance or
            abs(saved_domain_info['size_y'] - current_domain.size_y.meters) > size_tolerance):
            print(f"⚠️  Domain size mismatch: saved ({saved_domain_info['size_x']:.6f}, {saved_domain_info['size_y']:.6f}) m, "
                  f"current ({current_domain.size_x.meters:.6f}, {current_domain.size_y.meters:.6f}) m")
        
        print("[OK] Domain compatibility validated")


def generate_initial_state_filename(config: MicroCConfig, step: int = 0) -> str:
    """Generate a standardized filename for initial state files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dimensions = f"{config.domain.dimensions}D"
    grid = f"{config.domain.nx}x{config.domain.ny}"
    if config.domain.dimensions == 3 and config.domain.nz:
        grid += f"x{config.domain.nz}"
    
    if step == 0:
        return f"initial_state_{dimensions}_{grid}_{timestamp}.h5"
    else:
        return f"cell_state_step{step:06d}_{dimensions}_{grid}_{timestamp}.h5"
