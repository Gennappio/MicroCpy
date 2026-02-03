"""
Iteration-specific plotter for generating heatmaps with iteration numbers.

This module provides plotting functionality for individual loop iterations,
with iteration numbers included in filenames and plot titles.
"""

from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


class IterationPlotter:
    """
    Plotter for generating iteration-specific heatmaps.
    
    Generates substance concentration heatmaps with iteration numbers
    in both filenames and plot titles.
    """
    
    def __init__(self, config, plots_dir: Path):
        """
        Initialize the iteration plotter.
        
        Args:
            config: Simulation configuration object
            plots_dir: Directory to save plots to
        """
        self.config = config
        self.plots_dir = Path(plots_dir)
        
        # Create heatmaps subdirectory
        (self.plots_dir / "heatmaps").mkdir(parents=True, exist_ok=True)
    
    def plot_substance_heatmap(
        self,
        substance_name: str,
        concentrations: np.ndarray,
        cell_positions: List[Tuple[int, int]],
        iteration: int,
        config_name: str = "unknown",
        population=None
    ):
        """
        Plot concentration heatmap for a single substance with iteration number.
        
        Args:
            substance_name: Name of the substance
            concentrations: 2D array of concentrations
            cell_positions: List of (x, y) cell positions
            iteration: Current iteration number
            config_name: Name of the configuration
            population: Population object (for additional info)
        
        Returns:
            Path to the saved plot file
        """
        # Handle 3D arrays (take middle slice)
        if len(concentrations.shape) == 3:
            nz = concentrations.shape[0]
            middle_z = nz // 2
            plot_data = concentrations[middle_z, :, :]
        else:
            plot_data = concentrations
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Create heatmap
        vmin = plot_data.min()
        vmax = plot_data.max()
        
        im = ax.imshow(
            plot_data,
            cmap='viridis',
            origin='lower',
            aspect='equal',
            vmin=vmin,
            vmax=vmax,
            interpolation='bilinear'
        )
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(f'{substance_name} (mM)', rotation=270, labelpad=20, fontsize=12)
        
        # Plot cell positions
        if cell_positions:
            # Convert cell positions to grid coordinates
            cell_x = [pos[0] for pos in cell_positions]
            cell_y = [pos[1] for pos in cell_positions]
            
            # Scale cell positions to match grid
            if hasattr(self.config, 'domain'):
                domain = self.config.domain
                nx, ny = domain.nx, domain.ny
                domain_size_x = domain.size_x.micrometers if hasattr(domain.size_x, 'micrometers') else domain.size_x
                domain_size_y = domain.size_y.micrometers if hasattr(domain.size_y, 'micrometers') else domain.size_y
                cell_size = 20.0  # Default cell size in μm
                
                # Convert cell positions to grid coordinates
                grid_x = [int((x * cell_size) / (domain_size_x / nx)) for x in cell_x]
                grid_y = [int((y * cell_size) / (domain_size_y / ny)) for y in cell_y]
                
                ax.scatter(grid_x, grid_y, c='red', s=10, alpha=0.5, marker='o', label='Cells')
        
        # Set title with iteration number
        ax.set_title(f'{substance_name} Concentration - Iteration {iteration}', fontsize=16, fontweight='bold')
        ax.set_xlabel('X Position', fontsize=12)
        ax.set_ylabel('Y Position', fontsize=12)
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Add legend if cells are plotted
        if cell_positions:
            ax.legend(loc='upper right', fontsize=10)
        
        # Add info text
        info_text = f"Min: {vmin:.6f} mM\nMax: {vmax:.6f} mM\nMean: {plot_data.mean():.6f} mM"
        if population:
            num_cells = len(population.state.cells) if hasattr(population, 'state') else 0
            info_text += f"\nCells: {num_cells}"
        
        ax.text(
            0.02, 0.98, info_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment='top',
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9)
        )
        
        # Save plot with iteration number in filename
        filename = f"{substance_name}_heatmap_iter{iteration:03d}.png"
        filepath = self.plots_dir / "heatmaps" / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        return filepath

    def generate_iteration_plots(
        self,
        simulator,
        population,
        iteration: int,
        substance_filter: Optional[List[str]] = None
    ) -> List[Path]:
        """
        Generate all plots for a specific iteration.

        Args:
            simulator: Simulator instance for current state
            population: Population instance for cell positions
            iteration: Current iteration number
            substance_filter: Optional list of substance names to plot (None = all)

        Returns:
            List of paths to generated plot files
        """
        generated_plots = []

        if not simulator:
            print("[ITERATION_PLOTTER] No simulator provided - skipping plots")
            return generated_plots

        # Get actual cell positions from the population
        cell_positions = []
        if population:
            cell_data = population.get_cell_positions()
            cell_positions = [pos for pos, phenotype in cell_data]

        # Get config name from plots directory
        config_name = self.plots_dir.name if hasattr(self.plots_dir, 'name') else "unknown"

        # Determine which substances to plot
        if substance_filter:
            print(f"[ITERATION_PLOTTER] Substance filter requested: {substance_filter}")
            print(f"[ITERATION_PLOTTER] Simulator substances: {list(simulator.state.substances.keys())}")
            substances_to_plot = [s for s in substance_filter if s in simulator.state.substances]
            if len(substances_to_plot) < len(substance_filter):
                missing = set(substance_filter) - set(substances_to_plot)
                print(f"[ITERATION_PLOTTER] Warning: substances not found: {missing}")
            print(f"[ITERATION_PLOTTER] Will plot: {substances_to_plot}")
        else:
            substances_to_plot = list(self.config.substances.keys())

        # Generate heatmap for each substance
        for substance in substances_to_plot:
            if substance in simulator.state.substances:
                concentrations = simulator.state.substances[substance].concentrations

                plot_path = self.plot_substance_heatmap(
                    substance,
                    concentrations,
                    cell_positions,
                    iteration,
                    config_name,
                    population
                )
                generated_plots.append(plot_path)
                print(f"   [OK] {substance} heatmap (iter {iteration}): {plot_path.name}")

        return generated_plots

