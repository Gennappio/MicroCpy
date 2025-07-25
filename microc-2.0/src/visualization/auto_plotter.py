"""
Automatic Plotting Module for MicroC 2.0

Generates publication-quality plots automatically:
- Substance concentration heatmaps
- Time series plots
- Cell population dynamics
- Gene network activity
- Multi-substance comparisons

All plots are saved to the plots_dir specified in YAML configuration.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Set matplotlib style for publication quality
plt.style.use('default')
plt.rcParams.update({
    'font.size': 12,
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 12,
    'figure.titlesize': 18,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1
})

class AutoPlotter:
    """Automatic plotting for MicroC simulations"""
    
    def __init__(self, config, plots_dir: Path):
        self.config = config
        self.plots_dir = Path(plots_dir)
        self.plots_dir.mkdir(parents=True, exist_ok=True)

    def _get_threshold_for_substance(self, substance_name):
        """Get the threshold value for a substance if it has a gene network association."""
        # Mapping from substance names to gene network input nodes
        if not hasattr(self.config, 'associations') or not hasattr(self.config, 'thresholds'):
            return None

        # Check if substance has an association with a gene network input
        if substance_name in self.config.associations:
            gene_input_name = self.config.associations[substance_name]

            # Check if that gene input has a threshold defined
            if gene_input_name in self.config.thresholds:
                threshold_config = self.config.thresholds[gene_input_name]
                return threshold_config.threshold

        return None
        
        # Create subdirectories
        (self.plots_dir / "heatmaps").mkdir(exist_ok=True)
        (self.plots_dir / "timeseries").mkdir(exist_ok=True)
        (self.plots_dir / "summary").mkdir(exist_ok=True)
        
        print(f"📊 Plots will be saved to: {self.plots_dir}")
    
    def plot_substance_heatmap(self, substance_name: str, concentrations: np.ndarray,
                              cell_positions: List[Tuple[int, int]], time_point: float,
                              config_name: str = "unknown", population=None, title_suffix: str = "",
                              is_initial: bool = False, is_final: bool = False):
        """Plot concentration heatmap for a single substance with detailed debugging"""

        # DEBUG: Print actual concentration values
        # print(f"🔍 DEBUG {substance_name} heatmap:")
        # print(f"   Array shape: {concentrations.shape}")
        # print(f"   Array dtype: {concentrations.dtype}")
        # print(f"   Raw min: {concentrations.min():.8f}")
        # print(f"   Raw max: {concentrations.max():.8f}")
        # print(f"   Raw mean: {concentrations.mean():.8f}")
        # print(f"   Sample values: {concentrations.flat[:5]}")

        fig, ax = plt.subplots(figsize=(12, 10))

        # Create heatmap with explicit vmin/vmax to fix colorbar
        vmin = concentrations.min()
        vmax = concentrations.max()

        # Fix for uniform data: add small epsilon to prevent vmin=vmax colormap issues
        if vmax - vmin < 1e-10:  # Essentially uniform data
            epsilon = max(abs(vmin) * 1e-6, 1e-10)  # Small relative epsilon
            vmin = vmin - epsilon
            vmax = vmax + epsilon
            print(f"   ⚠️  Uniform data detected, adding epsilon: ±{epsilon:.2e}")

        # Additional debugging for the plotting values
        print(f"   Plot vmin: {vmin:.8f}")
        print(f"   Plot vmax: {vmax:.8f}")

        im = ax.imshow(concentrations, cmap='viridis', origin='lower',
                      extent=[0, self.config.domain.size_x.value,
                             0, self.config.domain.size_y.value],
                      vmin=vmin, vmax=vmax)

        # Add threshold isoline if this substance has a gene network association
        threshold_value = self._get_threshold_for_substance(substance_name)
        if threshold_value is not None:
            # Create coordinate grids for contour
            x_coords = np.linspace(0, self.config.domain.size_x.value, concentrations.shape[1])
            y_coords = np.linspace(0, self.config.domain.size_y.value, concentrations.shape[0])
            X, Y = np.meshgrid(x_coords, y_coords)

            # Add threshold contour line
            threshold_contour = ax.contour(X, Y, concentrations, levels=[threshold_value],
                                         colors=['red'], linewidths=2, linestyles='-')
            # Add threshold label
            ax.clabel(threshold_contour, inline=True, fontsize=10, fmt=f'Threshold: {threshold_value:.3g}')
            print(f"   🎯 Added threshold isoline at {threshold_value:.3g} mM for {substance_name}")

        # Add colorbar with FORCED correct range
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label(f'{substance_name} Concentration (mM)', rotation=270, labelpad=20)

        # FORCE the colorbar to show the correct range using the mappable
        im.set_clim(vmin, vmax)

        # Set explicit ticks to ensure correct scaling (always set ticks, even for uniform data)
        # Create 5 evenly spaced ticks
        tick_values = np.linspace(vmin, vmax, 5)
        cbar.set_ticks(tick_values)
        cbar.set_ticklabels([f'{val:.6f}' for val in tick_values])

        # Add concentration range text on colorbar
        cbar.ax.text(1.15, 0.5, f'ACTUAL\nRange:\n{vmin:.6f}\nto\n{vmax:.6f}\nmM',
                    transform=cbar.ax.transAxes, va='center', fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.9))

        # Mark cell positions with colors
        cell_colors_used = {}
        if cell_positions and population:
            # Use biological cell diameter (cell_height parameter), not grid spacing
            cell_diameter = self.config.domain.cell_height.value  # 20 μm for biological cells
            grid_spacing = self.config.domain.size_x.value / self.config.domain.nx  # 10 μm for FiPy grid

            # Get cell data with phenotypes and colors
            cell_data = population.get_cell_positions()


            cell_counter = 0
            for (x, y), phenotype in cell_data:
                cell_counter += 1
                # Convert grid coordinates to physical coordinates
                phys_x = (x + 0.5) * grid_spacing
                phys_y = (y + 0.5) * grid_spacing

                # Get cell color from custom function if available
                interior_color = 'lightgray'  # default interior
                border_color = 'gray'  # default border
                try:
                    # Try to get the actual cell object to get gene states
                    cell = population.get_cell_at_position((x, y))
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
                            phenotype_color_map = {
                                'Proliferation': 'lightgreen',
                                'Quiescence': 'gray',
                                'Hypoxia': 'orange',
                                'Necrosis': 'black',
                                'Apoptosis': 'red',
                                'growth_arrest': 'orange',
                                'proliferation': 'lightgreen'
                            }
                            border_color = phenotype_color_map.get(phenotype, 'gray')
                            interior_color = 'lightgray'
                    else:
                        # Use phenotype-based colors as fallback
                        phenotype_color_map = {
                            'Proliferation': 'lightgreen',
                            'Quiescence': 'gray',
                            'Hypoxia': 'orange',
                            'Necrosis': 'black',
                            'Apoptosis': 'red',
                            'Growth_Arrest': 'orange',
                            'growth_arrest': 'orange',
                            'proliferation': 'lightgreen'
                        }
                        border_color = phenotype_color_map.get(phenotype, 'gray')
                        interior_color = 'lightgray'
                except Exception as e:
                    # Fallback to phenotype-based colors only on error
                    phenotype_color_map = {
                        'Proliferation': 'lightgreen',
                        'Quiescence': 'gray',
                        'Hypoxia': 'orange',
                        'Necrosis': 'black',
                        'Apoptosis': 'red',
                        'growth_arrest': 'orange',
                        'proliferation': 'lightgreen'
                    }
                    border_color = phenotype_color_map.get(phenotype, 'gray')
                    interior_color = 'lightgray'

                # Track colors used for legend - separate interior and border legends
                # Interior colors represent metabolic states
                interior_to_state = {
                    'green': 'glycoATP',
                    'blue': 'mitoATP',
                    'violet': 'mixed',
                    'lightgray': 'none'
                }
                metabolic_state = interior_to_state.get(interior_color, interior_color)
                cell_colors_used[f"Interior: {metabolic_state}"] = interior_color

                # Border colors represent phenotypes
                border_to_phenotype = {
                    'black': 'Necrosis',
                    'red': 'Apoptosis',
                    'orange': 'Growth_Arrest',
                    'lightgreen': 'Proliferation',
                    'gray': 'Quiescent'
                }
                phenotype_state = border_to_phenotype.get(border_color, border_color)
                cell_colors_used[f"Border: {phenotype_state}"] = border_color

                # Draw cell with interior and border colors
                circle = patches.Circle((phys_x, phys_y), cell_diameter/2,
                                      facecolor=interior_color, edgecolor=border_color,
                                      alpha=0.8, linewidth=2, fill=True)
                ax.add_patch(circle)

        elif cell_positions:
            # Fallback for when population is not available
            cell_diameter = self.config.domain.cell_height.value  # Biological cell diameter
            grid_spacing = self.config.domain.size_x.value / self.config.domain.nx  # Grid spacing
            for x, y in cell_positions:
                phys_x = (x + 0.5) * grid_spacing
                phys_y = (y + 0.5) * grid_spacing
                circle = patches.Circle((phys_x, phys_y), cell_diameter/2,
                                      color='red', alpha=0.7, linewidth=2, fill=False)
                ax.add_patch(circle)
                cell_colors_used['Cell'] = 'red'

        # Enhanced title with detailed information
        domain_info = f"{self.config.domain.size_x.value}×{self.config.domain.size_y.value} {self.config.domain.size_x.unit}"
        grid_info = f"{self.config.domain.nx}×{self.config.domain.ny}"

        # Get accurate cell count from population if available, otherwise use cell_positions
        cell_count = 0
        if population:
            pop_stats = population.get_population_statistics()
            cell_count = pop_stats['total_cells']

        elif cell_positions:
            cell_count = len(cell_positions)
            print(f"🔍 TITLE DEBUG: Using cell_positions count: {cell_count}")

        detailed_title = (f'{substance_name} Distribution at t = {time_point:.3f} {title_suffix}\n'
                         f'Config: {config_name} | Domain: {domain_info} | Grid: {grid_info}\n'
                         f'Range: {vmin:.6f} - {vmax:.6f} mM | Mean: {concentrations.mean():.6f} mM | '
                         f'Cells: {cell_count}')

        ax.set_title(detailed_title, fontsize=11, pad=20)

        # Formatting
        ax.set_xlabel(f'X Position ({self.config.domain.size_x.unit})')
        ax.set_ylabel(f'Y Position ({self.config.domain.size_y.unit})')

        # Add FiPy mesh grid
        nx, ny = self.config.domain.nx, self.config.domain.ny
        domain_x = self.config.domain.size_x.micrometers
        domain_y = self.config.domain.size_y.micrometers

        # Create grid lines at FiPy mesh boundaries
        x_grid = np.linspace(0, domain_x, nx + 1)
        y_grid = np.linspace(0, domain_y, ny + 1)

        # Add vertical grid lines
        for x in x_grid:
            ax.axvline(x, color='white', alpha=0.5, linewidth=0.5)

        # Add horizontal grid lines
        for y in y_grid:
            ax.axhline(y, color='white', alpha=0.5, linewidth=0.5)

        # Add coordinate grid (lighter)
        ax.grid(True, alpha=0.2, color='gray', linestyle='--')

        # Add dual cell legends if cells are present - ENHANCED
        if cell_colors_used:
            from matplotlib.patches import Patch, Circle

            # Separate interior and border legend items
            interior_items = {k: v for k, v in cell_colors_used.items() if k.startswith('Interior:')}
            border_items = {k: v for k, v in cell_colors_used.items() if k.startswith('Border:')}

            # Create interior legend (metabolic states)
            if interior_items:
                interior_elements = [Patch(facecolor=color, label=state.replace('Interior: ', ''),
                                         edgecolor='gray', linewidth=0.5)
                                   for state, color in sorted(interior_items.items())]

                interior_legend = ax.legend(handles=interior_elements, loc='upper left',
                                          bbox_to_anchor=(0, 1),
                                          title='🔋 Metabolic States (Interior)', fontsize=9,
                                          title_fontsize=10, frameon=True, fancybox=True,
                                          shadow=True, facecolor='white', edgecolor='black',
                                          framealpha=0.9)
                interior_legend.get_title().set_fontweight('bold')

                # Add the interior legend to the plot
                ax.add_artist(interior_legend)

            # Create border legend (phenotypes)
            if border_items:
                border_elements = [Patch(facecolor='white', label=state.replace('Border: ', ''),
                                       edgecolor=color, linewidth=2)
                                 for state, color in sorted(border_items.items())]

                border_legend = ax.legend(handles=border_elements, loc='upper left',
                                        bbox_to_anchor=(0, 0.7),
                                        title='🧬 Phenotypes (Border)', fontsize=9,
                                        title_fontsize=10, frameon=True, fancybox=True,
                                        shadow=True, facecolor='white', edgecolor='black',
                                        framealpha=0.9)
                border_legend.get_title().set_fontweight('bold')

            print(f"🎨 Dual legends created - Interior: {len(interior_items)}, Border: {len(border_items)}")

        # Add text box with additional details including grid info
        grid_spacing = domain_x / nx
        cell_diameter = self.config.domain.cell_height.value
        info_text = (f'Simulation Details:\n'
                    f'• Config: {config_name}\n'
                    f'• Time: {time_point:.3f}\n'
                    f'• Substance: {substance_name}\n'
                    f'• FiPy Grid: {nx}×{ny} cells\n'
                    f'• Grid Spacing: {grid_spacing:.1f} μm\n'
                    f'• Cell Diameter: {cell_diameter:.1f} μm\n'
                    f'• Domain: {domain_x:.0f}×{domain_y:.0f} μm\n'
                    f'• Min: {vmin:.6f} mM\n'
                    f'• Max: {vmax:.6f} mM\n'
                    f'• Mean: {concentrations.mean():.6f} mM\n'
                    f'• Std: {concentrations.std():.6f} mM\n'
                    f'• Cells: {cell_count}')

        ax.text(0.02, 0.85, info_text, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.5",
                facecolor="white", alpha=0.9))

        # Save plot with unique filename to avoid overwriting
        if is_initial:
            filename = f"{substance_name}_heatmap_t{time_point:.3f}_INITIAL.png"
        elif is_final:
            filename = f"{substance_name}_heatmap_t{time_point:.3f}_FINAL.png"
        else:
            filename = f"{substance_name}_heatmap_t{time_point:.3f}.png"

        filepath = self.plots_dir / "heatmaps" / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        return filepath
    
    def plot_substance_timeseries(self, substance_data: Dict[str, Dict[str, List[float]]], 
                                 time_points: List[float]):
        """Plot time series for all substances"""
        
        # Determine number of subplots needed
        substances = list(substance_data.keys())
        n_substances = len(substances)
        
        if n_substances == 0:
            return None
        
        # Create subplots
        cols = min(3, n_substances)
        rows = (n_substances + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows))

        # Handle different subplot configurations
        if n_substances == 1:
            axes = [axes]
        elif rows == 1 and cols > 1:
            axes = [axes[i] for i in range(cols)]
        elif rows > 1 and cols == 1:
            axes = [axes[i] for i in range(rows)]
        elif rows > 1 and cols > 1:
            axes = [axes[i // cols, i % cols] for i in range(rows * cols)]

        # Plot each substance
        for i, substance in enumerate(substances):
            ax = axes[i]
            
            data = substance_data[substance]
            
            # Plot min, max, mean
            if 'min' in data and len(data['min']) > 0:
                ax.plot(time_points[:len(data['min'])], data['min'], 
                       label='Min', color='blue', alpha=0.7)
            if 'max' in data and len(data['max']) > 0:
                ax.plot(time_points[:len(data['max'])], data['max'], 
                       label='Max', color='red', alpha=0.7)
            if 'mean' in data and len(data['mean']) > 0:
                ax.plot(time_points[:len(data['mean'])], data['mean'], 
                       label='Mean', color='green', linewidth=2)
            
            ax.set_xlabel('Time')
            ax.set_ylabel(f'{substance} (mM)')
            ax.set_title(f'{substance} Concentration')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # Hide empty subplots
        for i in range(n_substances, rows * cols):
            if i < len(axes):
                axes[i].set_visible(False)
        
        plt.tight_layout()
        
        # Save plot
        filepath = self.plots_dir / "timeseries" / "substance_timeseries.png"
        plt.savefig(filepath)
        plt.close()
        
        return filepath
    
    def plot_simulation_summary(self, substance_data: Dict[str, Dict[str, List[float]]], 
                               cell_counts: List[Dict[str, int]], 
                               time_points: List[float]):
        """Create a comprehensive summary plot"""
        
        fig = plt.figure(figsize=(16, 12))
        
        # Create grid layout
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. Key substances overview (top left)
        ax1 = fig.add_subplot(gs[0, 0])
        key_substances = ['Oxygen', 'Glucose', 'Lactate']
        colors = ['blue', 'green', 'orange']
        
        for substance, color in zip(key_substances, colors):
            if substance in substance_data and 'mean' in substance_data[substance]:
                data = substance_data[substance]['mean']
                ax1.plot(time_points[:len(data)], data, 
                        label=substance, color=color, linewidth=2)
        
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Concentration (mM)')
        ax1.set_title('Essential Metabolites')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Cell population (top middle)
        ax2 = fig.add_subplot(gs[0, 1])
        if cell_counts:
            total_cells = []
            for count_data in cell_counts:
                try:
                    if isinstance(count_data, dict):
                        # Handle nested dict structure
                        total = 0
                        for value in count_data.values():
                            if isinstance(value, (int, float)):
                                total += value
                            elif isinstance(value, dict):
                                total += sum(v for v in value.values() if isinstance(v, (int, float)))
                        total_cells.append(total)
                    elif isinstance(count_data, (int, float)):
                        total_cells.append(count_data)
                    else:
                        total_cells.append(0)
                except Exception:
                    total_cells.append(0)

            if total_cells:
                ax2.plot(time_points[:len(total_cells)], total_cells,
                        color='purple', linewidth=3, marker='o')
                ax2.set_xlabel('Time')
                ax2.set_ylabel('Total Cells')
                ax2.set_title('Cell Population')
                ax2.grid(True, alpha=0.3)
        
        # 3. Substance gradients (top right)
        ax3 = fig.add_subplot(gs[0, 2])
        if 'Oxygen' in substance_data:
            oxygen_data = substance_data['Oxygen']
            if 'min' in oxygen_data and 'max' in oxygen_data:
                gradients = []
                for i in range(len(oxygen_data['min'])):
                    if i < len(oxygen_data['max']):
                        gradient = oxygen_data['max'][i] - oxygen_data['min'][i]
                        gradients.append(gradient)
                
                ax3.plot(time_points[:len(gradients)], gradients, 
                        color='red', linewidth=2)
                ax3.set_xlabel('Time')
                ax3.set_ylabel('Oxygen Gradient (mM)')
                ax3.set_title('Oxygen Depletion')
                ax3.grid(True, alpha=0.3)
        
        # 4. Growth factors (bottom span)
        ax4 = fig.add_subplot(gs[1, :])
        growth_factors = ['FGF', 'TGFA', 'HGF']
        colors = ['cyan', 'magenta', 'yellow']
        
        for substance, color in zip(growth_factors, colors):
            if substance in substance_data and 'mean' in substance_data[substance]:
                data = substance_data[substance]['mean']
                if any(x > 1e-10 for x in data):  # Only plot if non-zero
                    ax4.plot(time_points[:len(data)], data, 
                            label=substance, color=color, linewidth=2)
        
        ax4.set_xlabel('Time')
        ax4.set_ylabel('Concentration (mM)')
        ax4.set_title('Growth Factors')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        if any('FGF' in substance_data or 'TGFA' in substance_data or 'HGF' in substance_data for _ in [1]):
            ax4.set_yscale('log')
        
        # 5. Simulation info (bottom)
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis('off')
        
        # Add simulation information
        info_text = f"""
