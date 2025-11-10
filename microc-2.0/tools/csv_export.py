#!/usr/bin/env python3
"""
CSV Export Module for MicroC 2.0 - 2D Simulation Results

This module provides CSV export functionality for 2D simulations, equivalent to VTK export for 3D:
1. Cell state export (positions, gene states, phenotypes)
2. Substance field export (concentration grids)

CSV format is human-readable and easily processed by analysis tools.
"""

import csv
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class CSVCellStateExporter:
    """CSV export functionality for cell states during simulation"""

    def __init__(self, cell_size_um: float = 20.0):
        """Initialize with cell size in micrometers"""
        self.cell_size_um = cell_size_um

    def export_simulation_state(self, population, output_dir: str, step: int) -> Optional[str]:
        """
        Export complete cell state to CSV format
        
        Args:
            population: Cell population object
            output_dir: Output directory path
            step: Simulation step number
            
        Returns:
            Path to exported CSV file
        """
        if not population.state.cells:
            print("[!] No cells to export")
            return None

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate output filename
        csv_filename = output_path / f"cells_step_{step:06d}.csv"

        # Extract cell data
        cells_data = []
        for i, (cell_id, cell) in enumerate(population.state.cells.items()):
            cell_data = {
                'cell_id': cell_id,
                'x': cell.state.position[0],
                'y': cell.state.position[1],
                'phenotype': cell.state.phenotype,
                'age': getattr(cell.state, 'age', 0.0),
                'generation': getattr(cell.state, 'generation', 0)
            }

            # Add gene states if available
            if hasattr(cell.state, 'gene_states') and cell.state.gene_states:
                for gene_name, state in cell.state.gene_states.items():
                    cell_data[f'gene_{gene_name}'] = 'true' if state else 'false'

            cells_data.append(cell_data)

        # Write CSV file
        if cells_data:
            fieldnames = list(cells_data[0].keys())
            
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                # Write metadata header
                f.write(f'# MicroC 2D Cell States - Step {step}\n')
                f.write(f'# Generated: {datetime.now().isoformat()}\n')
                f.write(f'# Cell count: {len(cells_data)}\n')
                f.write(f'# Cell size: {self.cell_size_um} um\n')
                f.write(f'# Coordinate system: logical grid positions\n')
                
                # Write CSV data
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(cells_data)

            print(f"[+] CSV cell state exported: {csv_filename.name}")
            return str(csv_filename)

        return None


