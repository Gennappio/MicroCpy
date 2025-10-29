#!/usr/bin/env python3
"""
Initial State Loader for MicroC Simulations

Handles loading of:
1. Cell positions (2D/3D coordinates)
2. Gene network activation states for each cell (when embedded)

Supported formats:
- VTK: For 3D simulations and complex 2D setups with gene networks
- CSV: For simple 2D simulations (human-readable format)

HDF5 support has been removed.
"""

# HDF5 support removed
import numpy as np
import csv
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
            # Preserve centered positioning (don't shift to positive values)
            cell_size_m = avg_edge_length_m

            for center in cell_centers:
                # Convert directly to biological grid coordinates (preserve centering around 0,0,0)
                bio_x = center[0] / cell_size_m
                bio_y = center[1] / cell_size_m
                bio_z = center[2] / cell_size_m
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


class CSVCellLoader:
    """Load 2D cell positions from CSV files (human-readable format)"""

    def __init__(self, file_path: Union[str, Path], cell_size_um: float = 20.0):
        """
        Initialize CSV cell loader

        Args:
            file_path: Path to CSV file
            cell_size_um: Cell size in micrometers (from YAML config)
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        self.cell_positions = []
        self.cell_size_um = cell_size_um
        self.cell_count = 0
        self.gene_states = {}
        self.phenotypes = []
        self.ages = []  # Store cell ages from checkpoint files
        self.generations = []  # Store cell generations from checkpoint files
        self.metadata = {}

        self._load_csv_file()

    def _load_csv_file(self):
        """Parse CSV file to extract cell positions and optional metadata"""
        print(f"[CSV] Loading 2D cell positions from {self.file_path}")

        with open(self.file_path, 'r', encoding='utf-8') as f:
            # Read all lines to detect format
            all_lines = f.readlines()

        # Detect if this is a checkpoint file (unified format)
        is_checkpoint = any('SECTION 1: CELLS' in line for line in all_lines[:20])

        if is_checkpoint:
            print("[CSV] Detected checkpoint format (unified CSV with cells + substances)")
            self._load_checkpoint_format(all_lines)
        else:
            print("[CSV] Detected initial state format (simple CSV)")
            self._load_simple_format(all_lines)

        self.cell_count = len(self.cell_positions)
        print(f"[+] Loaded {self.cell_count} cells from CSV")
        print(f"[+] Cell size: {self.cell_size_um:.2f} um (from YAML config)")

        if self.phenotypes:
            unique_phenotypes = set(self.phenotypes)
            print(f"[+] Phenotypes: {len(unique_phenotypes)} types ({', '.join(unique_phenotypes)})")

        if any(self.gene_states.values()):
            gene_names = set()
            for cell_genes in self.gene_states.values():
                gene_names.update(cell_genes.keys())
            print(f"[+] Gene states: {len(gene_names)} genes ({', '.join(sorted(gene_names))})")

    def _load_simple_format(self, all_lines):
        """Load simple initial state CSV format"""
        # Parse metadata from first line if it's a comment
        if all_lines and all_lines[0].strip().startswith('#'):
            self._parse_metadata_comment(all_lines[0].strip())
            all_lines = all_lines[1:]  # Skip metadata line

        # Parse CSV data
        reader = csv.DictReader(all_lines)

        # Validate required columns
        required_cols = ['x', 'y']
        if not all(col in reader.fieldnames for col in required_cols):
            raise ValueError(f"CSV must contain columns: {required_cols}. Found: {reader.fieldnames}")

        # Optional columns
        has_phenotype = 'phenotype' in reader.fieldnames
        has_age = 'age' in reader.fieldnames

        # Parse gene state columns (any column starting with 'gene_')
        gene_columns = [col for col in reader.fieldnames if col.startswith('gene_')]

        for i, row in enumerate(reader):
            try:
                # Parse logical coordinates (may be float, will be rounded)
                x_logical = float(row['x'])
                y_logical = float(row['y'])

                # Store as logical coordinates (same as VTK system)
                self.cell_positions.append((x_logical, y_logical))

                # Parse phenotype if available
                phenotype = row.get('phenotype', 'Quiescent').strip()
                self.phenotypes.append(phenotype)

                # Parse gene states if available
                cell_gene_states = {}
                for gene_col in gene_columns:
                    gene_name = gene_col.replace('gene_', '')  # Remove 'gene_' prefix
                    gene_value = row[gene_col].strip().lower()
                    # Convert to boolean
                    cell_gene_states[gene_name] = gene_value in ('true', '1', 'yes', 'on', 'active')

                self.gene_states[i] = cell_gene_states

            except (ValueError, KeyError) as e:
                print(f"[WARNING] Skipping invalid row {i+1}: {e}")
                continue

    def _load_checkpoint_format(self, all_lines):
        """Load checkpoint CSV format (unified format with cells + substances)"""
        # Find the CELLS section
        cells_section_start = None
        cells_section_end = None

        for i, line in enumerate(all_lines):
            if 'SECTION 1: CELLS' in line:
                cells_section_start = i + 1  # Next line after section marker
            elif 'SECTION 2: SUBSTANCES' in line:
                cells_section_end = i - 1  # Line before section marker
                break

        if cells_section_start is None:
            raise ValueError("Could not find CELLS section in checkpoint file")

        # Extract cell data lines (skip comments)
        cell_lines = []
        for i in range(cells_section_start, cells_section_end + 1 if cells_section_end else len(all_lines)):
            line = all_lines[i].strip()
            if line and not line.startswith('#'):
                cell_lines.append(line)

        if not cell_lines:
            print("[WARNING] No cell data found in checkpoint file")
            return

        # Parse cell data
        reader = csv.DictReader(cell_lines)

        # Validate required columns (checkpoint format uses 'cell_id' and has 'age', 'generation')
        required_cols = ['x', 'y']
        if not all(col in reader.fieldnames for col in required_cols):
            raise ValueError(f"Checkpoint CSV must contain columns: {required_cols}. Found: {reader.fieldnames}")

        # Check if checkpoint has age and generation columns
        has_age = 'age' in reader.fieldnames
        has_generation = 'generation' in reader.fieldnames

        # Parse gene state columns (any column starting with 'gene_')
        gene_columns = [col for col in reader.fieldnames if col.startswith('gene_')]

        for i, row in enumerate(reader):
            try:
                # Parse logical coordinates (may be float, will be rounded)
                x_logical = float(row['x'])
                y_logical = float(row['y'])

                # Store as logical coordinates
                self.cell_positions.append((x_logical, y_logical))

                # Parse phenotype
                phenotype = row.get('phenotype', 'Quiescent').strip()
                self.phenotypes.append(phenotype)

                # Parse age and generation if available
                if has_age:
                    age = float(row.get('age', 0.0))
                    self.ages.append(age)
                else:
                    self.ages.append(0.0)

                if has_generation:
                    generation = int(row.get('generation', 0))
                    self.generations.append(generation)
                else:
                    self.generations.append(0)

                # Parse gene states
                cell_gene_states = {}
                for gene_col in gene_columns:
                    gene_name = gene_col.replace('gene_', '')  # Remove 'gene_' prefix
                    gene_value = row[gene_col].strip().lower()
                    # Convert to boolean
                    cell_gene_states[gene_name] = gene_value in ('true', '1', 'yes', 'on', 'active')

                self.gene_states[i] = cell_gene_states

            except (ValueError, KeyError) as e:
                print(f"[WARNING] Skipping invalid row {i+1}: {e}")
                continue

    def _parse_metadata_comment(self, comment_line: str):
        """Parse metadata from CSV comment line"""
        # Example: # cell_size_um=20.0, domain_size_um=500.0, description="Spheroid initial state"
        try:
            # Remove '#' and split by commas
            metadata_str = comment_line[1:].strip()
            for item in metadata_str.split(','):
                if '=' in item:
                    key, value = item.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')  # Remove quotes

                    # Try to convert to appropriate type
                    try:
                        if '.' in value:
                            self.metadata[key] = float(value)
                        else:
                            self.metadata[key] = int(value)
                    except ValueError:
                        self.metadata[key] = value
        except Exception as e:
            print(f"[WARNING] Could not parse metadata comment: {e}")

    def get_cell_positions(self) -> List[Tuple[float, float]]:
        """Get cell positions in logical grid coordinates"""
        return self.cell_positions

    def get_cell_size_um(self) -> float:
        """Get biological cell size in micrometers"""
        return self.cell_size_um

    def get_cell_count(self) -> int:
        """Get number of cells"""
        return len(self.cell_positions)

    def get_gene_states(self) -> Dict[int, Dict[str, bool]]:
        """Get gene states for all cells"""
        return self.gene_states

    def get_phenotypes(self) -> List[str]:
        """Get phenotypes for all cells"""
        return self.phenotypes

    def get_ages(self) -> List[float]:
        """Get ages for all cells (from checkpoint files)"""
        return self.ages

    def get_generations(self) -> List[int]:
        """Get generations for all cells (from checkpoint files)"""
        return self.generations

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata from CSV file"""
        return self.metadata