Simulation Summary:
• Domain: {self.config.domain.size_x.value}×{self.config.domain.size_y.value} {self.config.domain.size_x.unit}
• Grid: {self.config.domain.nx}×{self.config.domain.ny} cells
• Substances: {len(self.config.substances)}
• Simulation time: {time_points[-1] if time_points else 0:.3f}
• Time steps: {len(time_points)}
        """
        
        ax5.text(0.1, 0.5, info_text, fontsize=12, verticalalignment='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))
        
        # Main title
        fig.suptitle('MicroC 2.0 Simulation Summary', fontsize=20, fontweight='bold')
        
        # Save plot
        filepath = self.plots_dir / "summary" / "simulation_summary.png"
        plt.savefig(filepath)
        plt.close()
        
        return filepath

    def plot_initial_state_summary(self, population, simulator):
        """Plot TRUE initial state of the simulation (before any gene network updates)"""

        # First create the 4-panel summary
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Initial cell placement (top-left) - show raw placement without gene network colors
        cell_data = population.get_cell_positions()
        cell_colors_used = {}  # Initialize outside the if block
        if cell_data:
            for pos, phenotype in cell_data:
                x, y = pos

                # Use simple phenotype-based colors (no gene network evaluation)
                # This shows the TRUE initial state before any processing
                phenotype_color_map = {
                    'Proliferation': 'lightgreen',
                    'Quiescence': 'lightblue',
                    'Hypoxia': 'orange',
                    'Necrosis': 'black',
                    'Apoptosis': 'red',
                    'growth_arrest': 'orange',
                    'proliferation': 'lightgreen',
                    'normal': 'lightgray'
                }
                cell_color = phenotype_color_map.get(phenotype, 'lightgray')

                # Track colors for legend (use phenotype names for initial state)
                cell_colors_used[phenotype] = cell_color

                ax1.scatter(x, y, c=cell_color, s=100, alpha=0.8, edgecolors='black', linewidth=0.5)

        ax1.set_title('Initial Cell Placement', fontsize=14, fontweight='bold')
        ax1.set_xlabel('X Position (grid units)')
        ax1.set_ylabel('Y Position (grid units)')
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal')

        # Add cell legend
        if cell_colors_used:
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor=color, label=state)
                             for state, color in sorted(cell_colors_used.items())]
            ax1.legend(handles=legend_elements, loc='upper right', fontsize=8)

        # 2. TRUE Initial substance concentrations (top-right) - from config, not simulator
        substance_names = list(self.config.substances.keys())[:4]  # Show first 4 substances
        substance_values = []
        substance_labels = []

        for substance in substance_names:
            if substance in self.config.substances:
                # Use TRUE initial value from configuration (not current simulator state)
                initial_value = self.config.substances[substance].initial_value.value
                substance_values.append(initial_value)
                substance_labels.append(f"{substance}\n{initial_value:.4f} mM")

        if substance_values:
            bars = ax2.bar(range(len(substance_values)), substance_values,
                          color=['skyblue', 'lightgreen', 'salmon', 'gold'][:len(substance_values)])
            ax2.set_title('TRUE Initial Substance Concentrations\n(From Configuration)', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Concentration (mM)')
            ax2.set_xticks(range(len(substance_labels)))
            ax2.set_xticklabels([s.split('\n')[0] for s in substance_labels], rotation=45)

            # Add value labels on bars
            for bar, label in zip(bars, substance_labels):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.4f}', ha='center', va='bottom', fontsize=8)

        # 3. Initial population statistics (bottom-left)
        pop_stats = population.get_population_statistics()
        phenotype_counts = pop_stats.get('phenotype_counts', {})

        if phenotype_counts:
            phenotypes = list(phenotype_counts.keys())
            counts = list(phenotype_counts.values())
            colors = [cell_colors_used.get(p, 'gray') for p in phenotypes]

            ax3.pie(counts, labels=phenotypes, colors=colors, autopct='%1.1f%%', startangle=90)
            ax3.set_title('Initial Cell Phenotype Distribution', fontsize=14, fontweight='bold')

        # 4. Simulation configuration info (bottom-right)
        # Get gene network info safely
        gene_network_info = "Unknown"
        try:
            if hasattr(self.config, 'gene_network') and self.config.gene_network:
                if hasattr(self.config.gene_network, 'nodes') and self.config.gene_network.nodes:
                    gene_network_info = f"{len(self.config.gene_network.nodes)} nodes"
                else:
                    gene_network_info = "Minimal network"
            else:
                gene_network_info = "No network"
        except:
            gene_network_info = "Network info unavailable"

        config_info = f"""Initial Simulation Configuration:

