"""
Main plotting functionality for MicroC 2.0

Provides comprehensive visualization of simulation results including:
- Substance concentration fields
- Cell population distributions  
- Performance metrics
- Multi-panel scientific figures
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import sys
from pathlib import Path

# Add interfaces to path
sys.path.insert(0, str(Path(__file__).parent.parent))
# Hook system removed - using direct function calls

@dataclass
class PlotConfig:
    """Configuration for plotting parameters"""
    figsize: Tuple[float, float] = (12, 8)
    dpi: int = 300
    style: str = 'seaborn-v0_8'
    colormap: str = 'viridis'
    font_size: int = 12
    title_size: int = 14
    label_size: int = 10
    save_format: str = 'png'
    transparent: bool = False
    bbox_inches: str = 'tight'

class SimulationPlotter:
    """
    Comprehensive plotting system for MicroC 2.0 simulations
    
    Provides publication-quality visualizations of simulation results.
    """
    
    def __init__(self, config: Optional[PlotConfig] = None, custom_functions_module=None):
        super().__init__(custom_functions_module)
        
        self.config = config or PlotConfig()
        
        # Set up matplotlib style
        plt.style.use('default')  # Use default instead of seaborn
        plt.rcParams.update({
            'font.size': self.config.font_size,
            'axes.titlesize': self.config.title_size,
            'axes.labelsize': self.config.label_size,
            'figure.dpi': self.config.dpi
        })
        
        # Color schemes
        self.phenotype_colors = {
            'normal': '#2E8B57',      # Sea green
            'hypoxic': '#DC143C',     # Crimson
            'proliferative': '#4169E1', # Royal blue
            'quiescent': '#DAA520',   # Goldenrod
            'dead': '#696969'         # Dim gray
        }
        
        # Custom colormap for concentrations
        self.concentration_cmap = LinearSegmentedColormap.from_list(
            'concentration', ['#000080', '#0000FF', '#00FFFF', '#FFFF00', '#FF0000']
        )

    def _get_threshold_for_substance(self, substance_name, config):
        """Get the threshold value for a substance if it has a gene network association."""
        # Mapping from substance names to gene network input nodes
        if not hasattr(config, 'associations') or not hasattr(config, 'thresholds'):
            return None

        # Check if substance has an association with a gene network input
        if substance_name in config.associations:
            gene_input_name = config.associations[substance_name]

            # Check if that gene input has a threshold defined
            if gene_input_name in config.thresholds:
                threshold_config = config.thresholds[gene_input_name]
                return threshold_config.threshold

        return None
    
    def plot_concentration_field(self, simulator, title: str = "Substance Concentration", 
                               save_path: Optional[str] = None) -> plt.Figure:
        """Plot 2D concentration field"""
        
        # Get concentration data
        concentration = np.array(simulator.concentration.value)
        mesh = simulator.mesh_manager.mesh
        
        # Reshape for 2D plotting
        nx = simulator.mesh_manager.config.nx
        ny = simulator.mesh_manager.config.ny
        conc_2d = concentration.reshape((ny, nx))
        
        # Create figure
        fig, ax = plt.subplots(figsize=self.config.figsize)
        
        # Create coordinate arrays
        x = np.linspace(0, simulator.mesh_manager.config.size_x.micrometers, nx)
        y = np.linspace(0, simulator.mesh_manager.config.size_y.micrometers, ny)
        X, Y = np.meshgrid(x, y)
        
        # Plot concentration field
        im = ax.contourf(X, Y, conc_2d, levels=20, cmap=self.concentration_cmap)

        # Add threshold isoline if this substance has a gene network association
        substance_name = simulator.substance_config.name
        threshold_value = self._get_threshold_for_substance(substance_name, simulator.config)
        if threshold_value is not None:
            # Add threshold contour line
            threshold_contour = ax.contour(X, Y, conc_2d, levels=[threshold_value],
                                         colors=['red'], linewidths=2, linestyles='-')
            # Add threshold label
            ax.clabel(threshold_contour, inline=True, fontsize=10, fmt=f'Threshold: {threshold_value:.3g}')
            print(f"   🎯 Added threshold isoline at {threshold_value:.3g} mM for {substance_name}")

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(f'{simulator.substance_config.name} (mM)', fontsize=self.config.label_size)
        
        # Formatting
        ax.set_xlabel('X Position (μm)', fontsize=self.config.label_size)
        ax.set_ylabel('Y Position (μm)', fontsize=self.config.label_size)
        ax.set_title(title, fontsize=self.config.title_size)
        ax.set_aspect('equal')
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Save if requested
        if save_path:
            self._save_figure(fig, save_path)
        
        return fig
    
    def plot_cell_population(self, population, title: str = "Cell Population", 
                           save_path: Optional[str] = None) -> plt.Figure:
        """Plot cell population distribution"""
        
        fig, ax = plt.subplots(figsize=self.config.figsize)
        
        # Get cell positions and phenotypes
        positions = population.get_cell_positions()
        
        # Plot cells by phenotype with custom colors if available
        cell_colors_used = {}
        for (pos, phenotype) in positions:
            x, y = pos

            # Try to get custom cell color first
            interior_color = '#D3D3D3'  # default light gray interior
            border_color = '#808080'    # default gray border
            try:
                # Try to get the actual cell object to get gene states
                cell = population.get_cell_at_position(pos)
                if cell and hasattr(population, 'custom_functions') and population.custom_functions and hasattr(population.custom_functions, 'get_cell_color'):
                    gene_states = cell.state.gene_states if hasattr(cell.state, 'gene_states') else {}
                    custom_color = population.custom_functions.get_cell_color(
                        cell=cell,
                        gene_states=gene_states,
                        config=population.config
                    )
                    if custom_color and '|' in custom_color:
                        # Parse new format: "interior_color|border_color"
                        interior_color, border_color = custom_color.split('|', 1)
                    elif custom_color:
                        # Legacy format: use as both interior and border
                        interior_color = custom_color
                        border_color = custom_color
                    else:
                        # Only use phenotype fallback if custom function returns None
                        enhanced_phenotype_colors = {
                            **self.phenotype_colors,
                            'growth_arrest': '#FFA500',  # Orange - different from proliferation
                            'proliferation': '#90EE90'   # Light green - different from quiescence
                        }
                        border_color = enhanced_phenotype_colors.get(phenotype, '#808080')
                        interior_color = '#D3D3D3'  # Light gray interior
            except Exception as e:
                # Fallback to enhanced phenotype colors only on error
                enhanced_phenotype_colors = {
                    **self.phenotype_colors,
                    'growth_arrest': '#FFA500',  # Orange - different from proliferation
                    'proliferation': '#90EE90'   # Light green - different from quiescence
                }
                border_color = enhanced_phenotype_colors.get(phenotype, '#808080')
                interior_color = '#D3D3D3'  # Light gray interior

            # Track colors used for legend - separate interior and border
            # Interior colors represent metabolic states
            interior_to_state = {
                'green': 'glycoATP',
                'blue': 'mitoATP',
                'violet': 'mixed',
                'lightgray': 'none',
                '#D3D3D3': 'none'
            }
            metabolic_state = interior_to_state.get(interior_color, interior_color)
            cell_colors_used[f"Interior: {metabolic_state}"] = interior_color

            # Border colors represent phenotypes
            border_to_phenotype = {
                'black': 'Necrosis',
                'red': 'Apoptosis',
                'orange': 'Growth_Arrest',
                'lightgreen': 'Proliferation',
                'gray': 'Quiescent',
                '#FFA500': 'Growth_Arrest',
                '#90EE90': 'Proliferation'
            }
            phenotype_state = border_to_phenotype.get(border_color, border_color)
            cell_colors_used[f"Border: {phenotype_state}"] = border_color

            ax.scatter(x, y, c=interior_color, s=100, alpha=0.7, edgecolors=border_color, linewidth=2)
        
        # Set up grid
        grid_size = population.grid_size
        ax.set_xlim(-0.5, grid_size[0] - 0.5)
        ax.set_ylim(-0.5, grid_size[1] - 0.5)
        
        # Add grid lines
        for i in range(grid_size[0] + 1):
            ax.axvline(i - 0.5, color='gray', alpha=0.3, linewidth=0.5)
        for i in range(grid_size[1] + 1):
            ax.axhline(i - 0.5, color='gray', alpha=0.3, linewidth=0.5)
        
        # Create dual legends with actual colors used
        if cell_colors_used:
            # Separate interior and border legend items
            interior_items = {k: v for k, v in cell_colors_used.items() if k.startswith('Interior:')}
            border_items = {k: v for k, v in cell_colors_used.items() if k.startswith('Border:')}

            # Create interior legend (metabolic states)
            if interior_items:
                interior_elements = [
                    plt.scatter([], [], c=color, s=100, label=state.replace('Interior: ', '').capitalize())
                    for state, color in sorted(interior_items.items())
                ]
                interior_legend = ax.legend(handles=interior_elements, loc='upper right',
                                          bbox_to_anchor=(1.15, 1),
                                          title='Metabolic States (Interior)')
                ax.add_artist(interior_legend)

            # Create border legend (phenotypes)
            if border_items:
                border_elements = [
                    plt.scatter([], [], c='white', s=100, edgecolors=color, linewidth=2,
                              label=state.replace('Border: ', '').capitalize())
                    for state, color in sorted(border_items.items())
                ]
                ax.legend(handles=border_elements, loc='upper right',
                         bbox_to_anchor=(1.15, 0.7),
                         title='Phenotypes (Border)')
        
        # Formatting
        ax.set_xlabel('Grid X', fontsize=self.config.label_size)
        ax.set_ylabel('Grid Y', fontsize=self.config.label_size)
        ax.set_title(title, fontsize=self.config.title_size)
        ax.set_aspect('equal')
        
        # Save if requested
        if save_path:
            self._save_figure(fig, save_path)
        
        return fig
    
    def plot_population_statistics(self, stats_history: List[Dict], 
                                 title: str = "Population Statistics", 
                                 save_path: Optional[str] = None) -> plt.Figure:
        """Plot population statistics over time"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=self.config.figsize)
        
        # Extract time series data
        times = [i for i in range(len(stats_history))]
        total_cells = [stats['total_cells'] for stats in stats_history]
        avg_ages = [stats.get('average_age', 0) for stats in stats_history]
        generations = [stats.get('generation_count', 0) for stats in stats_history]
        occupancies = [stats.get('grid_occupancy', 0) for stats in stats_history]
        
        # Plot total cells
        ax1.plot(times, total_cells, 'b-', linewidth=2)
        ax1.set_xlabel('Time Step')
        ax1.set_ylabel('Total Cells')
        ax1.set_title('Cell Count Over Time')
        ax1.grid(True, alpha=0.3)
        
        # Plot average age
        ax2.plot(times, avg_ages, 'g-', linewidth=2)
        ax2.set_xlabel('Time Step')
        ax2.set_ylabel('Average Age (hours)')
        ax2.set_title('Average Cell Age')
        ax2.grid(True, alpha=0.3)
        
        # Plot generation count
        ax3.plot(times, generations, 'r-', linewidth=2)
        ax3.set_xlabel('Time Step')
        ax3.set_ylabel('Generation Count')
        ax3.set_title('Cell Generations')
        ax3.grid(True, alpha=0.3)
        
        # Plot grid occupancy
        ax4.plot(times, [o * 100 for o in occupancies], 'm-', linewidth=2)
        ax4.set_xlabel('Time Step')
        ax4.set_ylabel('Grid Occupancy (%)')
        ax4.set_title('Grid Occupancy')
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=self.config.title_size)
        plt.tight_layout()
        
        # Save if requested
        if save_path:
            self._save_figure(fig, save_path)
        
        return fig
    
    def plot_performance_metrics(self, monitor, title: str = "Performance Metrics", 
                               save_path: Optional[str] = None) -> plt.Figure:
        """Plot performance monitoring results"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=self.config.figsize)
        
        # Get performance statistics
        stats = monitor.get_statistics()
        
        # Plot process timing statistics
        if 'profile_statistics' in stats:
            processes = list(stats['profile_statistics'].keys())
            avg_times = [stats['profile_statistics'][p].get('avg_duration', 0) * 1000 
                        for p in processes]
            
            ax1.bar(processes, avg_times, color='skyblue', alpha=0.7)
            ax1.set_ylabel('Average Time (ms)')
            ax1.set_title('Process Timing')
            ax1.tick_params(axis='x', rotation=45)
            ax1.grid(True, alpha=0.3)
        
        # Plot memory usage over time
        metrics_history = monitor.get_metrics_history(last_n=50)
        if metrics_history:
            times = range(len(metrics_history))
            memory_usage = [m['memory_mb'] for m in metrics_history]
            cpu_usage = [m['cpu_percent'] for m in metrics_history]
            
            ax2.plot(times, memory_usage, 'g-', linewidth=2)
            ax2.set_xlabel('Time')
            ax2.set_ylabel('Memory (MB)')
            ax2.set_title('Memory Usage')
            ax2.grid(True, alpha=0.3)
            
            ax3.plot(times, cpu_usage, 'r-', linewidth=2)
            ax3.set_xlabel('Time')
            ax3.set_ylabel('CPU (%)')
            ax3.set_title('CPU Usage')
            ax3.grid(True, alpha=0.3)
        
        # Plot alert summary
        alert_counts = {'Total Alerts': stats.get('total_alerts', 0)}
        ax4.bar(alert_counts.keys(), alert_counts.values(), color='orange', alpha=0.7)
        ax4.set_ylabel('Count')
        ax4.set_title('Performance Alerts')
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=self.config.title_size)
        plt.tight_layout()
        
        # Save if requested
        if save_path:
            self._save_figure(fig, save_path)
        
        return fig
    
    def plot_combined_overview(self, simulator, population, monitor, 
                             title: str = "Simulation Overview", 
                             save_path: Optional[str] = None) -> plt.Figure:
        """Create a comprehensive overview plot"""
        
        fig = plt.figure(figsize=(16, 12))
        
        # Create subplot layout
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Concentration field (large, top-left)
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        concentration = np.array(simulator.concentration.value)
        nx = simulator.mesh_manager.config.nx
        ny = simulator.mesh_manager.config.ny
        conc_2d = concentration.reshape((ny, nx))
        
        x = np.linspace(0, simulator.mesh_manager.config.size_x.micrometers, nx)
        y = np.linspace(0, simulator.mesh_manager.config.size_y.micrometers, ny)
        X, Y = np.meshgrid(x, y)
        
        im = ax1.contourf(X, Y, conc_2d, levels=20, cmap=self.concentration_cmap)
        cbar = plt.colorbar(im, ax=ax1)
        cbar.set_label(f'{simulator.substance_config.name} (mM)')
        ax1.set_title('Concentration Field')
        ax1.set_xlabel('X Position (μm)')
        ax1.set_ylabel('Y Position (μm)')
        
        # Cell population (top-right)
        ax2 = fig.add_subplot(gs[0, 2])
        positions = population.get_cell_positions()
        cell_colors_used = {}
        for (pos, phenotype) in positions:
            x, y = pos

            # Try to get custom cell color first
            interior_color = '#D3D3D3'  # default light gray interior
            border_color = '#808080'    # default gray border
            try:
                # Try to get the actual cell object to get gene states
                cell = population.get_cell_at_position(pos)
                if cell and hasattr(population, 'custom_functions') and population.custom_functions and hasattr(population.custom_functions, 'get_cell_color'):
                    gene_states = cell.state.gene_states if hasattr(cell.state, 'gene_states') else {}
                    custom_color = population.custom_functions.get_cell_color(
                        cell=cell,
                        gene_states=gene_states,
                        config=population.config
                    )
                    if custom_color and '|' in custom_color:
                        # Parse new format: "interior_color|border_color"
                        interior_color, border_color = custom_color.split('|', 1)
                    elif custom_color:
                        # Legacy format: use as both interior and border
                        interior_color = custom_color
                        border_color = custom_color
                    else:
                        # Only use phenotype fallback if custom function returns None
                        enhanced_phenotype_colors = {
                            **self.phenotype_colors,
                            'growth_arrest': '#FFA500',  # Orange - different from proliferation
                            'proliferation': '#90EE90'   # Light green - different from quiescence
                        }
                        border_color = enhanced_phenotype_colors.get(phenotype, '#808080')
                        interior_color = '#D3D3D3'  # Light gray interior
            except Exception as e:
                # Fallback to enhanced phenotype colors only on error
                enhanced_phenotype_colors = {
                    **self.phenotype_colors,
                    'growth_arrest': '#FFA500',  # Orange - different from proliferation
                    'proliferation': '#90EE90'   # Light green - different from quiescence
                }
                border_color = enhanced_phenotype_colors.get(phenotype, '#808080')
                interior_color = '#D3D3D3'  # Light gray interior

            # Track colors used for legend - separate interior and border
            # Interior colors represent metabolic states
            interior_to_state = {
                'green': 'glycoATP',
                'blue': 'mitoATP',
                'violet': 'mixed',
                'lightgray': 'none',
                '#D3D3D3': 'none'
            }
            metabolic_state = interior_to_state.get(interior_color, interior_color)
            cell_colors_used[f"Interior: {metabolic_state}"] = interior_color

            # Border colors represent phenotypes
            border_to_phenotype = {
                'black': 'Necrosis',
                'red': 'Apoptosis',
                'orange': 'Growth_Arrest',
                'lightgreen': 'Proliferation',
                'gray': 'Quiescent',
                '#FFA500': 'Growth_Arrest',
                '#90EE90': 'Proliferation'
            }
            phenotype_state = border_to_phenotype.get(border_color, border_color)
            cell_colors_used[f"Border: {phenotype_state}"] = border_color

            ax2.scatter(x, y, c=interior_color, s=50, alpha=0.7, edgecolors=border_color, linewidth=1.5)

        ax2.set_title('Cell Population')
        ax2.set_aspect('equal')

        # Add mini legend for cell colors (simplified for space)
        if cell_colors_used:
            from matplotlib.patches import Patch
            # Only show border colors (phenotypes) in mini legend to save space
            border_items = {k: v for k, v in cell_colors_used.items() if k.startswith('Border:')}
            if border_items:
                mini_legend = [Patch(facecolor='white', edgecolor=color, linewidth=1.5,
                                   label=state.replace('Border: ', ''))
                              for state, color in sorted(border_items.items())]
                ax2.legend(handles=mini_legend, loc='upper right', fontsize=6, title='Phenotypes')
        
        # Population statistics (middle-right)
        ax3 = fig.add_subplot(gs[1, 2])
        stats = population.get_population_statistics()
        phenotypes = list(stats['phenotype_counts'].keys())
        counts = list(stats['phenotype_counts'].values())
        # Use the actual colors from cell_colors_used if available, otherwise fallback to defaults
        colors = [cell_colors_used.get(p, self.phenotype_colors.get(p, '#808080')) for p in phenotypes]
        ax3.pie(counts, labels=phenotypes, colors=colors, autopct='%1.1f%%')
        ax3.set_title('Phenotype Distribution')
        
        # Performance metrics (bottom row)
        ax4 = fig.add_subplot(gs[2, 0])
        perf_stats = monitor.get_statistics()
        if 'current_metrics' in perf_stats:
            metrics = perf_stats['current_metrics']
            ax4.bar(['CPU %', 'Memory MB'], 
                   [metrics['cpu_percent'], metrics['memory_mb']], 
                   color=['red', 'blue'], alpha=0.7)
            ax4.set_title('Current Performance')
        
        ax5 = fig.add_subplot(gs[2, 1])
        sim_info = simulator.get_simulation_info()
        info_text = f"""Simulation Info:
