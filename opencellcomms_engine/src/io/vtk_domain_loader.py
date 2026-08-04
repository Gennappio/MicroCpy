#!/usr/bin/env python3
"""
VTK Domain Loader for OpenCellComms (library module)

This module provides VTKDomainLoader for reading enhanced VTK domain files
that embed positions, gene states, phenotypes, metabolism, and metadata.

It is extracted from tools/vtk_export.py to avoid dynamic sys.path imports and
keep reusable loader functionality under src/ for clean package imports.
"""
from pathlib import Path
from typing import Any, Dict, List, Sequence
import numpy as np

class VTKDomainLoader:
    """Load complete domain description from enhanced VTK files"""

    def __init__(self):
        """Initialize VTK domain loader"""
        pass

    def save_complete_domain(
        self,
        file_path: str,
        positions: Sequence[Sequence[float]],
        gene_states: Sequence[Dict[str, bool]],
        phenotypes: Sequence[str],
        metabolism: Sequence[float],
        gene_nodes: Sequence[str],
        metadata: Dict[str, Any],
    ) -> None:
        """Write the enhanced legacy-VTK format consumed by this loader.

        Each biological cell is represented as one VTK hexahedron. Logical
        positions are converted to physical metres with the configured cell
        size, matching ``load_complete_domain``'s inverse conversion.
        """
        count = len(positions)
        if not (
            len(gene_states) == count
            and len(phenotypes) == count
            and len(metabolism) == count
        ):
            raise ValueError("positions, gene_states, phenotypes and metabolism must have equal lengths")

        size_um = float(metadata.get('biocell_grid_size_um', 20.0))
        if size_um <= 0:
            raise ValueError("biocell_grid_size_um must be greater than zero")
        size_m = size_um * 1e-6
        half = size_m / 2.0

        phenotype_types = list(dict.fromkeys(str(value) for value in phenotypes))
        phenotype_indexes = {name: index for index, name in enumerate(phenotype_types)}

        description = [
            f"cells={count}",
            f"size={size_um:g}um",
            f"genes={','.join(gene_nodes)}",
            f"phenotypes={','.join(phenotype_types)}",
        ]
        for key, value in metadata.items():
            if key in {'biocell_grid_size_um', 'cell_count'}:
                continue
            if isinstance(value, (list, tuple)):
                value = ','.join(str(item) for item in value)
            description.append(f"{key}={str(value).replace(' ', '_')}")

        lines = [
            "# vtk DataFile Version 3.0",
            "OpenCellComms complete domain | " + " ".join(description),
            "ASCII",
            "DATASET UNSTRUCTURED_GRID",
            f"POINTS {count * 8} float",
        ]

        offsets = (
            (-half, -half, -half),
            (half, -half, -half),
            (half, half, -half),
            (-half, half, -half),
            (-half, -half, half),
            (half, -half, half),
            (half, half, half),
            (-half, half, half),
        )
        for position in positions:
            coords = list(position)
            if len(coords) not in (2, 3):
                raise ValueError(f"Cell position must have 2 or 3 coordinates: {position!r}")
            x, y = float(coords[0]) * size_m, float(coords[1]) * size_m
            z = float(coords[2]) * size_m if len(coords) == 3 else 0.0
            lines.extend(
                f"{x + dx:.12g} {y + dy:.12g} {z + dz:.12g}"
                for dx, dy, dz in offsets
            )

        lines.append(f"CELLS {count} {count * 9}")
        for index in range(count):
            start = index * 8
            lines.append("8 " + " ".join(str(start + offset) for offset in range(8)))
        lines.append(f"CELL_TYPES {count}")
        lines.extend("12" for _ in range(count))  # VTK_HEXAHEDRON
        lines.append(f"CELL_DATA {count}")

        def add_scalar(name: str, values: Sequence[Any], vtk_type: str = "int") -> None:
            lines.extend((f"SCALARS {name} {vtk_type} 1", "LOOKUP_TABLE default"))
            lines.extend(str(value) for value in values)

        for gene_name in gene_nodes:
            add_scalar(
                gene_name,
                [int(bool(states.get(gene_name, False))) for states in gene_states],
            )
        add_scalar("Phenotype", [phenotype_indexes[str(value)] for value in phenotypes])
        add_scalar("Metabolism", metabolism, "float")

        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def load_complete_domain(self, vtk_path: str) -> Dict:
        """
        Load complete domain description from VTK file

        Args:
            vtk_path: Path to VTK domain file

        Returns:
            Dict containing positions, gene_states, phenotypes, metabolism, metadata
        """
        # print(f"[VTK] Loading complete domain from {vtk_path}")

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
                            elif key == "ages":
                                metadata['ages'] = [float(v) for v in value.split(',') if v]
                            elif key == "generations":
                                metadata['generations'] = [int(v) for v in value.split(',') if v]
                            elif key == "bounds":
                                metadata['domain_bounds_um'] = value
                            else:
                                metadata[key] = value

        # Parse cell positions from POINTS section
        positions: List[List[float]] = []
        points_section = False
        cell_data_section = False
        current_scalar = None
        scalar_data: Dict[str, List[float]] = {}

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
                    scalar_value = float(line)
                    scalar_data[current_scalar].append(scalar_value)
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
        metabolism: List[float] = []

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
                phenotype_idx = int(phenotype_values[i])
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

        result['ages'] = metadata.get('ages', [])
        result['generations'] = metadata.get('generations', [])

        # print(f"[+] Loaded domain: {len(cell_positions)} cells")
        # print(f"    Cell size: {metadata.get('biocell_grid_size_um', 'unknown')} um")
        # print(f"    Gene nodes: {len(gene_nodes)}")
        # print(f"    Phenotypes: {len(set(phenotypes))} types")

        return result