• Domain: {population.grid_size[0]}×{population.grid_size[1]} grid
• Total Cells: {pop_stats['total_cells']}
• Substances: {len(self.config.substances)}
• Gene Network: {gene_network_info}

Substance Initial Values:
"""

        # Use TRUE initial values from configuration
        for substance in list(self.config.substances.keys())[:3]:  # Show first 3
            if substance in self.config.substances:
                initial_value = self.config.substances[substance].initial_value.value
                config_info += f"• {substance}: {initial_value:.4f} mM\n"

        ax4.text(0.1, 0.5, config_info, fontsize=11, verticalalignment='center',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.7))
        ax4.set_xlim(0, 1)
        ax4.set_ylim(0, 1)
        ax4.axis('off')
        ax4.set_title('Configuration Summary', fontsize=14, fontweight='bold')

        # Main title
        fig.suptitle('TRUE Initial State Summary (t=0.000)\nBefore Any Gene Network or Diffusion Updates', fontsize=16, fontweight='bold')
        plt.tight_layout()

        # Save summary plot
        filepath = self.plots_dir / "summary" / "initial_state_summary.png"
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        # Now create individual heatmaps for ALL substances showing true initial state
        self._plot_all_initial_substance_heatmaps(population)

        return filepath

    def _plot_all_initial_substance_heatmaps(self, population):
        """Create individual heatmaps for ALL substances showing true initial state"""

        # Get cell positions for overlay
        cell_positions = []
        if population:
            cell_data = population.get_cell_positions()
            cell_positions = [pos for pos, phenotype in cell_data]

        # Get config name
        config_name = self.plots_dir.name if hasattr(self.plots_dir, 'name') else "unknown"

        print(f"📊 Creating initial state heatmaps for all {len(self.config.substances)} substances...")

        for substance_name, substance_config in self.config.substances.items():
            # Create TRUE initial concentration field (uniform)
            nx, ny = self.config.domain.nx, self.config.domain.ny
            initial_value = substance_config.initial_value.value
            initial_concentrations = np.full((ny, nx), initial_value)

            # Create the heatmap
            plot_path = self.plot_substance_heatmap(
                substance_name,
                initial_concentrations,
                cell_positions,
                0.0,  # time = 0
                config_name,
                population,
                title_suffix="(TRUE Initial State - Uniform)",
                is_initial=True
            )

            print(f"   ✅ {substance_name} initial heatmap: {plot_path.name}")

    def generate_all_plots(self, results: Dict[str, Any], simulator=None, population=None):
        """Generate all plots automatically"""

        print(f"📊 Generating plots...")
        generated_plots = []

        time_points = results.get('time', [])
        substance_stats = results.get('substance_stats', [])
        cell_counts = results.get('cell_counts', [])

        # 1. Substance time series
        if substance_stats and time_points:
            substance_data = {}
            for substance in self.config.substances.keys():
                substance_data[substance] = {
                    'min': [stats.get(substance, {}).get('min', 0) for stats in substance_stats],
                    'max': [stats.get(substance, {}).get('max', 0) for stats in substance_stats],
                    'mean': [stats.get(substance, {}).get('mean', 0) for stats in substance_stats]
                }

            plot_path = self.plot_substance_timeseries(substance_data, time_points)
            if plot_path:
                generated_plots.append(plot_path)
                print(f"   ✅ Substance time series: {plot_path.name}")

        # 2. Initial and final concentration heatmaps
        if simulator:
            # Get actual cell positions from the population
            cell_positions = []
            if population:
                cell_data = population.get_cell_positions()
                cell_positions = [pos for pos, phenotype in cell_data]

            # Get config name from plots directory
            config_name = self.plots_dir.name if hasattr(self.plots_dir, 'name') else "unknown"

            # Plot ALL substances (not just key ones)
            all_substances = list(self.config.substances.keys())

            # SKIP initial state plots here - they were already created by generate_initial_plots()
            # Creating them again would overwrite the true initial state with final state data
            print(f"   ⏭️  Skipping initial state plots (already created before simulation)")

            # Note: Initial plots are created by generate_initial_plots() before simulation starts
            # This prevents overwriting true initial state with final state data

            # Plot final state - use current time from simulator or estimate from config
            if time_points:
                final_time = time_points[-1]
            else:
                # If no time series data, estimate final time from current simulation state
                # This happens when save_data_interval is larger than total steps
                final_time = getattr(simulator, 'current_time', 0.5)  # Default fallback

            for substance in all_substances:
                if substance in simulator.state.substances:
                    concentrations = simulator.state.substances[substance].concentrations

                    plot_path = self.plot_substance_heatmap(
                        substance, concentrations, cell_positions, final_time, config_name, population,
                        is_final=True
                    )
                    generated_plots.append(plot_path)
                    print(f"   ✅ {substance} final heatmap: {plot_path.name}")
        
        # 3. SKIP initial state summary plot - already created by generate_initial_plots()
        # Creating it again would overwrite the true initial state with final state data
        print(f"   ⏭️  Skipping initial state summary (already created before simulation)")

        # 4. Final simulation summary plot
        if substance_stats and time_points:
            plot_path = self.plot_simulation_summary(substance_data, cell_counts, time_points)
            if plot_path:
                generated_plots.append(plot_path)
                print(f"   ✅ Final simulation summary: {plot_path.name}")
        
        print(f"📊 Generated {len(generated_plots)} plots in {self.plots_dir}")
        return generated_plots
