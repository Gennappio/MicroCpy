#!/usr/bin/env python3
"""
CSV Cell Generator for 2D OpenCellComms Simulations

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


def _symmetric_ball(cell_count: int, centre: Tuple[float, ...]) -> List[Tuple[int, ...]]:
    """Lattice points packed as tightly as possible around ``centre`` whose
    centre of mass is EXACTLY ``centre`` (2D or 3D).

    ``centre`` components are all integers (the centre is a cell centre: the
    ODD-grid case) or all half-integers (the centre is a cell corner: the
    EVEN-grid case). The set is built from antipodal pairs (p, 2c - p), which
    keep the centre of mass on c whatever the fill; within a partially used
    shell the pairs are spread evenly in angle so the rim stays round.

    Parity: on a cell centre the count is 1 (the centre cell) + 2 * pairs, so
    an EVEN count is completed with one zero-sum triple of rim points
    (p + q + r = 3c), the smallest such triple by radius; on a cell corner
    every point has a partner, so the count must be even (an odd count can
    never have its centre of mass on a corner).
    """
    import itertools
    c = tuple(float(v) for v in centre)
    dims = len(c)
    on_cell_centre = all(abs(v - round(v)) < 1e-9 for v in c)
    on_cell_corner = all(abs(abs(v - round(v)) - 0.5) < 1e-9 for v in c)
    if not (on_cell_centre or on_cell_corner):
        raise ValueError(f"centre {centre} must be all-integer (cell centre) or all-half-integer (cell corner)")
    if on_cell_corner and cell_count % 2:
        raise ValueError(f"{cell_count} cells cannot have their centre of mass on a cell corner "
                         f"(even grid): use an even count")
    if dims == 2:
        radius = int(np.ceil(np.sqrt(cell_count / np.pi))) + 3
    else:
        radius = int(np.ceil((3.0 * cell_count / (4.0 * np.pi)) ** (1.0 / 3.0))) + 3

    def r2(p):
        return sum((p[i] - c[i]) ** 2 for i in range(dims))

    def mirror(p):
        return tuple(int(round(2 * c[i] - p[i])) for i in range(dims))

    ranges = [range(int(np.floor(c[i] - radius)), int(np.ceil(c[i] + radius)) + 1) for i in range(dims)]
    points = [p for p in itertools.product(*ranges) if r2(p) <= radius * radius]

    selected: List[Tuple[int, ...]] = []
    if on_cell_centre:
        origin = tuple(int(round(v)) for v in c)
        selected.append(origin)
    need = cell_count - len(selected)
    triple_needed = need % 2 == 1
    pairs_needed = (need - 3) // 2 if triple_needed else need // 2

    # Antipodal pairs, grouped by shell (squared radius), each shell's pairs
    # sorted by the angle of their representative so a partial shell can be
    # filled with evenly spread pairs.
    def angle_key(p):
        d = [p[i] - c[i] for i in range(dims)]
        return (np.arctan2(d[1], d[0]),) + tuple(d[2:])

    pairs = {}
    for p in points:
        q = mirror(p)
        if q == p:
            continue  # the centre cell itself
        rep = max(p, q)
        pairs[rep] = (round(r2(p), 6), rep, q)
    shells: Dict[float, List[Tuple]] = {}
    for radius2, rep, q in pairs.values():
        shells.setdefault(radius2, []).append((rep, q))
    for radius2 in sorted(shells):
        if pairs_needed == 0:
            break
        shell = sorted(shells[radius2], key=lambda pq: angle_key(pq[0]))
        if len(shell) <= pairs_needed:
            chosen = shell
        else:
            chosen = [shell[int(j * len(shell) / pairs_needed)] for j in range(pairs_needed)]
        for rep, q in chosen:
            selected.extend([rep, q])
        pairs_needed -= len(chosen)
    if pairs_needed:
        raise RuntimeError("search radius too small for the requested count")

    if triple_needed:
        taken = set(selected)
        target = tuple(int(round(3 * v)) for v in c)
        remaining = sorted((p for p in points if p not in taken), key=lambda p: (round(r2(p), 6), p))
        best = None
        for window in (96, 192, 384, len(remaining)):
            pool = remaining[:window]
            pool_set = set(pool)
            for a, b in itertools.combinations(pool, 2):
                d = tuple(target[i] - a[i] - b[i] for i in range(dims))
                if d in pool_set and d > b:  # a < b < d: each triple once
                    score = (max(r2(a), r2(b), r2(d)), r2(a) + r2(b) + r2(d), a, b, d)
                    if best is None or score < best:
                        best = score
            if best is not None:
                break
        if best is None:
            raise RuntimeError("no zero-sum rim triple found")
        selected.extend(best[2:])

    assert len(selected) == cell_count
    total = [sum(p[i] for p in selected) for i in range(dims)]
    assert all(abs(total[i] - cell_count * c[i]) < 1e-9 for i in range(dims)), "centre of mass is off"
    return selected


def symmetry_centre(domain_size: int) -> float:
    """The exact domain centre in bio-grid units: a cell centre (integer) on an
    odd grid, a cell corner (half-integer) on an even grid."""
    return domain_size / 2.0 - 0.5 if domain_size % 2 == 0 else float(domain_size // 2)


def generate_spheroid_pattern(center_x: float, center_y: float, cell_count: int) -> List[Tuple[int, int]]:
    """Cells packed in a circle whose centre of mass is exactly (center_x, center_y)."""
    return [tuple(p) for p in _symmetric_ball(cell_count, (center_x, center_y))]


def generate_spheroid_pattern_3d(center_x: float, center_y: float, center_z: float,
                                 cell_count: int) -> List[Tuple[int, int, int]]:
    """Cells packed in a ball whose centre of mass is exactly the given centre."""
    return [tuple(p) for p in _symmetric_ball(cell_count, (center_x, center_y, center_z))]


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

    for i, pos in enumerate(positions):
        x, y = pos[0], pos[1]
        cell = {'x': x, 'y': y}
        if len(pos) > 2:
            cell['z'] = pos[2]
        cell['phenotype'] = 'Proliferation'  # Default phenotype

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
            center_x = np.mean([p[0] for p in positions])
            center_y = np.mean([p[1] for p in positions])
            distance_sq = (x - center_x) ** 2 + (y - center_y) ** 2
            if len(pos) > 2:
                center_z = np.mean([p[2] for p in positions])
                distance_sq += (pos[2] - center_z) ** 2
            distance = np.sqrt(distance_sq)

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


def recenter_positions(positions: List[Tuple[int, ...]], center: Tuple[int, ...]) -> List[Tuple[int, ...]]:
    """Rebase absolute grid positions onto the centre-relative seed convention.

    Seed files store coordinates measured from the domain centre, so the same
    file stays centred at any Cell Height (the loader shifts them onto the
    corner-origin biological grid).
    """
    return [tuple(p[i] - center[i] for i in range(len(p))) for p in positions]


def write_csv_file(cells: List[Dict[str, Any]], output_path: Path, cell_size_um: float = 20.0,
                   domain_size_um: float = 500.0, description: str = "Generated cell positions"):
    """Write cells to CSV file with metadata"""

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        # Write metadata comment
        f.write(f'# origin=center, cell_size_um={cell_size_um}, domain_size_um={domain_size_um}, description="{description}"\n')

        # Write CSV data
        if cells:
            fieldnames = list(cells[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cells)


def main():
    parser = argparse.ArgumentParser(description='Generate CSV files with cell positions for 2D OpenCellComms simulations')
    parser.add_argument('--output', '-o', type=str, required=True, help='Output CSV file path')
    parser.add_argument('--pattern', '-p', choices=['spheroid', 'grid', 'random'], default='spheroid',
                       help='Cell placement pattern')
    parser.add_argument('--count', '-c', type=int, default=25, help='Number of cells (for spheroid/random patterns)')
    parser.add_argument('--grid_size', '-g', type=str, default='5x5', help='Grid size (e.g., 5x5 for grid pattern)')
    parser.add_argument('--domain_size', '-d', type=int, default=25, help='Domain size in grid units')
    parser.add_argument('--cell_size_um', type=float, default=20.0, help='Cell size in micrometers')
    parser.add_argument('--domain_size_um', type=float, default=500.0, help='Domain size in micrometers')
    parser.add_argument('--center_x', type=float, help='Center X (grid units; integer = cell centre, half-integer = cell corner; default: the exact domain centre)')
    parser.add_argument('--center_y', type=float, help='Center Y (grid units; default: the exact domain centre)')
    parser.add_argument('--center_z', type=float, help='Center Z (3D only; default: the exact domain centre)')
    parser.add_argument('--dimensions', type=int, choices=[2, 3], default=2,
                       help='2 for a flat seed (x,y), 3 for a Euclidean-ball spheroid with a z column')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducible results')
    parser.add_argument('--genes', type=str, help='Path to .bnd file to read all gene network nodes')
    
    args = parser.parse_args()
    
    # Set random seed
    np.random.seed(args.seed)
    
    # Generate positions based on pattern
    if args.pattern == 'spheroid':
        # The exact domain centre: a cell centre on an odd grid, a cell corner
        # on an even one. The colony's centre of mass lands on it exactly.
        auto_centre = symmetry_centre(args.domain_size)
        center_x = args.center_x if args.center_x is not None else auto_centre
        center_y = args.center_y if args.center_y is not None else auto_centre
        if args.dimensions == 3:
            center_z = args.center_z if args.center_z is not None else auto_centre
            positions = generate_spheroid_pattern_3d(center_x, center_y, center_z, args.count)
            description = (f"3D spheroid pattern with {len(positions)} cells "
                           f"(centre of mass exactly at the domain centre)")
        else:
            positions = generate_spheroid_pattern(center_x, center_y, args.count)
            description = (f"Spheroid pattern with {len(positions)} cells "
                           f"(centre of mass exactly at the domain centre)")
        
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

    # Patterns are laid out on the absolute grid; seed files store coordinates
    # relative to the domain centre so they stay centred at any Cell Height.
    domain_center = args.domain_size // 2
    positions = recenter_positions(positions, (domain_center,) * len(positions[0]))

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
