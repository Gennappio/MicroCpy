#!/usr/bin/env python3
"""
Simple Cell State Visualizer for MicroC 2.0 (Windows Compatible)

A simplified visualization tool without Unicode characters for Windows compatibility.
"""

import argparse
import h5py
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

class SimpleCellStateVisualizer:
    """Simple visualizer for MicroC cell state files"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.metadata = {}
        self.cell_data = {}
        self.gene_data = {}
        
        self._load_file()
        
        # Set up plotting style
        plt.style.use('default')
        sns.set_palette("husl")
    
    def _load_file(self):
        """Load data from HDF5 file"""
        print(f"Loading file: {self.file_path}")
        
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
        
        print(f"File loaded successfully")
    
    def plot_cell_positions_2d(self, save_path: str = None):
        """Plot cell positions in 2D"""
        if not self.cell_data:
            print("No cell data available")
            return
        
        positions = self.cell_data['positions']
        phenotypes = self.cell_data['phenotypes']
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Color by phenotype
        unique_phenotypes = list(set(phenotypes))
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_phenotypes)))
        phenotype_colors = {phenotype: colors[i] for i, phenotype in enumerate(unique_phenotypes)}
        
        for phenotype in unique_phenotypes:
            mask = np.array(phenotypes) == phenotype
            pos_subset = positions[mask]
            ax.scatter(pos_subset[:, 0], pos_subset[:, 1], 
                      c=[phenotype_colors[phenotype]], 
                      label=f'{phenotype} ({np.sum(mask)})',
                      alpha=0.7, s=20)
        
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.set_xlabel('X Position (m)')
        ax.set_ylabel('Y Position (m)')
        ax.set_title(f'Cell Positions - {self.file_path.name}\n'
                    f'{len(positions)} cells, Step {self.metadata.get("step", "unknown")}')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved plot: {save_path}")
        else:
            plt.show()
    
    def plot_cell_positions_3d(self, save_path: str = None):
        """Plot cell positions in 3D"""
        if not self.cell_data:
            print("No cell data available")
            return
        
        positions = self.cell_data['positions']
        if positions.shape[1] < 3:
            print("Not 3D data")
            return
        
        phenotypes = self.cell_data['phenotypes']
        
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Color by phenotype
        unique_phenotypes = list(set(phenotypes))
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_phenotypes)))
        phenotype_colors = {phenotype: colors[i] for i, phenotype in enumerate(unique_phenotypes)}
        
        for phenotype in unique_phenotypes:
            mask = np.array(phenotypes) == phenotype
            pos_subset = positions[mask]
            ax.scatter(pos_subset[:, 0], pos_subset[:, 1], pos_subset[:, 2],
                      c=[phenotype_colors[phenotype]], 
                      label=f'{phenotype} ({np.sum(mask)})',
                      alpha=0.7, s=20)
        
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.set_xlabel('X Position (m)')
        ax.set_ylabel('Y Position (m)')
        ax.set_zlabel('Z Position (m)')
        ax.set_title(f'3D Cell Positions - {self.file_path.name}\n'
                    f'{len(positions)} cells, Step {self.metadata.get("step", "unknown")}')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved plot: {save_path}")
        else:
            plt.show()
    
    def plot_phenotype_distribution(self, save_path: str = None):
        """Plot phenotype distribution"""
        if not self.cell_data:
            print("No cell data available")
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
            print(f"Saved plot: {save_path}")
        else:
            plt.show()
    
    def plot_fate_genes_analysis(self, save_path: str = None):
        """Plot fate genes analysis"""
        if not self.gene_data:
            print("No gene data available")
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
            print("No fate genes found")
            return
        
        # Calculate activation rates
        activation_rates = states_matrix[:, fate_gene_indices].mean(axis=0)
        cell_counts = states_matrix[:, fate_gene_indices].sum(axis=0)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Activation rates
        colors = ['green', 'red', 'orange', 'darkred']
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
            print(f"Saved plot: {save_path}")
        else:
            plt.show()
    
    def create_all_plots(self, output_dir: str = "simple_visualizations"):
        """Create all available plots"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        base_name = self.file_path.stem
        
        print(f"Creating all visualizations...")
        print(f"Output directory: {output_path}")
        
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
            
            # Phenotype distribution
            self.plot_phenotype_distribution(
                save_path=output_path / f"{base_name}_phenotypes.png"
            )
        
        # Fate genes analysis
        if self.gene_data:
            self.plot_fate_genes_analysis(
                save_path=output_path / f"{base_name}_fate_genes.png"
            )
        
        print(f"All visualizations created in {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Simple MicroC cell state visualizer")
    parser.add_argument('file_path', help='Path to the cell state HDF5 file')
    parser.add_argument('--positions-2d', action='store_true', help='Plot 2D cell positions')
    parser.add_argument('--positions-3d', action='store_true', help='Plot 3D cell positions')
    parser.add_argument('--phenotypes', action='store_true', help='Plot phenotype distribution')
    parser.add_argument('--fate-genes', action='store_true', help='Plot fate genes analysis')
    parser.add_argument('--all-plots', action='store_true', help='Create all available plots')
    parser.add_argument('--output-dir', default='simple_visualizations', help='Output directory')
    parser.add_argument('--show', action='store_true', help='Show plots instead of saving')
    
    args = parser.parse_args()
    
    try:
        visualizer = SimpleCellStateVisualizer(args.file_path)
        
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
            
            if args.phenotypes:
                visualizer.plot_phenotype_distribution(save_path_func("phenotypes"))
            
            if args.fate_genes:
                visualizer.plot_fate_genes_analysis(save_path_func("fate_genes"))
            
            # Default behavior
            if not any([args.positions_2d, args.positions_3d, args.phenotypes, args.fate_genes]):
                print("Creating default visualizations...")
                visualizer.plot_cell_positions_2d(save_path_func("positions_2d"))
                visualizer.plot_phenotype_distribution(save_path_func("phenotypes"))
                if visualizer.gene_data:
                    visualizer.plot_fate_genes_analysis(save_path_func("fate_genes"))
        
        print("Visualization completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
