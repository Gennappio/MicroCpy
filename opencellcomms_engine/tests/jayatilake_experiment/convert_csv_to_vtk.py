#!/usr/bin/env python3
"""
Convert 2D CSV checkpoint to 3D VTK checkpoint (standalone version).

This script converts a 2D CSV checkpoint file to a 3D VTK format that can be
loaded in 3D simulations. Cells from the 2D plane are placed at z=50 (center).
"""

import csv
from pathlib import Path


def write_vtk_domain(file_path, positions, gene_states_list, phenotypes, metabolism, gene_nodes, metadata):
    """Write VTK domain file with cell data."""
    
    # Prepare gene states data structure
    gene_states_dict = {}
    for i, cell_genes in enumerate(gene_states_list):
        gene_states_dict[i] = cell_genes
    
    # Convert metadata to strings
    meta_str = []
    for key, value in metadata.items():
        if isinstance(value, str):
            meta_str.append(f'{key}="{value}"')
        else:
            meta_str.append(f'{key}={value}')
    
    # Create gene list string
    genes_str = ','.join(gene_nodes)
    
    # Create phenotypes string
    phenotypes_str = ','.join(phenotypes)
    
    # Create description line
    description_line = f"| {' | '.join(meta_str)} | genes={genes_str} | phenotypes={phenotypes_str}"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        # VTK header
        f.write("# vtk DataFile Version 3.0\n")
        f.write(f"{description_line}\n")
        f.write("ASCII\n")
        f.write("DATASET UNSTRUCTURED_GRID\n\n")
        
        # Points (8 vertices per cube)
        num_cells = len(positions)
        num_points = num_cells * 8
        f.write(f"POINTS {num_points} float\n")
        
        for x, y, z in positions:
            # Write 8 vertices of cube centered at (x, y, z)
            f.write(f"{x-0.5} {y-0.5} {z-0.5}\n")  # 0: front-bottom-left
            f.write(f"{x+0.5} {y-0.5} {z-0.5}\n")  # 1: front-bottom-right
            f.write(f"{x+0.5} {y+0.5} {z-0.5}\n")  # 2: front-top-right
            f.write(f"{x-0.5} {y+0.5} {z-0.5}\n")  # 3: front-top-left
            f.write(f"{x-0.5} {y-0.5} {z+0.5}\n")  # 4: back-bottom-left
            f.write(f"{x+0.5} {y-0.5} {z+0.5}\n")  # 5: back-bottom-right
            f.write(f"{x+0.5} {y+0.5} {z+0.5}\n")  # 6: back-top-right
            f.write(f"{x-0.5} {y+0.5} {z+0.5}\n")  # 7: back-top-left
        
        # Cells (hexahedrons)
        f.write(f"\nCELLS {num_cells} {num_cells * 9}\n")
        for i in range(num_cells):
            base = i * 8
            f.write(f"8 {base} {base+1} {base+2} {base+3} {base+4} {base+5} {base+6} {base+7}\n")
        
        # Cell types (12 = VTK_HEXAHEDRON)
        f.write(f"\nCELL_TYPES {num_cells}\n")
        for _ in range(num_cells):
            f.write("12\n")
        
        # Cell data (gene states)
        f.write(f"\nCELL_DATA {num_cells}\n")
        
        # Write gene states as scalars
        for gene_name in gene_nodes:
            f.write(f"\nSCALARS {gene_name} int 1\n")
            f.write("LOOKUP_TABLE default\n")
            for i in range(num_cells):
                cell_genes = gene_states_dict.get(i, {})
                state = 1 if cell_genes.get(gene_name, False) else 0
                f.write(f"{state}\n")


def convert_csv_to_vtk_3d(csv_file, vtk_file, z_position=50):
    """
    Convert 2D CSV checkpoint to 3D VTK checkpoint.
    
    Args:
        csv_file: Path to input CSV file (2D format)
        vtk_file: Path to output VTK file (3D format)
        z_position: Z-coordinate to place all cells at (default: 50, center of 100um domain)
    """
    print(f"[CONVERT] Reading CSV file: {csv_file}")
    
    positions = []
    phenotypes = []
    gene_states_list = []
    gene_nodes = set()
    metadata = {}
    
    # Read CSV file
    with open(csv_file, 'r') as f:
        # Read first line for metadata
        first_line = f.readline().strip()
        if first_line.startswith('#'):
            # Parse metadata: # cell_size_um=20.0, domain_size_um=1500.0, description="..."
            parts = first_line[1:].split(',')
            for part in parts:
                part = part.strip()
                if '=' in part:
                    key, value = part.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    
                    # Convert numeric values
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass  # Keep as string
                    
                    metadata[key] = value
        else:
            # No metadata line, rewind
            f.seek(0)
        
        # Read CSV data
        reader = csv.DictReader(f)
        
        for row in reader:
            # Position (convert to 3D)
            x = int(row['x'])
            y = int(row['y'])
            z = z_position
            positions.append((x, y, z))
            
            # Phenotype
            phenotype = row.get('phenotype', 'Quiescent')
            phenotypes.append(phenotype)
            
            # Gene states
            cell_gene_states = {}
            for key, value in row.items():
                if key.startswith('gene_'):
                    gene_name = key[5:]  # Remove 'gene_' prefix
                    gene_nodes.add(gene_name)
                    cell_gene_states[gene_name] = (value.lower() == 'true')
            
            gene_states_list.append(cell_gene_states)
    
    print(f"[CONVERT] Loaded {len(positions)} cells from CSV")
    print(f"[CONVERT] Gene nodes: {sorted(gene_nodes)}")
    
    # Prepare VTK metadata
    cell_size_um = metadata.get('cell_size_um', 20.0)
    vtk_metadata = {
        'biocell_grid_size_um': float(cell_size_um),
        'dimensions': 3,
        'description': metadata.get('description', 'Converted from 2D CSV'),
        'original_domain_size_um': metadata.get('domain_size_um', 1500.0),
        'z_position': z_position
    }
    
    # Metabolism (placeholder)
    metabolism_list = [0] * len(positions)
    
    # Save as VTK
    print(f"[CONVERT] Saving VTK file: {vtk_file}")
    write_vtk_domain(
        file_path=str(vtk_file),
        positions=positions,
        gene_states_list=gene_states_list,
        phenotypes=phenotypes,
        metabolism=metabolism_list,
        gene_nodes=sorted(gene_nodes),
        metadata=vtk_metadata
    )
    
    print(f"[CONVERT] Successfully converted to 3D VTK format")
    print(f"[CONVERT] All cells placed at z={z_position}")


if __name__ == "__main__":
    # Convert the 1000-cell checkpoint
    csv_file = Path(__file__).parent / "initial_cells_1000_center_1500.csv"
    vtk_file = Path(__file__).parent / "checkpoint_1000_cells_3d.vtk"
    
    convert_csv_to_vtk_3d(csv_file, vtk_file, z_position=50)
    print(f"\n[DONE] Created: {vtk_file}")
    print(f"[INFO] This file can be loaded in 3D simulations with read_checkpoint")