class InitialStateManager:
    """
    Manages loading of initial cell states for MicroC simulations (VTK-based).
    """

    def __init__(self, config: MicroCConfig):
        self.config = config
        
    def save_initial_state(self, cells: Dict[str, Any], file_path: Union[str, Path],
                          step: int = 0) -> None:
        """HDF5 save removed; VTK is the only supported format."""
        raise NotImplementedError("Saving initial state is no longer supported here. Use VTK export utilities if needed.")
    
    def load_initial_state(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Auto-detect file format and load initial state.

        Supports:
        - .vtk files: For 3D simulations and complex 2D setups
        - .csv files: For simple 2D simulations (human-readable)

        Returns:
            Tuple of (cell_init_data, cell_size_um)
        """
        file_path = Path(file_path)

        if file_path.suffix.lower() == '.csv':
            return self.load_initial_state_from_csv(file_path)
        elif file_path.suffix.lower() == '.vtk':
            return self.load_initial_state_from_vtk(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}. Use .csv for 2D or .vtk for 2D/3D")

    def load_initial_state_from_csv(self, file_path: Union[str, Path]) -> Tuple[List[Dict[str, Any]], float]:
        """
        Load initial cell state from CSV file (2D only, human-readable format).

        CSV Format:
        - Required columns: x, y (logical grid coordinates)
        - Optional columns: phenotype, age, gene_<name> (for gene states)
        - Optional metadata comment line: # cell_size_um=20.0, description="..."

        Returns:
            Tuple of (cell_init_data, cell_size_um)
        """
        if self.config.domain.dimensions != 2:
            raise ValueError("CSV loading is only supported for 2D simulations. Use VTK for 3D.")

        # Get cell size from YAML config
        yaml_cell_height = getattr(self.config.domain, 'cell_height', 20.0)
        if hasattr(yaml_cell_height, 'value'):
            yaml_cell_size_um = float(yaml_cell_height.value)
        else:
            yaml_cell_size_um = float(yaml_cell_height)

        # Load CSV file
        csv_loader = CSVCellLoader(file_path, yaml_cell_size_um)
        positions = csv_loader.get_cell_positions()
        cell_size_um = csv_loader.get_cell_size_um()
        gene_states_dict = csv_loader.get_gene_states()
        phenotypes = csv_loader.get_phenotypes()
        ages = csv_loader.get_ages()  # Get ages from checkpoint files
        generations = csv_loader.get_generations()  # Get generations from checkpoint files

        print(f"[INFO] CSV file info: {len(positions)} cells, {cell_size_um:.2f} um cell size")

        if not positions:
            print("[!] No cells in CSV file")
            return [], cell_size_um

        # Create cell initialization data
        cell_init_data = []

        # Calculate biological grid bounds for validation
        bio_grid_x = int(self.config.domain.size_x.micrometers / self.config.domain.cell_height.micrometers)
        bio_grid_y = int(self.config.domain.size_y.micrometers / self.config.domain.cell_height.micrometers)

        for i, pos in enumerate(positions):
            # Read logical coordinates and round to nearest integer grid index
            x_log = int(round(pos[0]))
            y_log = int(round(pos[1]))

            # Clamp to valid biological grid bounds
            x_log = max(0, min(bio_grid_x - 1, x_log))
            y_log = max(0, min(bio_grid_y - 1, y_log))

            # Create 2D position tuple
            logical_pos = (x_log, y_log)

            # Generate unique cell ID
            cell_id = f"cell_{i:06d}"

            # Get phenotype for this cell
            cell_phenotype = phenotypes[i] if i < len(phenotypes) else 'Quiescent'

            # Get gene states for this cell
            cell_gene_states = gene_states_dict.get(i, {})

            # Get age and generation for this cell (from checkpoint files)
            cell_age = ages[i] if i < len(ages) else 0.0
            cell_generation = generations[i] if i < len(generations) else 0

            # Compute physical position from YAML cell size and logical indices
            original_physical_pos = (
                logical_pos[0] * cell_size_um,
                logical_pos[1] * cell_size_um,
                0.0  # Z coordinate is 0 for 2D
            )

            # Create cell with loaded data
            cell_init_data.append({
                'id': cell_id,
                'position': logical_pos,  # Logical position for simulation
                'original_physical_position': original_physical_pos,  # Physical position (um)
                'phenotype': cell_phenotype,
                'age': cell_age,  # Age from checkpoint or default 0.0
                'division_count': cell_generation,  # Generation from checkpoint or default 0
                'gene_states': cell_gene_states,  # Gene network initialization from CSV
                'metabolic_state': {},  # Empty metabolic state
                'tq_wait_time': 0.0  # Default wait time
            })

        print(f"[OK] Successfully loaded {len(cell_init_data)} cells from CSV file")
        print(f"[OK] Using biological cell size: {cell_size_um:.2f} um (from YAML config)")

        if any(gene_states_dict.values()):
            gene_names = set()
            for cell_genes in gene_states_dict.values():
                gene_names.update(cell_genes.keys())
            print(f"[OK] Initialized gene networks: {len(gene_names)} nodes per cell")

        unique_phenotypes = set(phenotypes) if phenotypes else {'Quiescent'}
        print(f"[OK] Loaded phenotypes: {len(unique_phenotypes)} unique types")

        return cell_init_data, cell_size_um

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
        # Import VTK domain loader from library module
        from .vtk_domain_loader import VTKDomainLoader

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

        # Calculate biological grid size (from domain config)
        bio_grid_x = int(self.config.domain.size_x.micrometers / self.config.domain.cell_height.micrometers)
        bio_grid_y = int(self.config.domain.size_y.micrometers / self.config.domain.cell_height.micrometers)
        bio_grid_z = int(self.config.domain.size_z.micrometers / self.config.domain.cell_height.micrometers) if self.config.domain.dimensions == 3 else 1

        # Positions coming from VTK are LOGICAL coordinates. Use them directly as grid indices.
        for i, pos in enumerate(positions):
            # Read logical coordinates (may be float); round to nearest integer grid index
            x_log = int(round(pos[0]))
            y_log = int(round(pos[1]))
            z_log = int(round(pos[2])) if (self.config.domain.dimensions == 3 and len(pos) > 2) else 0

            # Clamp to valid biological grid bounds
            x_log = max(0, min(bio_grid_x - 1, x_log))
            y_log = max(0, min(bio_grid_y - 1, y_log))
            z_log = max(0, min(bio_grid_z - 1, z_log)) if self.config.domain.dimensions == 3 else 0

            # Create position tuple in logical grid coordinates
            if self.config.domain.dimensions == 2:
                logical_pos = (x_log, y_log)
            else:
                logical_pos = (x_log, y_log, z_log)

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

            # Compute physical position strictly from YAML cell size and logical indices
            # Logical (grid) coordinates come from VTK; YAML cell size defines the physical spacing
            original_physical_pos = (
                logical_pos[0] * cell_size_um,
                logical_pos[1] * cell_size_um,
                (logical_pos[2] if len(logical_pos) > 2 else 0) * cell_size_um
            )

            # Create cell with loaded data
            cell_init_data.append({
                'id': cell_id,
                'position': logical_pos,  # Logical position for simulation
                'original_physical_position': original_physical_pos,  # Original physical position (um)
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

        # Clean up any potential Unicode issues in gene node names
        for cell_data in cell_init_data:
            # Ensure gene state keys are clean ASCII strings
            clean_gene_states = {}
            for gene_name, state in cell_data['gene_states'].items():
                # Convert gene name to clean ASCII string
                clean_gene_name = str(gene_name).encode('ascii', 'ignore').decode('ascii')
                clean_gene_states[clean_gene_name] = bool(state)
            cell_data['gene_states'] = clean_gene_states

            # Ensure phenotype is clean ASCII string
            cell_data['phenotype'] = str(cell_data['phenotype']).encode('ascii', 'ignore').decode('ascii')

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

        # Calculate logical grid bounds for validation
        domain_size_um = self.config.domain.size_x.micrometers
        cell_height_um = self.config.domain.cell_height.micrometers
        # Use actual grid dimensions from config instead of calculated value
        grid_max = self.config.domain.nx - 1  # e.g., 25-1 = 24 (max index)

        # Find physical coordinate bounds to center them properly
        if positions:
            # Positions are already in micrometers from VTKCellLoader
            x_coords_um = [pos[0] for pos in positions]
            y_coords_um = [pos[1] for pos in positions]
            z_coords_um = [(pos[2] if len(pos) > 2 else 0) for pos in positions]

            x_min_um, x_max_um = min(x_coords_um), max(x_coords_um)
            y_min_um, y_max_um = min(y_coords_um), max(y_coords_um)
            z_min_um, z_max_um = min(z_coords_um), max(z_coords_um)

            # Calculate center offset to shift coordinates to positive domain
            x_center_um = (x_min_um + x_max_um) / 2
            y_center_um = (y_min_um + y_max_um) / 2
            z_center_um = (z_min_um + z_max_um) / 2

            # Calculate domain center for positioning
            domain_center_um = domain_size_um / 2

            print(f"[INFO] VTK physical ranges (um): X({x_min_um:.1f}, {x_max_um:.1f}), Y({y_min_um:.1f}, {y_max_um:.1f}), Z({z_min_um:.1f}, {z_max_um:.1f})")
            print(f"[INFO] VTK center (um): ({x_center_um:.1f}, {y_center_um:.1f}, {z_center_um:.1f})")
            print(f"[INFO] Domain center (um): {domain_center_um:.1f}")
            print(f"[INFO] Cell height: {cell_height_um} um")
            print(f"[INFO] Logical grid bounds: (0, {grid_max})")
        else:
            x_center_um = y_center_um = z_center_um = 0
            domain_center_um = domain_size_um / 2

        for i, pos in enumerate(positions):
            # Convert physical positions (micrometers) to logical grid coordinates
            # 1. Shift to center the VTK coordinates in the domain
            # 2. Convert to logical coordinates (grid units)

            # Positions are already in micrometers from VTKCellLoader
            x_um = pos[0]
            y_um = pos[1]
            z_um = (pos[2] if len(pos) > 2 else 0)

            # Shift coordinates to center VTK data in the domain
            x_shifted_um = x_um - x_center_um + domain_center_um
            y_shifted_um = y_um - y_center_um + domain_center_um
            z_shifted_um = z_um - z_center_um + domain_center_um

            # Convert from physical coordinates (um) to logical coordinates (grid units)
            x_logical = x_shifted_um / cell_height_um
            y_logical = y_shifted_um / cell_height_um
            z_logical = z_shifted_um / cell_height_um

            # Convert 3D position to 2D if needed for 2D simulations
            if self.config.domain.dimensions == 2:
                pos = (float(x_logical), float(y_logical))  # Drop z coordinate
            else:
                pos = (float(x_logical), float(y_logical), float(z_logical))

            # Generate unique cell ID
            cell_id = f"cell_{i:06d}"

            # Store original physical position for VTK export preservation
            # Positions from VTKCellLoader are biological grid coordinates, convert to physical coordinates (um)
            original_physical_pos = (
                positions[i][0] * cell_size_um,  # Convert logical grid to physical um
                positions[i][1] * cell_size_um,
                (positions[i][2] if len(positions[i]) > 2 else 0) * cell_size_um
            )

            # Create cell with default values
            cell_init_data.append({
                'id': cell_id,
                'position': pos,  # Logical position for simulation
                'original_physical_position': original_physical_pos,  # Original physical position (um)
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
            print(f"[WARNING]  Grid size mismatch: saved ({saved_domain_info['nx']}, {saved_domain_info['ny']}), "
                  f"current ({current_domain.nx}, {current_domain.ny})")
        
        # Check domain size
        size_tolerance = 1e-6  # 1 um tolerance
        if (abs(saved_domain_info['size_x'] - current_domain.size_x.meters) > size_tolerance or
            abs(saved_domain_info['size_y'] - current_domain.size_y.meters) > size_tolerance):
            print(f"[WARNING]  Domain size mismatch: saved ({saved_domain_info['size_x']:.6f}, {saved_domain_info['size_y']:.6f}) m, "
                  f"current ({current_domain.size_x.meters:.6f}, {current_domain.size_y.meters:.6f}) m")
        
        print("[OK] Domain compatibility validated")

