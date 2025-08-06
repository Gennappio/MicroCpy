#!/usr/bin/env python3
"""
Cell State Visualizer for MicroC 2.0

This tool creates visualizations of cell state and initial state files.

Features:
- 2D/3D cell position plots
- Gene network heatmaps
- Phenotype distribution plots
- Temporal evolution analysis
- Interactive plots with plotly
- Static plots with matplotlib

Usage:
    python cell_state_visualizer.py <file_path> [options]
    python cell_state_visualizer.py --help
"""

import argparse
import h5py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import ListedColormap
import seaborn as sns
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import sys

# Try to import plotly for interactive plots
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("[WARN]  Plotly not available. Interactive plots disabled. Install with: pip install plotly")

class CellStateVisualizer:
    """Visualizer for MicroC cell state files"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.metadata = {}
        self.cell_data = {}
        self.gene_data = {}
        self.metabolic_data = {}
        
        self._load_file()
        
        # Set up plotting style
        plt.style.use('default')
        sns.set_palette("husl")
    
    def _load_file(self):
        """Load data from HDF5 file"""
        print(f"[*] Loading file: {self.file_path}")

        with h5py.File(self.file_path, 'r') as f:
            # Load metadata
            if 'metadata' in f:
                meta_group = f['metadata']
                for key in meta_group.attrs.keys():
                    value = meta_group.attrs[key]
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    self.metadata[key] = value

            # Load cell data
            if 'cells' in f:
                cells_group = f['cells']
                self.cell_data = {
                    'ids': [s.decode('utf-8') for s in cells_group['ids'][:]],
                    'positions': cells_group['positions'][:],
                    'phenotypes': [s.decode('utf-8') for s in cells_group['phenotypes'][:]],
                    'ages': cells_group['ages'][:],
                    'division_counts': cells_group['division_counts'][:],
                    'tq_wait_times': cells_group['tq_wait_times'][:]
                }

            # Load gene states
            if 'gene_states' in f:
                gene_group = f['gene_states']
                self.gene_data = {
                    'gene_names': [s.decode('utf-8') for s in gene_group['gene_names'][:]],
                    'states': gene_group['states'][:]
                }

            # Load metabolic states
            if 'metabolic_states' in f:
                metab_group = f['metabolic_states']
                self.metabolic_data = {
                    'metabolite_names': [s.decode('utf-8') for s in metab_group['metabolite_names'][:]],
                    'values': metab_group['values'][:]
                }

        print(f"[+] File loaded successfully")
    
    def plot_cell_positions_2d(self, save_path: str = None, show_phenotypes: bool = True):
        """Plot cell positions in 2D"""
        if not self.cell_data:
            print("[!] No cell data available")
            return

        positions = self.cell_data['positions']
        phenotypes = self.cell_data['phenotypes']

        # Convert biological grid coordinates to FiPy grid coordinates
        # Use the same logic as H5 reader: discrete positions with Z-slice filtering
        cell_height = 5e-6  # 5 um for 3D simulations (from config files)
        domain_size = 500e-6  # 500 um domain (from config files)
        nx = ny = nz = 25  # 25x25x25 grid (from config files)
        dx = dy = dz = domain_size / 25

        # Convert to discrete FiPy grid coordinates (same as H5 reader)
        all_coords = []
        z_coords = []

        for pos in positions:
            x_meters = pos[0] * cell_height
            y_meters = pos[1] * cell_height
            z_meters = pos[2] * cell_height if len(pos) > 2 else 0

            x = int(x_meters / dx)
            y = int(y_meters / dy)
            z = int(z_meters / dz)

            all_coords.append([x, y, z])
            z_coords.append(z)

        all_coords = np.array(all_coords)
        z_coords = np.array(z_coords)

        # Find the Z slice with most cells (same logic as H5 reader)
        unique_z, counts = np.unique(z_coords, return_counts=True)
        middle_z = unique_z[np.argmax(counts)]

        # Filter cells in the displayed slice (±1 for visibility, same as H5 reader)
        slice_mask = np.abs(z_coords - middle_z) <= 1
        positions_fipy = all_coords[slice_mask][:, :2]  # Only X,Y coordinates

        # Filter other data arrays to match
        if len(phenotypes) == len(positions):
            phenotypes = [phenotypes[i] for i in range(len(phenotypes)) if slice_mask[i]]

        fig, ax = plt.subplots(figsize=(12, 10))

        if show_phenotypes:
            # Color by phenotype
            unique_phenotypes = list(set(phenotypes))
            colors = plt.cm.Set3(np.linspace(0, 1, len(unique_phenotypes)))
            phenotype_colors = {phenotype: colors[i] for i, phenotype in enumerate(unique_phenotypes)}

            for phenotype in unique_phenotypes:
                mask = np.array(phenotypes) == phenotype
                pos_subset = positions_fipy[mask]
                ax.scatter(pos_subset[:, 0], pos_subset[:, 1],
                          c=[phenotype_colors[phenotype]],
                          label=f'{phenotype} ({np.sum(mask)})',
                          alpha=0.7, s=20)

            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        else:
            # Color by age
            ages = self.cell_data['ages']
            scatter = ax.scatter(positions_fipy[:, 0], positions_fipy[:, 1],
                               c=ages, cmap='viridis', alpha=0.7, s=20)
            plt.colorbar(scatter, label='Cell Age')

        ax.set_xlabel('X Grid Index')
        ax.set_ylabel('Y Grid Index')
        ax.set_title(f'Cell Positions - {self.file_path.name} (Z slice {middle_z}±1)\n'
                    f'Showing {len(positions_fipy)} of {len(positions)} cells, Step {self.metadata.get("step", "unknown")}')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[+] Saved plot: {save_path}")
        else:
            plt.show()
    
    def plot_cell_positions_3d(self, save_path: str = None, show_phenotypes: bool = True):
        """Plot cell positions in 3D"""
        if not self.cell_data:
            print("[!] No cell data available")
            return

        positions = self.cell_data['positions']
        if positions.shape[1] < 3:
            print("[!] Not 3D data")
            return

        phenotypes = self.cell_data['phenotypes']

        # Convert biological grid coordinates to FiPy grid coordinates
        # Show actual continuous positions within the FiPy grid (not discrete grid centers)
        cell_height = 5e-6  # 5 um for 3D simulations (from config files)
        domain_size = 500e-6  # 500 um domain (from config files)
        grid_size = 25  # 25x25x25 grid (from config files)
        dx = domain_size / grid_size

        # Two-step conversion: biological grid → physical → FiPy continuous coordinates
        positions_physical = positions * cell_height  # Convert to meters
        positions_fipy = positions_physical / dx  # Convert to FiPy grid coordinates (continuous)

        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        if show_phenotypes:
            # Color by phenotype
            unique_phenotypes = list(set(phenotypes))
            colors = plt.cm.Set3(np.linspace(0, 1, len(unique_phenotypes)))
            phenotype_colors = {phenotype: colors[i] for i, phenotype in enumerate(unique_phenotypes)}

            for phenotype in unique_phenotypes:
                mask = np.array(phenotypes) == phenotype
                pos_subset = positions_fipy[mask]
                ax.scatter(pos_subset[:, 0], pos_subset[:, 1], pos_subset[:, 2],
                          c=[phenotype_colors[phenotype]],
                          label=f'{phenotype} ({np.sum(mask)})',
                          alpha=0.7, s=20)

            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        else:
            # Color by age
            ages = self.cell_data['ages']
            scatter = ax.scatter(positions_fipy[:, 0], positions_fipy[:, 1], positions_fipy[:, 2],
                               c=ages, cmap='viridis', alpha=0.7, s=20)
            plt.colorbar(scatter, label='Cell Age')

        ax.set_xlabel('X Grid Coordinate')
        ax.set_ylabel('Y Grid Coordinate')
        ax.set_zlabel('Z Grid Coordinate')
        ax.set_title(f'3D Cell Positions - {self.file_path.name}\n'
                    f'{len(positions)} cells, Step {self.metadata.get("step", "unknown")}')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[SAVE] Saved plot: {save_path}")
        else:
            plt.show()
    
    def plot_gene_heatmap(self, save_path: str = None, max_genes: int = 50, max_cells: int = 100):
        """Plot gene activation heatmap"""
        if not self.gene_data:
            print("[!] No gene data available")
            return
        
        gene_names = self.gene_data['gene_names']
        states_matrix = self.gene_data['states']
        
        # Limit size for readability
        n_cells = min(max_cells, states_matrix.shape[0])
        n_genes = min(max_genes, len(gene_names))
        
        # Select most variable genes
        gene_variance = np.var(states_matrix, axis=0)
        top_gene_indices = np.argsort(gene_variance)[-n_genes:]
        
        # Select random subset of cells
        cell_indices = np.random.choice(states_matrix.shape[0], n_cells, replace=False)
        
        # Create subset
        subset_matrix = states_matrix[np.ix_(cell_indices, top_gene_indices)]
        subset_gene_names = [gene_names[i] for i in top_gene_indices]
        
        # Plot heatmap
        fig, ax = plt.subplots(figsize=(max(8, n_genes * 0.3), max(6, n_cells * 0.1)))
        
        sns.heatmap(subset_matrix, 
                   xticklabels=subset_gene_names,
                   yticklabels=[f'Cell {i}' for i in cell_indices],
                   cmap='RdYlBu_r',
                   cbar_kws={'label': 'Gene Active'},
                   ax=ax)
        
        ax.set_title(f'Gene Activation Heatmap - {self.file_path.name}\n'
                    f'Top {n_genes} most variable genes, {n_cells} random cells')
        ax.set_xlabel('Genes')
        ax.set_ylabel('Cells')
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[SAVE] Saved plot: {save_path}")
        else:
            plt.show()
    
    def plot_phenotype_distribution(self, save_path: str = None):
        """Plot phenotype distribution"""
        if not self.cell_data:
            print("[!] No cell data available")
            return
        
        phenotypes = self.cell_data['phenotypes']
        unique_phenotypes, counts = np.unique(phenotypes, return_counts=True)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Bar plot
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_phenotypes)))
        bars = ax1.bar(unique_phenotypes, counts, color=colors)
        ax1.set_title('Phenotype Distribution (Counts)')
        ax1.set_ylabel('Number of Cells')
        ax1.set_xlabel('Phenotype')
        
        # Add count labels on bars
        for bar, count in zip(bars, counts):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01*max(counts),
                    str(count), ha='center', va='bottom')
        
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Pie chart
        ax2.pie(counts, labels=unique_phenotypes, autopct='%1.1f%%', colors=colors)
        ax2.set_title('Phenotype Distribution (Percentages)')
        
        fig.suptitle(f'Cell Phenotypes - {self.file_path.name}\n'
                    f'Total: {len(phenotypes)} cells, Step {self.metadata.get("step", "unknown")}')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[SAVE] Saved plot: {save_path}")
        else:
            plt.show()
    
    def plot_fate_genes_analysis(self, save_path: str = None):
        """Plot fate genes analysis"""
        if not self.gene_data:
            print("[!] No gene data available")
            return
        
        gene_names = self.gene_data['gene_names']
        states_matrix = self.gene_data['states']
        
        # Find fate genes
        fate_genes = ['Proliferation', 'Apoptosis', 'Growth_Arrest', 'Necrosis']
        fate_gene_indices = []
        fate_gene_names_found = []
        
        for gene in fate_genes:
            if gene in gene_names:
                fate_gene_indices.append(gene_names.index(gene))
                fate_gene_names_found.append(gene)
        
        if not fate_gene_indices:
            print("[!] No fate genes found")
            return
        
        # Calculate activation rates
        activation_rates = states_matrix[:, fate_gene_indices].mean(axis=0)
        cell_counts = states_matrix[:, fate_gene_indices].sum(axis=0)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Activation rates
        colors = ['#2E8B57', '#DC143C', '#FF8C00', '#8B0000']  # Green, Red, Orange, Dark Red
        bars1 = ax1.bar(fate_gene_names_found, activation_rates, 
                       color=colors[:len(fate_gene_names_found)])
        ax1.set_title('Fate Gene Activation Rates')
        ax1.set_ylabel('Activation Rate')
        ax1.set_xlabel('Fate Gene')
        ax1.set_ylim(0, 1)
        
        # Add percentage labels
        for bar, rate in zip(bars1, activation_rates):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{rate:.1%}', ha='center', va='bottom')
        
        # Cell counts
        bars2 = ax2.bar(fate_gene_names_found, cell_counts,
                       color=colors[:len(fate_gene_names_found)])
        ax2.set_title('Fate Gene Active Cell Counts')
        ax2.set_ylabel('Number of Active Cells')
        ax2.set_xlabel('Fate Gene')
        
        # Add count labels
        for bar, count in zip(bars2, cell_counts):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01*max(cell_counts),
                    str(int(count)), ha='center', va='bottom')
        
        fig.suptitle(f'Fate Gene Analysis - {self.file_path.name}\n'
                    f'Total: {states_matrix.shape[0]} cells, Step {self.metadata.get("step", "unknown")}')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[SAVE] Saved plot: {save_path}")
        else:
            plt.show()
    
    def plot_age_distribution(self, save_path: str = None):
        """Plot cell age distribution"""
        if not self.cell_data:
            print("[!] No cell data available")
            return
        
        ages = self.cell_data['ages']
        phenotypes = self.cell_data['phenotypes']
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Overall age distribution
        ax1.hist(ages, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.axvline(np.mean(ages), color='red', linestyle='--', label=f'Mean: {np.mean(ages):.1f}')
        ax1.axvline(np.median(ages), color='orange', linestyle='--', label=f'Median: {np.median(ages):.1f}')
        ax1.set_title('Overall Age Distribution')
        ax1.set_xlabel('Cell Age')
        ax1.set_ylabel('Frequency')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Age distribution by phenotype
        unique_phenotypes = list(set(phenotypes))
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_phenotypes)))
        
        for i, phenotype in enumerate(unique_phenotypes):
            mask = np.array(phenotypes) == phenotype
            phenotype_ages = ages[mask]
            ax2.hist(phenotype_ages, bins=20, alpha=0.6, 
                    label=f'{phenotype} (n={np.sum(mask)})',
                    color=colors[i])
        
        ax2.set_title('Age Distribution by Phenotype')
        ax2.set_xlabel('Cell Age')
        ax2.set_ylabel('Frequency')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        fig.suptitle(f'Cell Age Analysis - {self.file_path.name}\n'
                    f'Total: {len(ages)} cells, Step {self.metadata.get("step", "unknown")}')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[SAVE] Saved plot: {save_path}")
        else:
            plt.show()
    
    def create_interactive_3d_plot(self, save_path: str = None):
        """Create interactive 3D plot with plotly"""
        if not PLOTLY_AVAILABLE:
            print("[!] Plotly not available for interactive plots")
            return
        
        if not self.cell_data:
            print("[!] No cell data available")
            return
        
        positions = self.cell_data['positions']
        if positions.shape[1] < 3:
            print("[!] Not 3D data")
            return
        
        phenotypes = self.cell_data['phenotypes']
        ages = self.cell_data['ages']
        
        # Create color mapping for phenotypes
        unique_phenotypes = list(set(phenotypes))
        color_map = px.colors.qualitative.Set3[:len(unique_phenotypes)]
        phenotype_colors = {phenotype: color_map[i] for i, phenotype in enumerate(unique_phenotypes)}
        colors = [phenotype_colors[p] for p in phenotypes]
        
        fig = go.Figure(data=go.Scatter3d(
            x=positions[:, 0],
            y=positions[:, 1],
            z=positions[:, 2],
            mode='markers',
            marker=dict(
                size=5,
                color=colors,
                opacity=0.8
            ),
            text=[f'ID: {self.cell_data["ids"][i]}<br>'
                  f'Phenotype: {phenotypes[i]}<br>'
                  f'Age: {ages[i]:.1f}<br>'
                  f'Position: ({positions[i, 0]:.2e}, {positions[i, 1]:.2e}, {positions[i, 2]:.2e})'
                  for i in range(len(phenotypes))],
            hovertemplate='%{text}<extra></extra>'
        ))
        
        fig.update_layout(
            title=f'Interactive 3D Cell Positions - {self.file_path.name}<br>'
                  f'{len(positions)} cells, Step {self.metadata.get("step", "unknown")}',
            scene=dict(
                xaxis_title='X Position (m)',
                yaxis_title='Y Position (m)',
                zaxis_title='Z Position (m)'
            ),
            width=800,
            height=600
        )
        
        if save_path:
            fig.write_html(save_path)
            print(f"[SAVE] Saved interactive plot: {save_path}")
        else:
            fig.show()
    
    def create_all_plots(self, output_dir: str = "visualizations"):
        """Create all available plots"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        base_name = self.file_path.stem
        
        print(f"\n[ART] Creating all visualizations...")
        print(f"[DIR] Output directory: {output_path}")
        
        # 2D positions
        if self.cell_data:
            self.plot_cell_positions_2d(
                save_path=output_path / f"{base_name}_positions_2d.png"
            )
            
            # 3D positions if available
            if self.cell_data['positions'].shape[1] >= 3:
                self.plot_cell_positions_3d(
                    save_path=output_path / f"{base_name}_positions_3d.png"
                )
                
                # Interactive 3D plot
                if PLOTLY_AVAILABLE:
                    self.create_interactive_3d_plot(
                        save_path=output_path / f"{base_name}_interactive_3d.html"
                    )
            
            # Phenotype distribution
            self.plot_phenotype_distribution(
                save_path=output_path / f"{base_name}_phenotypes.png"
            )
            
            # Age distribution
            self.plot_age_distribution(
                save_path=output_path / f"{base_name}_ages.png"
            )
        
        # Gene heatmap
        if self.gene_data:
            self.plot_gene_heatmap(
                save_path=output_path / f"{base_name}_gene_heatmap.png"
            )
            
            # Fate genes analysis
            self.plot_fate_genes_analysis(
                save_path=output_path / f"{base_name}_fate_genes.png"
            )
        
        print(f"[+] All visualizations created in {output_path}")


