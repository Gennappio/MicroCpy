#!/usr/bin/env python3
"""
Initial State Generator and Loader for MicroC 3D Simulations

Handles saving and loading of:
1. Cell positions (3D coordinates)
2. Gene network activation states for each cell

Uses HDF5 format for efficient storage of structured scientific data.
"""

import h5py
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional, Any
from dataclasses import dataclass
import uuid
import json
from datetime import datetime

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


class InitialStateManager:
    """
    Manages saving and loading of initial cell states for MicroC simulations.
    
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
        Save initial cell states to HDF5 file.
        
        Args:
            cells: Dictionary of cell_id -> Cell objects
            file_path: Path to save the HDF5 file
            step: Simulation step (for periodic saves)
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert cells to serializable format
        cell_data = []
        for cell_id, cell in cells.items():
            # Convert position to 3D if needed
            pos = cell.state.position
            if len(pos) == 2:
                pos_3d = (pos[0], pos[1], 0.0)  # Add z=0 for 2D simulations
            else:
                pos_3d = pos
                
            cell_data.append(CellStateData(
                id=cell.state.id,
                position=pos_3d,
                phenotype=cell.state.phenotype,
                age=cell.state.age,
                division_count=cell.state.division_count,
                gene_states=cell.state.gene_states.copy(),
                metabolic_state=cell.state.metabolic_state.copy(),
                tq_wait_time=cell.state.tq_wait_time
            ))
        
        print(f"💾 Saving {len(cell_data)} cell states to {file_path}")
        
        with h5py.File(file_path, 'w') as f:
            # Save metadata
            meta_group = f.create_group('metadata')
            meta_group.attrs['timestamp'] = datetime.now().isoformat()
            meta_group.attrs['version'] = "MicroC-2.0"
            meta_group.attrs['cell_count'] = len(cell_data)
            meta_group.attrs['step'] = step
            meta_group.attrs['config_hash'] = self._compute_config_hash()
            
            # Save domain info
            domain_info = {
                'dimensions': self.config.domain.dimensions,
                'size_x': self.config.domain.size_x.meters,
                'size_y': self.config.domain.size_y.meters,
                'size_z': self.config.domain.size_z.meters if self.config.domain.size_z else 0.0,
                'nx': self.config.domain.nx,
                'ny': self.config.domain.ny,
                'nz': self.config.domain.nz if self.config.domain.nz else 1,
                'cell_height': self.config.domain.cell_height.meters
            }
            meta_group.attrs['domain_info'] = json.dumps(domain_info)
            
            if not cell_data:
                print("⚠️  No cells to save")
                return
                
            # Save cell data
            cells_group = f.create_group('cells')
            
            # Basic cell properties
            cells_group.create_dataset('ids', data=[c.id.encode('utf-8') for c in cell_data])
            cells_group.create_dataset('positions', data=np.array([c.position for c in cell_data]))
            cells_group.create_dataset('phenotypes', data=[c.phenotype.encode('utf-8') for c in cell_data])
            cells_group.create_dataset('ages', data=[c.age for c in cell_data])
            cells_group.create_dataset('division_counts', data=[c.division_count for c in cell_data])
            cells_group.create_dataset('tq_wait_times', data=[c.tq_wait_time for c in cell_data])
            
            # Save gene states
            if cell_data and cell_data[0].gene_states:
                gene_group = f.create_group('gene_states')
                
                # Get all unique gene names
                all_genes = set()
                for cell in cell_data:
                    all_genes.update(cell.gene_states.keys())
                gene_names = sorted(list(all_genes))
                
                # Create gene states matrix (cells x genes)
                gene_matrix = np.zeros((len(cell_data), len(gene_names)), dtype=bool)
                for i, cell in enumerate(cell_data):
                    for j, gene_name in enumerate(gene_names):
                        gene_matrix[i, j] = cell.gene_states.get(gene_name, False)
                
                gene_group.create_dataset('gene_names', data=[g.encode('utf-8') for g in gene_names])
                gene_group.create_dataset('states', data=gene_matrix)
                
                print(f"✅ Saved gene states: {len(gene_names)} genes for {len(cell_data)} cells")
            
            # Save metabolic states
            if cell_data and cell_data[0].metabolic_state:
                metab_group = f.create_group('metabolic_states')
                
                # Get all unique metabolite names
                all_metabolites = set()
                for cell in cell_data:
                    all_metabolites.update(cell.metabolic_state.keys())
                metabolite_names = sorted(list(all_metabolites))
                
                # Create metabolic states matrix (cells x metabolites)
                metab_matrix = np.zeros((len(cell_data), len(metabolite_names)), dtype=float)
                for i, cell in enumerate(cell_data):
                    for j, metab_name in enumerate(metabolite_names):
                        metab_matrix[i, j] = cell.metabolic_state.get(metab_name, 0.0)
                
                metab_group.create_dataset('metabolite_names', data=[m.encode('utf-8') for m in metabolite_names])
                metab_group.create_dataset('values', data=metab_matrix)
                
                print(f"✅ Saved metabolic states: {len(metabolite_names)} metabolites for {len(cell_data)} cells")
        
        print(f"✅ Successfully saved initial state to {file_path}")
    
    def load_initial_state(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Load initial cell states from HDF5 file.
        
        Returns:
            List of cell initialization dictionaries compatible with CellPopulation.initialize_cells()
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Initial state file not found: {file_path}")
        
        print(f"📂 Loading initial state from {file_path}")
        
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
                
                print(f"✅ Loaded gene states: {len(gene_names)} genes")
            
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
                
                print(f"✅ Loaded metabolic states: {len(metabolite_names)} metabolites")
            
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
        
        print(f"✅ Successfully loaded {len(cell_init_data)} cells from {file_path}")
        return cell_init_data
    
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
        size_tolerance = 1e-6  # 1 μm tolerance
        if (abs(saved_domain_info['size_x'] - current_domain.size_x.meters) > size_tolerance or
            abs(saved_domain_info['size_y'] - current_domain.size_y.meters) > size_tolerance):
            print(f"⚠️  Domain size mismatch: saved ({saved_domain_info['size_x']:.6f}, {saved_domain_info['size_y']:.6f}) m, "
                  f"current ({current_domain.size_x.meters:.6f}, {current_domain.size_y.meters:.6f}) m")
        
        print("✅ Domain compatibility validated")


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
