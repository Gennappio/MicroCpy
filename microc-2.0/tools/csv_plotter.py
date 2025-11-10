#!/usr/bin/env python3
"""
CSV Plotter for MicroC 2D Simulation Results

Decoupled plotting tool that generates visualizations from CSV export files.
Can be run independently of simulation to create plots from existing CSV data.

Usage:
    python csv_plotter.py --cells-dir results/csv_cells --substances-dir results/csv_substances --output plots/
"""

import argparse
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re
from collections import defaultdict


class CSVPlotter:
    """Generate plots from CSV simulation results"""

    def __init__(self, output_dir: str = "plots"):
        """Initialize plotter with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Color schemes
        self.phenotype_colors = {
            'Proliferation': '#2E8B57',      # Sea Green
            'Growth_Arrest': '#FFD700',     # Gold
            'Apoptosis': '#DC143C',         # Crimson
            'Necrosis': '#8B4513',          # Saddle Brown
            'Quiescent': '#4682B4',         # Steel Blue
            'Unknown': '#808080'            # Gray
        }

    def load_cell_states_series(self, cells_dir: str) -> Dict[int, Dict]:
        """Load time series of cell states from CSV files"""
        cells_dir = Path(cells_dir)
        cell_files = sorted(cells_dir.glob("cells_step_*.csv"))
        
        time_series = {}
        for file_path in cell_files:
            # Extract step number from filename
            match = re.search(r'cells_step_(-?\d+)\.csv', file_path.name)
            if match:
                step = int(match.group(1))
                
                # Load cell data
                from csv_export import load_csv_cell_state
                data = load_csv_cell_state(str(file_path))
                time_series[step] = data
                
        return time_series

    def load_substance_fields_series(self, substances_dir: str) -> Dict[str, Dict[int, Dict]]:
        """Load time series of substance fields from CSV files"""
        substances_dir = Path(substances_dir)
        substance_files = sorted(substances_dir.glob("*_field_step_*.csv"))
        
        # Group by substance name
        substances = defaultdict(dict)
        for file_path in substance_files:
            # Extract substance name and step
            match = re.search(r'(.+)_field_step_(-?\d+)\.csv', file_path.name)
            if match:
                substance_name = match.group(1)
                step = int(match.group(2))
                
                # Load substance field data
                from csv_export import load_csv_substance_field
                data = load_csv_substance_field(str(file_path))
                substances[substance_name][step] = data
                
        return dict(substances)

    def plot_cell_states_snapshot(self, cell_data: Dict, step: int, save_path: Optional[str] = None):
        """Plot cell states for a single time step"""
        if not cell_data or 'cells' not in cell_data:
            print(f"[!] No cell data for step {step}")
            return

        cells = cell_data['cells']
        metadata = cell_data.get('metadata', {})

        fig, ax = plt.subplots(figsize=(10, 8))

        # Plot cells
        for cell in cells:
            x = float(cell['x'])
            y = float(cell['y'])
            phenotype = cell.get('phenotype', 'Unknown')
            color = self.phenotype_colors.get(phenotype, '#808080')
            
            ax.scatter(x, y, c=color, s=100, alpha=0.7, 
                      edgecolors='black', linewidth=0.5, label=phenotype)

        # Remove duplicate labels
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper right')

        ax.set_xlabel('X Position (grid units)')
        ax.set_ylabel('Y Position (grid units)')
        ax.set_title(f'Cell States - Step {step}')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        # Add metadata text
        if metadata:
            info_text = f"Cells: {metadata.get('cell_count', len(cells))}"
            if 'cell_size_um' in metadata:
                info_text += f"\nCell size: {metadata['cell_size_um']} μm"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[+] Cell states plot saved: {save_path}")
        else:
            plt.show()
        
        plt.close()

    def plot_substance_field_snapshot(self, field_data: Dict, substance_name: str, 
                                    step: int, save_path: Optional[str] = None):
        """Plot substance field for a single time step"""
        if not field_data or 'field_data' not in field_data:
            print(f"[!] No field data for {substance_name} at step {step}")
            return

        field_points = field_data['field_data']
        metadata = field_data.get('metadata', {})

        # Extract coordinates and concentrations
        x_coords = [float(point['x_position_um']) for point in field_points]
        y_coords = [float(point['y_position_um']) for point in field_points]
        
        # Find concentration column
        conc_key = None
        for key in field_points[0].keys():
            if 'concentration' in key.lower():
                conc_key = key
                break
        
        if not conc_key:
            print(f"[!] No concentration data found for {substance_name}")
            return

        concentrations = [float(point[conc_key]) for point in field_points]

        # Create grid for contour plot
        nx = metadata.get('nx', int(np.sqrt(len(field_points))))
        ny = metadata.get('ny', int(np.sqrt(len(field_points))))
        
        x_grid = np.array(x_coords).reshape((ny, nx))
        y_grid = np.array(y_coords).reshape((ny, nx))
        conc_grid = np.array(concentrations).reshape((ny, nx))

        fig, ax = plt.subplots(figsize=(10, 8))

        # Create contour plot
        contour = ax.contourf(x_grid, y_grid, conc_grid, levels=20, cmap='viridis')
        cbar = plt.colorbar(contour, ax=ax)
        cbar.set_label(f'{substance_name} Concentration (mM)')

        ax.set_xlabel('X Position (μm)')
        ax.set_ylabel('Y Position (μm)')
        ax.set_title(f'{substance_name} Field - Step {step}')
        ax.set_aspect('equal')

        # Add metadata text
        if metadata:
            info_text = f"Grid: {nx} × {ny}\nPoints: {metadata.get('total_points', len(field_points))}"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[+] {substance_name} field plot saved: {save_path}")
        else:
            plt.show()
        
        plt.close()

    def create_cell_animation(self, time_series: Dict[int, Dict], save_path: Optional[str] = None):
        """Create animation of cell states over time"""
        if not time_series:
            print("[!] No time series data for animation")
            return

        steps = sorted(time_series.keys())
        
        fig, ax = plt.subplots(figsize=(10, 8))

        def animate(frame_idx):
            ax.clear()
            step = steps[frame_idx]
            cell_data = time_series[step]
            
            if 'cells' not in cell_data:
                return

            cells = cell_data['cells']
            colors_used = {}

            # Plot cells
            for cell in cells:
                x = float(cell['x'])
                y = float(cell['y'])
                phenotype = cell.get('phenotype', 'Unknown')
                color = self.phenotype_colors.get(phenotype, '#808080')
                colors_used[phenotype] = color
                
                ax.scatter(x, y, c=color, s=100, alpha=0.7,
                          edgecolors='black', linewidth=0.5)

            # Set consistent axis limits
            all_x = []
            all_y = []
            for step_data in time_series.values():
                if 'cells' in step_data:
                    for cell in step_data['cells']:
                        all_x.append(float(cell['x']))
                        all_y.append(float(cell['y']))
            
            if all_x and all_y:
                margin = 2
                ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
                ax.set_ylim(min(all_y) - margin, max(all_y) + margin)

            # Legend
            if colors_used:
                legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                            markerfacecolor=color, markersize=10, label=phenotype)
                                 for phenotype, color in colors_used.items()]
                ax.legend(handles=legend_elements, loc='upper right')

            ax.set_xlabel('X Position (grid units)')
            ax.set_ylabel('Y Position (grid units)')
            ax.set_title(f'Cell States - Step {step}')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')

        anim = animation.FuncAnimation(fig, animate, frames=len(steps), 
                                     interval=500, repeat=True)
        
        if save_path:
            anim.save(save_path, writer='pillow', fps=2)
            print(f"[+] Cell animation saved: {save_path}")
        else:
            plt.show()
        
        plt.close()

    def plot_population_statistics(self, time_series: Dict[int, Dict], save_path: Optional[str] = None):
        """Plot population statistics over time"""
        if not time_series:
            print("[!] No time series data for statistics")
            return

        steps = sorted(time_series.keys())
        phenotype_counts = defaultdict(list)
        total_counts = []

        # Collect statistics
        for step in steps:
            cell_data = time_series[step]
            if 'cells' not in cell_data:
                continue

            cells = cell_data['cells']
            total_counts.append(len(cells))
            
            # Count phenotypes
            step_phenotypes = defaultdict(int)
            for cell in cells:
                phenotype = cell.get('phenotype', 'Unknown')
                step_phenotypes[phenotype] += 1
            
            # Add counts for this step
            for phenotype in self.phenotype_colors.keys():
                phenotype_counts[phenotype].append(step_phenotypes.get(phenotype, 0))

        # Create plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Total population
        ax1.plot(steps, total_counts, 'b-', linewidth=2, marker='o')
        ax1.set_xlabel('Simulation Step')
        ax1.set_ylabel('Total Cell Count')
        ax1.set_title('Total Population Over Time')
        ax1.grid(True, alpha=0.3)

        # Phenotype breakdown
        for phenotype, counts in phenotype_counts.items():
            if any(c > 0 for c in counts):  # Only plot if phenotype appears
                color = self.phenotype_colors.get(phenotype, '#808080')
                ax2.plot(steps, counts, color=color, linewidth=2, 
                        marker='o', label=phenotype)

        ax2.set_xlabel('Simulation Step')
        ax2.set_ylabel('Cell Count by Phenotype')
        ax2.set_title('Phenotype Distribution Over Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[+] Population statistics plot saved: {save_path}")
        else:
            plt.show()
        
        plt.close()


def main():
    parser = argparse.ArgumentParser(description='Generate plots from CSV simulation results')
    parser.add_argument('--cells-dir', required=True, help='Directory containing CSV cell state files')
    parser.add_argument('--substances-dir', help='Directory containing CSV substance field files')
    parser.add_argument('--output', '-o', default='plots', help='Output directory for plots')
    parser.add_argument('--snapshots', action='store_true', help='Generate snapshot plots for each step')
    parser.add_argument('--animations', action='store_true', help='Generate animations')
    parser.add_argument('--statistics', action='store_true', help='Generate population statistics plots')
    parser.add_argument('--step', type=int, help='Generate plots for specific step only')
    
    args = parser.parse_args()
    
    plotter = CSVPlotter(args.output)
    
    # Load cell data
    print(f"[*] Loading cell states from {args.cells_dir}...")
    cell_time_series = plotter.load_cell_states_series(args.cells_dir)
    
    if not cell_time_series:
        print("[!] No cell data found")
        return
    
    print(f"[+] Loaded {len(cell_time_series)} time steps")
    
    # Load substance data if available
    substance_time_series = {}
    if args.substances_dir:
        print(f"[*] Loading substance fields from {args.substances_dir}...")
        substance_time_series = plotter.load_substance_fields_series(args.substances_dir)
        if substance_time_series:
            print(f"[+] Loaded {len(substance_time_series)} substances")
    
    # Generate plots based on options
    if args.step is not None:
        # Single step plots
        if args.step in cell_time_series:
            output_path = plotter.output_dir / f"cells_step_{args.step:06d}.png"
            plotter.plot_cell_states_snapshot(cell_time_series[args.step], args.step, str(output_path))
            
            # Substance fields for this step
            for substance_name, substance_data in substance_time_series.items():
                if args.step in substance_data:
                    output_path = plotter.output_dir / f"{substance_name}_step_{args.step:06d}.png"
                    plotter.plot_substance_field_snapshot(
                        substance_data[args.step], substance_name, args.step, str(output_path))
        else:
            print(f"[!] Step {args.step} not found in data")
    
    elif args.snapshots:
        # Generate snapshots for all steps
        print("[*] Generating snapshot plots...")
        for step, cell_data in cell_time_series.items():
            output_path = plotter.output_dir / f"cells_step_{step:06d}.png"
            plotter.plot_cell_states_snapshot(cell_data, step, str(output_path))
            
            # Substance fields
            for substance_name, substance_data in substance_time_series.items():
                if step in substance_data:
                    output_path = plotter.output_dir / f"{substance_name}_step_{step:06d}.png"
                    plotter.plot_substance_field_snapshot(
                        substance_data[step], substance_name, step, str(output_path))
    
    if args.animations:
        # Generate animations
        print("[*] Generating cell animation...")
        output_path = plotter.output_dir / "cells_animation.gif"
        plotter.create_cell_animation(cell_time_series, str(output_path))
    
    if args.statistics:
        # Generate statistics plots
        print("[*] Generating population statistics...")
        output_path = plotter.output_dir / "population_statistics.png"
        plotter.plot_population_statistics(cell_time_series, str(output_path))
    
    print(f"[DONE] Plots saved to {plotter.output_dir}")


if __name__ == '__main__':
    main()
