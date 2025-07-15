"""
Export and animation tools for MicroC 2.0

Provides data export and animation capabilities for simulation results.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from typing import Dict, List, Optional, Any, Callable
import json
import csv
from pathlib import Path
import sys

# Add interfaces to path
sys.path.insert(0, str(Path(__file__).parent.parent))
# CustomizableComponent removed - using direct function calls

class PlotExporter:
    """
    Export simulation data and plots in various formats
    """
    
    def __init__(self, output_dir: str = "plots", custom_functions_module=None):
        super().__init__(custom_functions_module)
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"📁 Plot export directory: {self.output_dir.absolute()}")
    
    def export_concentration_data(self, simulator, filename: str = "concentration_data.csv") -> str:
        """Export concentration field data to CSV"""
        
        concentration = np.array(simulator.concentration.value)
        mesh = simulator.mesh_manager.mesh
        
        # Create coordinate arrays
        nx = simulator.mesh_manager.config.nx
        ny = simulator.mesh_manager.config.ny
        
        # Get cell centers
        x_centers = np.array(mesh.cellCenters[0])
        y_centers = np.array(mesh.cellCenters[1])
        
        # Create DataFrame
        data = {
            'x_position_m': x_centers,
            'y_position_m': y_centers,
            'x_position_um': x_centers * 1e6,
            'y_position_um': y_centers * 1e6,
            'concentration_mM': concentration
        }
        
        df = pd.DataFrame(data)
        
        # Save to CSV
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        print(f"📊 Concentration data exported: {filepath}")
        return str(filepath)
    
    def export_population_data(self, population, filename: str = "population_data.csv") -> str:
        """Export cell population data to CSV"""
        
        # Collect cell data
        cell_data = []
        for cell_id, cell in population.state.cells.items():
            cell_data.append({
                'cell_id': cell_id,
                'x_position': cell.state.position[0],
                'y_position': cell.state.position[1],
                'phenotype': cell.state.phenotype,
                'age_hours': cell.state.age,
                'generation': getattr(cell.state, 'generation', 0),  # Default to 0 if not present
                'is_alive': getattr(cell.state, 'is_alive', True)  # Default to True if not present
            })
        
        df = pd.DataFrame(cell_data)
        
        # Save to CSV
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        print(f"🦠 Population data exported: {filepath}")
        return str(filepath)
    
    def export_performance_data(self, monitor, filename: str = "performance_data.json") -> str:
        """Export performance monitoring data to JSON"""
        
        # Get comprehensive performance data
        stats = monitor.get_statistics()
        metrics_history = monitor.get_metrics_history()
        
        # Prepare export data
        export_data = {
            'summary_statistics': stats,
            'metrics_history': metrics_history,
            'export_timestamp': pd.Timestamp.now().isoformat()
        }
        
        # Save to JSON
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"📊 Performance data exported: {filepath}")
        return str(filepath)
    
    def export_simulation_summary(self, simulator, population, monitor, 
                                filename: str = "simulation_summary.json") -> str:
        """Export comprehensive simulation summary"""
        
        # Collect all simulation data
        summary = {
            'simulation_info': simulator.get_simulation_info(),
            'population_statistics': population.get_population_statistics(),
            'performance_summary': monitor.get_statistics(),
            'mesh_metadata': simulator.mesh_manager.get_metadata(),
            'export_timestamp': pd.Timestamp.now().isoformat()
        }
        
        # Save to JSON
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"📋 Simulation summary exported: {filepath}")
        return str(filepath)
    
    def create_publication_figure(self, simulator, population, monitor, 
                                filename: str = "publication_figure.png") -> str:
        """Create a publication-ready figure"""
        
        # Import plotter here to avoid circular imports
        from .plotter import SimulationPlotter, PlotConfig
        
        # Configure for publication
        pub_config = PlotConfig(
            figsize=(12, 8),
            dpi=300,
            font_size=12,
            title_size=14,
            save_format='png'
        )
        
        plotter = SimulationPlotter(pub_config)
        
        # Create comprehensive overview
        fig = plotter.plot_combined_overview(
            simulator, population, monitor,
            title="MicroC 2.0 Simulation Results"
        )
        
        # Save with high quality
        filepath = self.output_dir / filename
        fig.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        print(f"📊 Publication figure saved: {filepath}")
        return str(filepath)

class AnimationExporter:
    """
    Create animations from simulation time series data
    """
    
    def __init__(self, output_dir: str = "plots", custom_functions_module=None):
        super().__init__(custom_functions_module)
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def animate_concentration_evolution(self, concentration_history: List[np.ndarray],
                                      mesh_config, substance_name: str = "Substance",
                                      filename: str = "concentration_animation.gif",
                                      fps: int = 2) -> str:
        """Create animation of concentration field evolution"""
        
        if not concentration_history:
            raise ValueError("No concentration history provided")
        
        # Set up figure
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Get mesh parameters
        nx, ny = mesh_config.nx, mesh_config.ny
        x = np.linspace(0, mesh_config.size_x.micrometers, nx)
        y = np.linspace(0, mesh_config.size_y.micrometers, ny)
        X, Y = np.meshgrid(x, y)
        
        # Find global min/max for consistent color scale
        all_concentrations = np.concatenate([conc.flatten() for conc in concentration_history])
        vmin, vmax = np.min(all_concentrations), np.max(all_concentrations)
        
        # Initialize plot
        conc_2d = concentration_history[0].reshape((ny, nx))
        im = ax.contourf(X, Y, conc_2d, levels=20, vmin=vmin, vmax=vmax, cmap='viridis')
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(f'{substance_name} (mM)')
        
        ax.set_xlabel('X Position (μm)')
        ax.set_ylabel('Y Position (μm)')
        title = ax.set_title(f'{substance_name} Evolution - Step 0')
        ax.set_aspect('equal')
        
        def animate(frame):
            ax.clear()
            conc_2d = concentration_history[frame].reshape((ny, nx))
            im = ax.contourf(X, Y, conc_2d, levels=20, vmin=vmin, vmax=vmax, cmap='viridis')
            ax.set_xlabel('X Position (μm)')
            ax.set_ylabel('Y Position (μm)')
            ax.set_title(f'{substance_name} Evolution - Step {frame}')
            ax.set_aspect('equal')
            return [im]
        
        # Create animation
        anim = animation.FuncAnimation(
            fig, animate, frames=len(concentration_history),
            interval=1000//fps, blit=False, repeat=True
        )
        
        # Save animation
        filepath = self.output_dir / filename
        anim.save(filepath, writer='pillow', fps=fps)
        plt.close(fig)
        
        print(f"🎬 Concentration animation saved: {filepath}")
        return str(filepath)
    
    def animate_population_growth(self, population_history: List[Dict],
                                grid_size: tuple,
                                filename: str = "population_animation.gif",
                                fps: int = 2) -> str:
        """Create animation of population growth"""
        
        if not population_history:
            raise ValueError("No population history provided")
        
        # Set up figure
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Color scheme for phenotypes
        # Use Jayatilake experiment color scheme with distinct colors
        phenotype_colors = {
            'Proliferation': 'green',
            'Quiescence': 'blue',
            'Hypoxia': 'orange',
            'Necrosis': 'black',
            'Apoptosis': 'red',
            'growth_arrest': 'orange',     # Different from proliferation
            'proliferation': 'lightgreen', # Different from quiescence
            'normal': '#2E8B57',
            'hypoxic': '#DC143C',
            'proliferative': '#4169E1',
            'quiescent': '#DAA520',
            'dead': '#696969'
        }
        
        def animate(frame):
            ax.clear()

            # Get population data for this frame
            pop_data = population_history[frame]

            # Track colors used for legend
            colors_used = {}

            # Plot cells if position data is available
            if 'cell_positions' in pop_data:
                for pos, phenotype in pop_data['cell_positions']:
                    x, y = pos
                    color = phenotype_colors.get(phenotype, '#808080')
                    colors_used[phenotype] = color
                    ax.scatter(x, y, c=color, s=100, alpha=0.7,
                             edgecolors='black', linewidth=0.5)

            # Set up grid
            ax.set_xlim(-0.5, grid_size[0] - 0.5)
            ax.set_ylim(-0.5, grid_size[1] - 0.5)

            # Add grid lines
            for i in range(grid_size[0] + 1):
                ax.axvline(i - 0.5, color='gray', alpha=0.3, linewidth=0.5)
            for i in range(grid_size[1] + 1):
                ax.axhline(i - 0.5, color='gray', alpha=0.3, linewidth=0.5)

            # Add legend for cell types
            if colors_used:
                from matplotlib.patches import Patch
                legend_elements = [Patch(facecolor=color, label=phenotype)
                                 for phenotype, color in sorted(colors_used.items())]
                ax.legend(handles=legend_elements, loc='upper right',
                         title='Cell Types', fontsize=8)

            ax.set_xlabel('Grid X')
            ax.set_ylabel('Grid Y')
            ax.set_title(f'Population Evolution - Step {frame} '
                        f'(Total: {pop_data.get("total_cells", 0)} cells)')
            ax.set_aspect('equal')
        
        # Create animation
        anim = animation.FuncAnimation(
            fig, animate, frames=len(population_history),
            interval=1000//fps, blit=False, repeat=True
        )
        
        # Save animation
        filepath = self.output_dir / filename
        anim.save(filepath, writer='pillow', fps=fps)
        plt.close(fig)
        
        print(f"🎬 Population animation saved: {filepath}")
        return str(filepath)
    
    def create_combined_animation(self, concentration_history: List[np.ndarray],
                                population_history: List[Dict],
                                mesh_config, substance_name: str = "Substance",
                                filename: str = "combined_animation.gif",
                                fps: int = 2) -> str:
        """Create combined animation of concentration and population"""
        
        if len(concentration_history) != len(population_history):
            raise ValueError("Concentration and population histories must have same length")
        
        # Set up figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Mesh parameters
        nx, ny = mesh_config.nx, mesh_config.ny
        x = np.linspace(0, mesh_config.size_x.micrometers, nx)
        y = np.linspace(0, mesh_config.size_y.micrometers, ny)
        X, Y = np.meshgrid(x, y)
        
        # Color scales
        all_concentrations = np.concatenate([conc.flatten() for conc in concentration_history])
        vmin, vmax = np.min(all_concentrations), np.max(all_concentrations)
        
        # Use Jayatilake experiment color scheme with distinct colors
        phenotype_colors = {
            'Proliferation': 'green',
            'Quiescence': 'blue',
            'Hypoxia': 'orange',
            'Necrosis': 'black',
            'Apoptosis': 'red',
            'growth_arrest': 'orange',     # Different from proliferation
            'proliferation': 'lightgreen', # Different from quiescence
            'normal': '#2E8B57',
            'hypoxic': '#DC143C',
            'proliferative': '#4169E1',
            'quiescent': '#DAA520',
            'dead': '#696969'
        }
        
        def animate(frame):
            # Clear both axes
            ax1.clear()
            ax2.clear()
            
            # Plot concentration field
            conc_2d = concentration_history[frame].reshape((ny, nx))
            im = ax1.contourf(X, Y, conc_2d, levels=20, vmin=vmin, vmax=vmax, cmap='viridis')
            ax1.set_xlabel('X Position (μm)')
            ax1.set_ylabel('Y Position (μm)')
            ax1.set_title(f'{substance_name} Field - Step {frame}')
            ax1.set_aspect('equal')
            
            # Plot population
            pop_data = population_history[frame]
            colors_used = {}
            if 'cell_positions' in pop_data:
                for pos, phenotype in pop_data['cell_positions']:
                    x_pos, y_pos = pos
                    color = phenotype_colors.get(phenotype, '#808080')
                    colors_used[phenotype] = color
                    ax2.scatter(x_pos, y_pos, c=color, s=100, alpha=0.7,
                              edgecolors='black', linewidth=0.5)

            # Add legend for cell types
            if colors_used:
                from matplotlib.patches import Patch
                legend_elements = [Patch(facecolor=color, label=phenotype)
                                 for phenotype, color in sorted(colors_used.items())]
                ax2.legend(handles=legend_elements, loc='upper right',
                          title='Cell Types', fontsize=6)

            grid_size = (nx, ny)  # Assuming grid matches mesh
            ax2.set_xlim(-0.5, grid_size[0] - 0.5)
            ax2.set_ylim(-0.5, grid_size[1] - 0.5)
            ax2.set_xlabel('Grid X')
            ax2.set_ylabel('Grid Y')
            ax2.set_title(f'Cell Population - Step {frame} '
                         f'(Total: {pop_data.get("total_cells", 0)})')
            ax2.set_aspect('equal')
            
            plt.tight_layout()
        
        # Create animation
        anim = animation.FuncAnimation(
            fig, animate, frames=len(concentration_history),
            interval=1000//fps, blit=False, repeat=True
        )
        
        # Save animation
        filepath = self.output_dir / filename
        anim.save(filepath, writer='pillow', fps=fps)
        plt.close(fig)
        
        print(f"🎬 Combined animation saved: {filepath}")
        return str(filepath)