class TemporalAnalyzer:
    """Analyze temporal evolution across multiple cell state files"""

    def __init__(self, file_paths: List[str]):
        self.file_paths = [Path(p) for p in file_paths]
        self.time_points = []
        self.cell_counts = []
        self.phenotype_data = []
        self.gene_data = []

        self._load_temporal_data()

    def _load_temporal_data(self):
        """Load data from multiple time points"""
        print(f"📂 Loading {len(self.file_paths)} time points...")

        for file_path in sorted(self.file_paths):
            if not file_path.exists():
                print(f"[WARN]  File not found: {file_path}")
                continue

            try:
                with h5py.File(file_path, 'r') as f:
                    # Get step number
                    step = f['metadata'].attrs.get('step', 0)
                    self.time_points.append(step)

                    # Get cell count
                    cell_count = f['metadata'].attrs.get('cell_count', 0)
                    self.cell_counts.append(cell_count)

                    # Get phenotype distribution
                    if 'cells' in f:
                        phenotypes = [s.decode('utf-8') for s in f['cells']['phenotypes'][:]]
                        unique_phenotypes, counts = np.unique(phenotypes, return_counts=True)
                        phenotype_dict = {p: c for p, c in zip(unique_phenotypes, counts)}
                        self.phenotype_data.append(phenotype_dict)

                    # Get gene activation rates
                    if 'gene_states' in f:
                        gene_names = [s.decode('utf-8') for s in f['gene_states']['gene_names'][:]]
                        states_matrix = f['gene_states']['states'][:]
                        activation_rates = states_matrix.mean(axis=0)
                        gene_dict = {gene: rate for gene, rate in zip(gene_names, activation_rates)}
                        self.gene_data.append(gene_dict)

            except Exception as e:
                print(f"[WARN]  Error loading {file_path}: {e}")

        print(f"[+] Loaded {len(self.time_points)} time points")

    def plot_population_evolution(self, save_path: str = None):
        """Plot population evolution over time"""
        if not self.time_points:
            print("[!] No temporal data available")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Total cell count evolution
        ax1.plot(self.time_points, self.cell_counts, 'o-', linewidth=2, markersize=8)
        ax1.set_title('Population Size Evolution')
        ax1.set_xlabel('Simulation Step')
        ax1.set_ylabel('Total Cell Count')
        ax1.grid(True, alpha=0.3)

        # Phenotype evolution
        if self.phenotype_data:
            all_phenotypes = set()
            for phenotype_dict in self.phenotype_data:
                all_phenotypes.update(phenotype_dict.keys())

            colors = plt.cm.Set3(np.linspace(0, 1, len(all_phenotypes)))
            phenotype_colors = {p: colors[i] for i, p in enumerate(sorted(all_phenotypes))}

            for phenotype in sorted(all_phenotypes):
                counts = [phenotype_dict.get(phenotype, 0) for phenotype_dict in self.phenotype_data]
                ax2.plot(self.time_points, counts, 'o-',
                        label=phenotype, color=phenotype_colors[phenotype],
                        linewidth=2, markersize=6)

            ax2.set_title('Phenotype Evolution')
            ax2.set_xlabel('Simulation Step')
            ax2.set_ylabel('Cell Count by Phenotype')
            ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[SAVE] Saved plot: {save_path}")
        else:
            plt.show()

    def plot_fate_gene_evolution(self, save_path: str = None):
        """Plot fate gene evolution over time"""
        if not self.gene_data:
            print("[!] No gene data available")
            return

        fate_genes = ['Proliferation', 'Apoptosis', 'Growth_Arrest', 'Necrosis']
        colors = ['#2E8B57', '#DC143C', '#FF8C00', '#8B0000']

        fig, ax = plt.subplots(figsize=(12, 8))

        for i, gene in enumerate(fate_genes):
            activation_rates = []
            for gene_dict in self.gene_data:
                rate = gene_dict.get(gene, 0)
                activation_rates.append(rate)

            if any(rate > 0 for rate in activation_rates):  # Only plot if gene is active
                ax.plot(self.time_points, activation_rates, 'o-',
                       label=gene, color=colors[i], linewidth=2, markersize=6)

        ax.set_title('Fate Gene Activation Evolution')
        ax.set_xlabel('Simulation Step')
        ax.set_ylabel('Activation Rate')
        ax.set_ylim(0, 1)
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[SAVE] Saved plot: {save_path}")
        else:
            plt.show()


