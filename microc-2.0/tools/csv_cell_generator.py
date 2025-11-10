#!/usr/bin/env python3
"""
CSV Cell Generator for 2D MicroC Simulations

This tool generates CSV files with cell positions for 2D simulations.
CSV format is human-readable and easy to edit manually.

Usage:
    python csv_cell_generator.py --output cells.csv --pattern spheroid --count 50
    python csv_cell_generator.py --output cells.csv --pattern grid --grid_size 5x5
    python csv_cell_generator.py --output cells.csv --pattern random --count 30 --domain_size 25
"""

import argparse
import csv
import numpy as np
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any, Set


def parse_bnd_file(bnd_file_path: str) -> Set[str]:
    """Parse .bnd file and extract all node names"""
    node_names = set()

    try:
        with open(bnd_file_path, 'r') as f:
            content = f.read()

        # Find all node definitions using regex
        # Pattern: node NODE_NAME {
        node_pattern = r'node\s+(\w+)\s*\{'
        matches = re.finditer(node_pattern, content, re.MULTILINE)

        for match in matches:
            node_name = match.group(1)
            node_names.add(node_name)

        print(f"[+] Parsed {len(node_names)} nodes from {bnd_file_path}")
        return node_names

    except Exception as e:
        print(f"[!] Error parsing BND file {bnd_file_path}: {e}")
        return set()


def generate_spheroid_pattern(center_x: int, center_y: int, cell_count: int, max_radius: int = 10) -> List[Tuple[int, int]]:
    """Generate cells in a spheroid (circular) pattern"""
    positions = []
    radius = 1
    cells_placed = 0
    
    while cells_placed < cell_count and radius <= max_radius:
        for x in range(max(0, center_x - radius), center_x + radius + 1):
            for y in range(max(0, center_y - radius), center_y + radius + 1):
                if cells_placed >= cell_count:
                    break
                
                # Check if position is within circular distance
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                if distance <= radius:
                    positions.append((x, y))
                    cells_placed += 1
            if cells_placed >= cell_count:
                break
        radius += 1
    
    return positions[:cell_count]


def generate_grid_pattern(grid_width: int, grid_height: int, start_x: int = 0, start_y: int = 0) -> List[Tuple[int, int]]:
    """Generate cells in a regular grid pattern"""
    positions = []
    for x in range(start_x, start_x + grid_width):
        for y in range(start_y, start_y + grid_height):
            positions.append((x, y))
    return positions


def generate_random_pattern(cell_count: int, domain_size: int, seed: int = 42) -> List[Tuple[int, int]]:
    """Generate cells in random positions"""
    np.random.seed(seed)
    positions = []
    used_positions = set()
    
    attempts = 0
    while len(positions) < cell_count and attempts < cell_count * 10:
        x = np.random.randint(0, domain_size)
        y = np.random.randint(0, domain_size)
        
        if (x, y) not in used_positions:
            positions.append((x, y))
            used_positions.add((x, y))
        
        attempts += 1
    
    return positions


def assign_phenotypes_and_genes(positions: List[Tuple[int, int]], pattern: str, gene_nodes: Set[str] = None) -> List[Dict[str, Any]]:
    """Assign phenotypes and gene states to cells based on pattern"""
    cells = []

    # Use provided gene nodes or default set
    if gene_nodes is None:
        gene_nodes = {'mitoATP', 'glycoATP', 'Proliferation'}

    # Identify phenotype nodes (common output nodes)
    phenotype_nodes = {'Proliferation', 'Apoptosis', 'Growth_Arrest', 'Necrosis', 'Quiescent'}

    for i, (x, y) in enumerate(positions):
        cell = {
            'x': x,
            'y': y,
            'phenotype': 'Proliferation'  # Default phenotype
        }

        # Initialize all gene nodes randomly (true/false)
        for gene_node in sorted(gene_nodes):  # Sort for consistent ordering
            # Phenotype nodes start as false (will be set based on logic)
            if gene_node in phenotype_nodes:
                cell[f'gene_{gene_node}'] = 'false'
            else:
                # Random initialization for non-phenotype nodes
                cell[f'gene_{gene_node}'] = 'true' if np.random.random() > 0.5 else 'false'
        
        # Pattern-specific adjustments
        if pattern == 'spheroid':
            # Inner cells are proliferative, outer cells are quiescent
            center_x = np.mean([pos[0] for pos in positions])
            center_y = np.mean([pos[1] for pos in positions])
            distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)

            if distance <= 2:  # Core cells
                cell['phenotype'] = 'Proliferation'
                if 'gene_Proliferation' in cell:
                    cell['gene_Proliferation'] = 'true'
            else:  # Outer cells
                cell['phenotype'] = 'Growth_Arrest'
                if 'gene_Growth_Arrest' in cell:
                    cell['gene_Growth_Arrest'] = 'true'
                if 'gene_Proliferation' in cell:
                    cell['gene_Proliferation'] = 'false'

        elif pattern == 'grid':
            # All cells proliferative in grid pattern
            cell['phenotype'] = 'Proliferation'
            if 'gene_Proliferation' in cell:
                cell['gene_Proliferation'] = 'true'

        elif pattern == 'random':
            # Random phenotype assignment
            cell['phenotype'] = np.random.choice(['Proliferation', 'Growth_Arrest'], p=[0.7, 0.3])
            if 'gene_Proliferation' in cell:
                cell['gene_Proliferation'] = 'true' if cell['phenotype'] == 'Proliferation' else 'false'
            if 'gene_Growth_Arrest' in cell:
                cell['gene_Growth_Arrest'] = 'true' if cell['phenotype'] == 'Growth_Arrest' else 'false'
        
        cells.append(cell)
    
    return cells