Substance: {sim_info['substance_name']}
Converged: {sim_info['converged']}
Mean Conc: {sim_info['mean_concentration']:.2f} mM
Cells: {stats['total_cells']}
Avg Age: {stats['average_age']:.2f} h"""
        ax5.text(0.1, 0.5, info_text, transform=ax5.transAxes, fontsize=10,
                verticalalignment='center', bbox=dict(boxstyle='round', facecolor='lightgray'))
        ax5.set_xlim(0, 1)
        ax5.set_ylim(0, 1)
        ax5.axis('off')
        ax5.set_title('Simulation Summary')
        
        ax6 = fig.add_subplot(gs[2, 2])
        ax6.text(0.1, 0.5, f"""Performance Summary:
Total Profiles: {perf_stats['total_profiles']}
Total Alerts: {perf_stats['total_alerts']}
Active Profiles: {perf_stats['active_profiles']}""", 
                transform=ax6.transAxes, fontsize=10,
                verticalalignment='center', bbox=dict(boxstyle='round', facecolor='lightblue'))
        ax6.set_xlim(0, 1)
        ax6.set_ylim(0, 1)
        ax6.axis('off')
        ax6.set_title('Performance Summary')
        
        plt.suptitle(title, fontsize=16)
        
        # Save if requested
        if save_path:
            self._save_figure(fig, save_path)
        
        return fig
    
    def _save_figure(self, fig: plt.Figure, save_path: str):
        """Save figure with configured parameters"""
        fig.savefig(
            save_path,
            format=self.config.save_format,
            dpi=self.config.dpi,
            transparent=self.config.transparent,
            bbox_inches=self.config.bbox_inches
        )
        print(f"📊 Plot saved: {save_path}")
    
    def show_all(self):
        """Display all open figures"""
        plt.show()
    
    def close_all(self):
        """Close all open figures"""
        plt.close('all')