def analyze_temporal_evolution(file_pattern: str, output_dir: str = "temporal_analysis"):
    """Analyze temporal evolution from multiple files"""
    from glob import glob

    file_paths = glob(file_pattern)
    if not file_paths:
        print(f"[!] No files found matching pattern: {file_pattern}")
        return

    print(f"[TIME] Analyzing temporal evolution from {len(file_paths)} files")

    analyzer = TemporalAnalyzer(file_paths)

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Create temporal plots
    analyzer.plot_population_evolution(
        save_path=output_path / "population_evolution.png"
    )

    analyzer.plot_fate_gene_evolution(
        save_path=output_path / "fate_gene_evolution.png"
    )

    print(f"[+] Temporal analysis completed in {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Visualize MicroC cell state and initial state files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cell_state_visualizer.py initial_state_3D_S.h5
  python cell_state_visualizer.py cell_state.h5 --positions-3d
  python cell_state_visualizer.py state.h5 --gene-heatmap --fate-genes
  python cell_state_visualizer.py state.h5 --all-plots --output-dir my_plots
        """
    )
    
    parser.add_argument('file_path', help='Path to the cell state HDF5 file')
    parser.add_argument('--positions-2d', action='store_true',
                       help='Plot 2D cell positions')
    parser.add_argument('--positions-3d', action='store_true',
                       help='Plot 3D cell positions')
    parser.add_argument('--interactive-3d', action='store_true',
                       help='Create interactive 3D plot (requires plotly)')
    parser.add_argument('--gene-heatmap', action='store_true',
                       help='Plot gene activation heatmap')
    parser.add_argument('--phenotypes', action='store_true',
                       help='Plot phenotype distribution')
    parser.add_argument('--fate-genes', action='store_true',
                       help='Plot fate genes analysis')
    parser.add_argument('--ages', action='store_true',
                       help='Plot age distribution')
    parser.add_argument('--all-plots', action='store_true',
                       help='Create all available plots')
    parser.add_argument('--temporal', action='store_true',
                       help='Analyze temporal evolution (file_path should be a pattern)')
    parser.add_argument('--output-dir', default=None,
                       help='Output directory for plots (default: cell_visualizer_results)')
    parser.add_argument('--show', action='store_true',
                       help='Show plots instead of saving them')
    
    args = parser.parse_args()
    
    try:
        # Handle temporal analysis
        if args.temporal:
            analyze_temporal_evolution(args.file_path, args.output_dir)
            return

        # Create visualizer
        visualizer = CellStateVisualizer(args.file_path)

        # Set default output directory if not specified
        if args.output_dir is None:
            script_dir = Path(__file__).parent
            args.output_dir = script_dir / "cell_visualizer_results"

        save_path_func = lambda name: None if args.show else f"{args.output_dir}/{visualizer.file_path.stem}_{name}.png"
        
        if args.all_plots:
            visualizer.create_all_plots(args.output_dir)
        else:
            # Create output directory if saving
            if not args.show:
                Path(args.output_dir).mkdir(exist_ok=True)
            
            # Individual plots
            if args.positions_2d:
                visualizer.plot_cell_positions_2d(save_path_func("positions_2d"))
            
            if args.positions_3d:
                visualizer.plot_cell_positions_3d(save_path_func("positions_3d"))
            
            if args.interactive_3d:
                save_path = None if args.show else f"{args.output_dir}/{visualizer.file_path.stem}_interactive_3d.html"
                visualizer.create_interactive_3d_plot(save_path)
            
            if args.gene_heatmap:
                visualizer.plot_gene_heatmap(save_path_func("gene_heatmap"))
            
            if args.phenotypes:
                visualizer.plot_phenotype_distribution(save_path_func("phenotypes"))
            
            if args.fate_genes:
                visualizer.plot_fate_genes_analysis(save_path_func("fate_genes"))
            
            if args.ages:
                visualizer.plot_age_distribution(save_path_func("ages"))
            
            # Default behavior - show basic plots
            if not any([args.positions_2d, args.positions_3d, args.interactive_3d, 
                       args.gene_heatmap, args.phenotypes, args.fate_genes, args.ages]):
                print("[*] Creating default visualizations...")
                visualizer.plot_cell_positions_2d(save_path_func("positions_2d"))
                visualizer.plot_phenotype_distribution(save_path_func("phenotypes"))
                if visualizer.gene_data:
                    visualizer.plot_fate_genes_analysis(save_path_func("fate_genes"))
        
        print(f"\n[+] Visualization completed successfully!")

    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
