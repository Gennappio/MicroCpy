#!/usr/bin/env python3
"""
H5 File Generator for MicroC
Generate custom H5 cell state files with configurable parameters
"""

import argparse
import h5py
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
import uuid
from datetime import datetime

# VTK export functionality is imported locally when needed

class H5Generator:
    def __init__(self, cell_size: float, cell_number: int, sparseness: float, 
                 sphere_radius: float, radial_sparseness: float, gene_probs_file: str):
        """
        Initialize H5 generator

        Args:
            cell_size: Size of each cell in micrometers
            cell_number: Total number of cells to generate
            sparseness: Radial distribution (0=center concentrated, 0.5=random, 1=border concentrated)
            sphere_radius: Radius of enclosing sphere in micrometers
            radial_sparseness: [DEPRECATED - use sparseness instead]
            gene_probs_file: Path to gene activation probabilities file
        """
        self.cell_size = cell_size
        self.cell_number = cell_number
        self.sparseness = sparseness
        self.sphere_radius = sphere_radius
        self.radial_sparseness = radial_sparseness
        self.gene_probs_file = gene_probs_file
        
        # Load gene activation probabilities
        self.gene_probs = self._load_gene_probabilities()
        
        # Define gene network nodes (from MicroC)
        self.gene_nodes = [
            'Oxygen_supply', 'Glucose_supply', 'MCT1_stimulus', 'Proton_level',
            'FGFR_stimulus', 'EGFR_stimulus', 'Glycolysis', 'OXPHOS', 'ATP',
            'Proliferation', 'Apoptosis', 'Growth_Arrest'
        ]
        
        print(f"[*] H5 Generator initialized:")
        print(f"    Cell size: {cell_size} um")
        print(f"    Cell number: {cell_number}")
        print(f"    Sparseness: {sparseness}")
        print(f"    Sphere radius: {sphere_radius} um")
        print(f"    Radial sparseness: {radial_sparseness}")
        print(f"    Gene probabilities: {len(self.gene_probs)} nodes")
    
    def _load_gene_probabilities(self) -> Dict[str, float]:
        """Load gene activation probabilities from text file"""
        probs = {}
        try:
            with open(self.gene_probs_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            gene_name = parts[0]
                            prob = float(parts[1])
                            probs[gene_name] = max(0.0, min(1.0, prob))  # Clamp to [0,1]
            print(f"[+] Loaded {len(probs)} gene probabilities from {self.gene_probs_file}")
        except Exception as e:
            print(f"[!] Error loading gene probabilities: {e}")
            print(f"[*] Using default probabilities (0.5 for all genes)")
            # Default probabilities
            default_genes = [
                'Oxygen_supply', 'Glucose_supply', 'MCT1_stimulus', 'Proton_level',
                'FGFR_stimulus', 'EGFR_stimulus', 'Glycolysis', 'OXPHOS', 'ATP',
                'Proliferation', 'Apoptosis', 'Growth_Arrest'
            ]
            probs = {gene: 0.5 for gene in default_genes}
        
        return probs
    
    def _generate_spherical_positions(self) -> np.ndarray:
        """Generate cell positions within a sphere with specified radial distribution"""
        positions = []

        # Generate exactly the requested number of cells
        max_attempts = self.cell_number * 20  # Prevent infinite loops
        attempts = 0

        while len(positions) < self.cell_number and attempts < max_attempts:
            attempts += 1

            # Generate random point in sphere
            # Use rejection sampling for uniform distribution in sphere
            while True:
                x = np.random.uniform(-1, 1)
                y = np.random.uniform(-1, 1)
                z = np.random.uniform(-1, 1)

                if x*x + y*y + z*z <= 1.0:
                    break

            # Apply sparseness to control radial distribution
            r = np.sqrt(x*x + y*y + z*z)

            if self.sparseness < 0.5:
                # sparseness 0-0.5: Concentrate toward center
                # 0 = maximum concentration at center
                # 0.5 = uniform distribution
                concentration_factor = 1.0 - 2.0 * self.sparseness  # 1.0 to 0.0
                r = r ** (1.0 + concentration_factor * 3.0)  # Higher power = more center concentration

            elif self.sparseness > 0.5:
                # sparseness 0.5-1.0: Concentrate toward border
                # 0.5 = uniform distribution
                # 1.0 = maximum concentration at border
                concentration_factor = 2.0 * (self.sparseness - 0.5)  # 0.0 to 1.0
                r = r ** (1.0 - concentration_factor * 0.8)  # Lower power = more border concentration

            # If sparseness == 0.5, r remains unchanged (uniform distribution)

            # Normalize direction and apply new radius
            if r > 0:
                norm = np.sqrt(x*x + y*y + z*z)
                x = (x / norm) * r
                y = (y / norm) * r
                z = (z / norm) * r

            # Scale to sphere radius and convert to biological grid coordinates
            scale = self.sphere_radius / self.cell_size
            x_bio = int(x * scale)
            y_bio = int(y * scale)
            z_bio = int(z * scale)

            # Check for duplicates before adding
            position = [x_bio, y_bio, z_bio]
            if position not in positions:
                positions.append(position)

        # Convert to numpy array
        positions = np.array(positions)

        # Calculate average distance from center for reporting
        if len(positions) > 0:
            distances = np.sqrt(np.sum(positions**2, axis=1))
            avg_distance = np.mean(distances)
            max_distance = self.sphere_radius / self.cell_size
            relative_distance = avg_distance / max_distance

            print(f"[+] Generated {len(positions)} unique cell positions")
            print(f"    Radial distribution: sparseness={self.sparseness:.1f}, avg_distance={relative_distance:.2f} (0=center, 1=border)")

        return positions
    
    def _generate_gene_states(self) -> Dict[str, np.ndarray]:
        """Generate gene states based on probabilities"""
        gene_states = {}
        
        for gene in self.gene_nodes:
            prob = self.gene_probs.get(gene, 0.5)
            states = np.random.random(self.cell_number) < prob
            gene_states[gene] = states.astype(bool)
            
            active_count = np.sum(states)
            print(f"    {gene}: {active_count}/{self.cell_number} active ({prob:.2f} prob)")
        
        return gene_states
    
    def _determine_phenotypes(self, gene_states: Dict[str, np.ndarray]) -> List[str]:
        """Determine cell phenotypes based on gene states"""
        phenotypes = []
        
        proliferation = gene_states.get('Proliferation', np.zeros(self.cell_number, dtype=bool))
        apoptosis = gene_states.get('Apoptosis', np.zeros(self.cell_number, dtype=bool))
        growth_arrest = gene_states.get('Growth_Arrest', np.zeros(self.cell_number, dtype=bool))
        
        for i in range(self.cell_number):
            if apoptosis[i]:
                phenotypes.append('Apoptosis')
            elif growth_arrest[i]:
                phenotypes.append('Growth_Arrest')
            elif proliferation[i]:
                phenotypes.append('Proliferation')
            else:
                phenotypes.append('Quiescent')
        
        # Count phenotypes
        from collections import Counter
        pheno_counts = Counter(phenotypes)
        print(f"[+] Phenotype distribution:")
        for pheno, count in pheno_counts.items():
            print(f"    {pheno}: {count} cells")
        
        return phenotypes
    
    def generate_h5_files(self, output_prefix: str = "generated_cells"):
        """Generate the H5 files (cell states and gene states)"""

        print(f"\n[*] Generating H5 files...")

        # Create output directory
        output_dir = Path("tools/generated_h5")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate cell positions
        positions = self._generate_spherical_positions()
        actual_cell_count = len(positions)

        # Update cell number to actual generated count
        self.cell_number = actual_cell_count

        # Generate gene states
        gene_states = self._generate_gene_states()

        # Determine phenotypes
        phenotypes = self._determine_phenotypes(gene_states)

        # Generate cell metadata
        cell_ids = [f"cell_{i:06d}" for i in range(actual_cell_count)]
        ages = np.random.exponential(24.0, actual_cell_count)  # Hours
        division_counts = np.random.poisson(2, actual_cell_count)
        tq_wait_times = np.random.exponential(12.0, actual_cell_count)  # Hours

        # Generate output filenames (no timestamp in filename)
        cell_states_file = output_dir / f"{output_prefix}.h5"
        gene_states_file = output_dir / f"{output_prefix}_gene_states.h5"
        
        # Create cell states H5 file
        self._create_cell_states_h5(
            cell_states_file, cell_ids, positions, phenotypes, 
            ages, division_counts, tq_wait_times, gene_states
        )
        
        # Create gene states H5 file
        self._create_gene_states_h5(gene_states_file, cell_ids, gene_states)

        # Export VTK cubic cells using shared module
        from vtk_export import export_h5_initial_conditions
        vtk_file = export_h5_initial_conditions(positions, self.cell_size, output_prefix)

        print(f"\n[+] Generated files in {output_dir}:")
        print(f"    Cell states: {cell_states_file.name}")
        print(f"    Gene states: {gene_states_file.name}")
        print(f"    VTK cells: {Path(vtk_file).name}")

        return str(cell_states_file), str(gene_states_file)

    def _create_cell_states_h5(self, filename: str, cell_ids: List[str], positions: np.ndarray,
                              phenotypes: List[str], ages: np.ndarray, division_counts: np.ndarray,
                              tq_wait_times: np.ndarray, gene_states: Dict[str, np.ndarray]):
        """Create cell states H5 file (same format as MicroC)"""

        with h5py.File(filename, 'w') as f:
            # Create cells group
            cells_group = f.create_group('cells')

            # Store cell data
            cells_group.create_dataset('ids', data=[s.encode('utf-8') for s in cell_ids])
            cells_group.create_dataset('positions', data=positions)
            cells_group.create_dataset('phenotypes', data=[s.encode('utf-8') for s in phenotypes])
            cells_group.create_dataset('ages', data=ages)
            cells_group.create_dataset('division_counts', data=division_counts)
            cells_group.create_dataset('tq_wait_times', data=tq_wait_times)

            # Create gene_states group (format expected by visualizer)
            gene_group = f.create_group('gene_states')

            # Create gene_names dataset
            gene_names = list(gene_states.keys())
            gene_group.create_dataset('gene_names', data=[s.encode('utf-8') for s in gene_names])

            # Create states matrix (N cells x M genes)
            states_matrix = np.column_stack([gene_states[gene] for gene in gene_names])
            gene_group.create_dataset('states', data=states_matrix)

            # Create metadata group (expected by visualizer)
            meta_group = f.create_group('metadata')
            meta_group.attrs['timestamp'] = datetime.now().isoformat()
            meta_group.attrs['version'] = "H5Generator-1.0"
            meta_group.attrs['cell_count'] = len(cell_ids)
            meta_group.attrs['step'] = 0  # Initial state
            meta_group.attrs['generator_version'] = '1.0'
            meta_group.attrs['cell_size_um'] = self.cell_size
            meta_group.attrs['sphere_radius_um'] = self.sphere_radius
            meta_group.attrs['sparseness'] = self.sparseness
            meta_group.attrs['radial_sparseness'] = self.radial_sparseness

        print(f"[+] Created cell states H5: {filename}")

    def _create_gene_states_h5(self, filename: str, cell_ids: List[str],
                              gene_states: Dict[str, np.ndarray]):
        """Create gene states H5 file (same format as MicroC)"""

        with h5py.File(filename, 'w') as f:
            # Create main group
            main_group = f.create_group('gene_states')

            # Store gene states for each cell
            for i, cell_id in enumerate(cell_ids):
                cell_group = main_group.create_group(cell_id)

                for gene_name, states in gene_states.items():
                    cell_group.create_dataset(gene_name, data=bool(states[i]))

            # Add metadata
            f.attrs['creation_time'] = datetime.now().isoformat()
            f.attrs['cell_count'] = len(cell_ids)
            f.attrs['gene_count'] = len(gene_states)
            f.attrs['generator_version'] = '1.0'

        print(f"[+] Created gene states H5: {filename}")




def create_example_gene_probs_file(filename: str = "example_gene_probs.txt"):
    """Create an example gene probabilities file"""

    example_content = """# Gene Network Node Activation Probabilities
# Format: gene_name probability
# Probability should be between 0.0 and 1.0

# Supply nodes (usually high activation)
Oxygen_supply 0.8
Glucose_supply 0.9
MCT1_stimulus 0.6
Proton_level 0.4
FGFR_stimulus 0.3
EGFR_stimulus 0.2

# Metabolic nodes
Glycolysis 0.7
OXPHOS 0.5
ATP 0.8

# Fate nodes (usually lower activation)
Proliferation 0.3
Apoptosis 0.1
Growth_Arrest 0.2
"""

    with open(filename, 'w') as f:
        f.write(example_content)

    print(f"[+] Created example gene probabilities file: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate custom H5 cell state files for MicroC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 1000 cells in 50um sphere with balanced distribution
  python h5_generator.py --cells 1000 --radius 50 --gene-probs gene_probs.txt

  # Generate cells concentrated at sphere border
  python h5_generator.py --cells 500 --radius 30 --sparseness 0.9

  # Generate cells concentrated at center
  python h5_generator.py --cells 2000 --radius 40 --sparseness 0.1

  # Generate cells randomly distributed throughout sphere
  python h5_generator.py --cells 1000 --radius 35 --sparseness 0.5

  # Create example gene probabilities file
  python h5_generator.py --create-example
        """
    )

    parser.add_argument('--cells', type=int, default=1000,
                       help='Number of cells to generate (default: 1000)')
    parser.add_argument('--cell-size', '--size', type=float, default=20.0,
                       help='Size of each cell cube in micrometers (default: 20.0)')
    parser.add_argument('--radius', type=float, default=200.0,
                       help='Radius of sphere containing all cells in micrometers (default: 200.0)')
    parser.add_argument('--sparseness', type=float, default=0.5,
                       help='Radial distribution: 0=center concentrated, 0.5=random, 1=border concentrated (default: 0.5)')
    parser.add_argument('--radial', type=float, default=0.5,
                       help='[DEPRECATED] Use --sparseness instead (default: 0.5)')
    parser.add_argument('--gene-probs', default='gene_probs.txt',
                       help='Gene activation probabilities file (default: gene_probs.txt)')
    parser.add_argument('--output', default='generated_cells',
                       help='Output file prefix (default: generated_cells)')

    # Add examples to help
    parser.epilog = """
Examples:
  # Generate 100 cells in 400um radius sphere with 20um cell cubes:
  python run_microc.py --generate --cells 100 --radius 400 --cell-size 20 --output tumor_core

  # Generate dense core (center concentrated):
  python run_microc.py --generate --cells 200 --radius 300 --sparseness 0.1 --cell-size 15 --output dense_core

  # Generate sparse border (border concentrated):
  python run_microc.py --generate --cells 150 --radius 250 --sparseness 0.9 --cell-size 25 --output sparse_border
"""
    parser.add_argument('--create-example', action='store_true',
                       help='Create example gene probabilities file and exit')

    args = parser.parse_args()

    if args.create_example:
        create_example_gene_probs_file()
        return

    # Validate parameters
    if not (0.0 <= args.sparseness <= 1.0):
        print("[!] Error: sparseness must be between 0.0 and 1.0")
        return

    if not (0.0 <= args.radial <= 1.0):
        print("[!] Error: radial sparseness must be between 0.0 and 1.0")
        return

    if args.cells <= 0:
        print("[!] Error: number of cells must be positive")
        return

    if args.radius <= 0:
        print("[!] Error: sphere radius must be positive")
        return

    # Check if gene probabilities file exists
    if not Path(args.gene_probs).exists():
        print(f"[!] Gene probabilities file not found: {args.gene_probs}")
        print(f"[*] Create one with: python h5_generator.py --create-example")
        return

    # Create generator and generate files
    generator = H5Generator(
        cell_size=args.cell_size,
        cell_number=args.cells,
        sparseness=args.sparseness,
        sphere_radius=args.radius,
        radial_sparseness=args.radial,
        gene_probs_file=args.gene_probs
    )

    cell_file, gene_file = generator.generate_h5_files(args.output)

    print(f"\n[SUCCESS] H5 files generated successfully!")
    print(f"Use with: python run_microc.py --visualize {cell_file}")


if __name__ == "__main__":
    main()
