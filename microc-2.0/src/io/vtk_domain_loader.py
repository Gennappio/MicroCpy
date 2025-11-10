#!/usr/bin/env python3
"""
VTK Domain Loader for MicroC 2.0 (library module)

This module provides VTKDomainLoader for reading enhanced VTK domain files
that embed positions, gene states, phenotypes, metabolism, and metadata.

It is extracted from tools/vtk_export.py to avoid dynamic sys.path imports and
keep reusable loader functionality under src/ for clean package imports.
"""
from pathlib import Path
from typing import Dict, List
import numpy as np

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
            Dict containing positions, gene_states, phenotypes, metabolism, metadata
        """
        print(f"[VTK] Loading complete domain from {vtk_path}")

        with open(vtk_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Parse metadata from description line
        metadata: Dict = {}
        gene_nodes: List[str] = []
        phenotype_types: List[str] = []

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
        positions: List[List[float]] = []
        points_section = False
        cell_data_section = False
        current_scalar = None
        scalar_data: Dict[str, List[int]] = {}

        for line in lines:
            line = line.strip()

            if line.startswith("POINTS"):
                points_section = True
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
                coords = list(map(float, line.split()))
                if len(coords) == 3:
                    positions.append(coords)
            elif cell_data_section and current_scalar and line and not line.startswith("#") and not line.startswith("SCALARS"):
                try:
                    value = int(line)
                    scalar_data[current_scalar].append(value)
                except ValueError:
                    pass

        # Convert point coordinates to cell centers (every 8 points = 1 cell)
        cell_positions: List[List[float]] = []
        original_physical_positions: List[List[float]] = []  # meters
        cell_size_m = metadata.get('biocell_grid_size_um', 20.0) * 1e-6

        for i in range(0, len(positions), 8):
            if i + 7 < len(positions):
                cube_points = positions[i:i+8]
                center_x = sum(p[0] for p in cube_points) / 8
                center_y = sum(p[1] for p in cube_points) / 8
                center_z = sum(p[2] for p in cube_points) / 8

                original_physical_positions.append([center_x, center_y, center_z])

                # Convert back to biological grid coordinates (preserve centering around 0,0,0)
                bio_x = center_x / cell_size_m
                bio_y = center_y / cell_size_m
                bio_z = center_z / cell_size_m

                cell_positions.append([bio_x, bio_y, bio_z])

        # Parse gene states, phenotypes, and metabolism
        gene_states: Dict[int, Dict[str, bool]] = {}
        phenotypes: List[str] = []
        metabolism: List[int] = []

        # Get phenotype mapping
        phenotype_values = scalar_data.get('Phenotype', [])
        phenotype_map = {i: p for i, p in enumerate(phenotype_types)}

        # Get metabolism values
        metabolism_values = scalar_data.get('Metabolism', [])

        for i in range(len(cell_positions)):
            # Gene states for this cell
            cell_genes: Dict[str, bool] = {}
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

            # Metabolism for this cell
            if i < len(metabolism_values):
                metabolism.append(metabolism_values[i])
            else:
                metabolism.append(0)

        result = {
            'positions': np.array(cell_positions),
            'original_physical_positions': np.array(original_physical_positions),
            'gene_states': gene_states,
            'phenotypes': phenotypes,
            'metabolism': metabolism,
            'metadata': metadata,
            'gene_nodes': gene_nodes,
            'phenotype_types': phenotype_types
        }

        print(f"[+] Loaded domain: {len(cell_positions)} cells")
        print(f"    Cell size: {metadata.get('biocell_grid_size_um', 'unknown')} um")
        print(f"    Gene nodes: {len(gene_nodes)}")
        print(f"    Phenotypes: {len(set(phenotypes))} types")

        return result