def write_csv_file(cells: List[Dict[str, Any]], output_path: Path, cell_size_um: float = 20.0, 
                   domain_size_um: float = 500.0, description: str = "Generated cell positions"):
    """Write cells to CSV file with metadata"""
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        # Write metadata comment
        f.write(f'# cell_size_um={cell_size_um}, domain_size_um={domain_size_um}, description="{description}"\n')
        
        # Write CSV data
        if cells:
            fieldnames = list(cells[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cells)


def main():
    parser = argparse.ArgumentParser(description='Generate CSV files with cell positions for 2D MicroC simulations')
    parser.add_argument('--output', '-o', type=str, required=True, help='Output CSV file path')
    parser.add_argument('--pattern', '-p', choices=['spheroid', 'grid', 'random'], default='spheroid',
                       help='Cell placement pattern')
    parser.add_argument('--count', '-c', type=int, default=25, help='Number of cells (for spheroid/random patterns)')
    parser.add_argument('--grid_size', '-g', type=str, default='5x5', help='Grid size (e.g., 5x5 for grid pattern)')
    parser.add_argument('--domain_size', '-d', type=int, default=25, help='Domain size in grid units')
    parser.add_argument('--cell_size_um', type=float, default=20.0, help='Cell size in micrometers')
    parser.add_argument('--domain_size_um', type=float, default=500.0, help='Domain size in micrometers')
    parser.add_argument('--center_x', type=int, help='Center X coordinate (auto-calculated if not specified)')
    parser.add_argument('--center_y', type=int, help='Center Y coordinate (auto-calculated if not specified)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducible results')
    parser.add_argument('--genes', type=str, help='Path to .bnd file to read all gene network nodes')
    
    args = parser.parse_args()
    
    # Set random seed
    np.random.seed(args.seed)
    
    # Generate positions based on pattern
    if args.pattern == 'spheroid':
        center_x = args.center_x if args.center_x is not None else args.domain_size // 2
        center_y = args.center_y if args.center_y is not None else args.domain_size // 2
        positions = generate_spheroid_pattern(center_x, center_y, args.count, args.domain_size // 2)
        description = f"Spheroid pattern with {len(positions)} cells"
        
    elif args.pattern == 'grid':
        grid_parts = args.grid_size.split('x')
        if len(grid_parts) != 2:
            raise ValueError("Grid size must be in format 'WxH' (e.g., '5x5')")
        grid_width, grid_height = int(grid_parts[0]), int(grid_parts[1])
        
        start_x = (args.domain_size - grid_width) // 2
        start_y = (args.domain_size - grid_height) // 2
        positions = generate_grid_pattern(grid_width, grid_height, start_x, start_y)
        description = f"Grid pattern {args.grid_size} with {len(positions)} cells"
        
    elif args.pattern == 'random':
        positions = generate_random_pattern(args.count, args.domain_size, args.seed)
        description = f"Random pattern with {len(positions)} cells"
    
    # Parse gene nodes from BND file if provided
    gene_nodes = None
    if args.genes:
        gene_nodes = parse_bnd_file(args.genes)
        if not gene_nodes:
            print("[!] Warning: No genes found in BND file, using default gene set")

    # Assign phenotypes and gene states
    cells = assign_phenotypes_and_genes(positions, args.pattern, gene_nodes)

    # Write to CSV file
    output_path = Path(args.output)
    write_csv_file(cells, output_path, args.cell_size_um, args.domain_size_um, description)

    print(f"Generated {len(cells)} cells in {args.pattern} pattern")
    print(f"Saved to: {output_path}")
    print(f"Domain size: {args.domain_size} grid units ({args.domain_size_um} um)")
    print(f"Cell size: {args.cell_size_um} um")
    if args.genes:
        print(f"Gene network: {len(gene_nodes)} nodes from {args.genes}")

    # Show preview of first few cells
    print("\nPreview (first 5 cells):")
    for i, cell in enumerate(cells[:5]):
        # Show first few gene states for preview
        gene_preview = []
        for key, value in cell.items():
            if key.startswith('gene_') and len(gene_preview) < 3:
                gene_preview.append(f"{key.replace('gene_', '')}:{value}")
        gene_str = " ".join(gene_preview)
        if len([k for k in cell.keys() if k.startswith('gene_')]) > 3:
            gene_str += "..."
        print(f"  Cell {i+1}: ({cell['x']}, {cell['y']}) - {cell['phenotype']} - {gene_str}")


if __name__ == '__main__':
    main()