class CSVSubstanceFieldExporter:
    """CSV export functionality for substance concentration fields"""

    def __init__(self):
        """Initialize CSV substance field exporter"""
        pass

    def export_substance_fields(self, simulator, output_dir: str, step: int) -> List[str]:
        """
        Export all substance concentration fields to CSV format
        
        Args:
            simulator: Multi-substance simulator with FiPy variables
            output_dir: Output directory path
            step: Simulation step number
            
        Returns:
            List of exported CSV file paths
        """
        try:
            import fipy
            FIPY_AVAILABLE = True
        except ImportError:
            FIPY_AVAILABLE = False

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
        print(f"[CSV] Exporting substance fields for step {step}...")

        for substance_name, fipy_var in simulator.fipy_variables.items():
            try:
                # Generate output filename
                csv_filename = output_path / f"{substance_name}_field_step_{step:06d}.csv"

                # Export this substance field
                success = self._export_single_substance_field(
                    substance_name=substance_name,
                    fipy_var=fipy_var,
                    mesh=simulator.fipy_mesh,
                    output_path=str(csv_filename),
                    step=step
                )

                if success:
                    exported_files.append(str(csv_filename))
                    print(f"   [OK] {substance_name}: {csv_filename.name}")
                else:
                    print(f"   [!] Failed to export {substance_name}")

            except Exception as e:
                print(f"   [!] Error exporting {substance_name}: {e}")

        print(f"[CSV] Exported {len(exported_files)} substance field files")
        return exported_files

    def _export_single_substance_field(self, substance_name: str, fipy_var, mesh, 
                                     output_path: str, step: int) -> bool:
        """Export a single substance field to CSV"""
        try:
            # Get concentration values
            concentration_values = np.array(fipy_var.value)
            
            # Get mesh information
            cell_centers = mesh.cellCenters
            x_centers = np.array(cell_centers[0])
            y_centers = np.array(cell_centers[1])

            # Determine grid dimensions
            unique_x = np.unique(x_centers)
            unique_y = np.unique(y_centers)
            nx, ny = len(unique_x), len(unique_y)

            # Create structured data
            field_data = []
            for i, (x, y, conc) in enumerate(zip(x_centers, y_centers, concentration_values)):
                field_data.append({
                    'x_position_m': float(x),
                    'y_position_m': float(y),
                    'x_position_um': float(x * 1e6),
                    'y_position_um': float(y * 1e6),
                    'grid_index': i,
                    f'{substance_name}_concentration_mM': float(conc)
                })

            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                # Write metadata header
                f.write(f'# MicroC 2D Substance Field: {substance_name} - Step {step}\n')
                f.write(f'# Generated: {datetime.now().isoformat()}\n')
                f.write(f'# Grid dimensions: {nx} x {ny}\n')
                f.write(f'# Total grid points: {len(field_data)}\n')
                f.write(f'# Coordinate system: physical positions (meters and micrometers)\n')
                
                # Write CSV data
                if field_data:
                    fieldnames = list(field_data[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(field_data)

            return True

        except Exception as e:
            print(f"[!] Error exporting {substance_name} field: {e}")
            return False


# Main export functions (equivalent to VTK export functions)

def export_microc_csv_cell_state(population, output_dir: str, step: int, 
                                cell_size_um: float = 20.0) -> Optional[str]:
    """Export cell state to CSV format for MicroC simulation"""
    exporter = CSVCellStateExporter(cell_size_um)
    return exporter.export_simulation_state(population, output_dir, step)


def export_microc_csv_substance_fields(simulator, output_dir: str, step: int) -> List[str]:
    """Export substance concentration fields to CSV format for MicroC simulation"""
    exporter = CSVSubstanceFieldExporter()
    return exporter.export_substance_fields(simulator, output_dir, step)


# Utility functions for analysis

def load_csv_cell_state(csv_path: str) -> Dict[str, Any]:
    """Load cell state data from CSV file"""
    cells = []
    metadata = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Read metadata from header comments
        for line in f:
            if line.startswith('#'):
                if 'Cell count:' in line:
                    metadata['cell_count'] = int(line.split(':')[1].strip())
                elif 'Cell size:' in line:
                    metadata['cell_size_um'] = float(line.split(':')[1].strip().split()[0])
                elif 'Step' in line:
                    metadata['step'] = int(line.split('Step')[1].strip())
            else:
                # Reset file pointer to start of CSV data
                f.seek(0)
                # Skip comment lines
                while True:
                    pos = f.tell()
                    line = f.readline()
                    if not line.startswith('#'):
                        f.seek(pos)
                        break
                
                # Read CSV data
                reader = csv.DictReader(f)
                for row in reader:
                    cells.append(row)
                break
    
    return {'cells': cells, 'metadata': metadata}


def load_csv_substance_field(csv_path: str) -> Dict[str, Any]:
    """Load substance field data from CSV file"""
    field_data = []
    metadata = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Read metadata from header comments
        for line in f:
            if line.startswith('#'):
                if 'Grid dimensions:' in line:
                    dims = line.split(':')[1].strip().split('x')
                    metadata['nx'] = int(dims[0].strip())
                    metadata['ny'] = int(dims[1].strip())
                elif 'Total grid points:' in line:
                    metadata['total_points'] = int(line.split(':')[1].strip())
                elif 'Step' in line:
                    metadata['step'] = int(line.split('Step')[1].strip())
            else:
                # Reset file pointer to start of CSV data
                f.seek(0)
                # Skip comment lines
                while True:
                    pos = f.tell()
                    line = f.readline()
                    if not line.startswith('#'):
                        f.seek(pos)
                        break
                
                # Read CSV data
                reader = csv.DictReader(f)
                for row in reader:
                    field_data.append(row)
                break
    
    return {'field_data': field_data, 'metadata': metadata}
