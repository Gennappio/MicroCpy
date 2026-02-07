"""
Plot concentration heatmaps for all substances.

Creates color gradient plots showing the concentration field for each substance.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import numpy as np
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation, ISubstanceSimulator, IConfig


@register_function(
    display_name="Plot Concentration Heatmaps",
    description="Generate heatmap plots with color gradients for each substance",
    category="FINALIZATION",
    parameters=[
        {"name": "output_dir", "type": "STRING", "description": "Output directory for plots", "default": "results/plots"},
        {"name": "colormap", "type": "STRING", "description": "Matplotlib colormap name", "default": "viridis"},
        {"name": "show_cells", "type": "BOOL", "description": "Overlay cell positions on heatmap", "default": True},
    ],
    outputs=[],
    cloneable=True
)
def plot_concentration_heatmaps(
    context: Dict[str, Any],
    output_dir: str = "results/plots",
    colormap: str = "viridis",
    show_cells: bool = True,
    **kwargs
) -> bool:
    """
    Generate concentration heatmap plots for all substances.
    
    Creates one plot per substance showing the concentration field
    with color gradient visualization.
    
    Args:
        context: Workflow context containing simulator, population, config
        output_dir: Directory to save plots
        colormap: Matplotlib colormap to use
        show_cells: Whether to overlay cell positions
        
    Returns:
        True if successful
    """
    print("[FINALIZATION] Generating concentration heatmaps...")
    
    try:
        import matplotlib.pyplot as plt
        
        simulator: Optional[ISubstanceSimulator] = context.get('simulator')
        population: Optional[ICellPopulation] = context.get('population')
        config: Optional[IConfig] = context.get('config')
        
        if not simulator:
            print("[ERROR] No simulator in context")
            return False
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get domain parameters
        if config and hasattr(config, 'domain'):
            nx = config.domain.nx
            ny = config.domain.ny
            size_x = config.domain.size_x.micrometers if hasattr(config.domain.size_x, 'micrometers') else config.domain.size_x
            size_y = config.domain.size_y.micrometers if hasattr(config.domain.size_y, 'micrometers') else config.domain.size_y
        else:
            # Fallback: try to get from substances dict
            substances = context.get('substances', {})
            if not substances:
                print("[WARNING] No substances found")
                return True
            # Try to infer from simulator state
            nx, ny = 25, 25
            size_x, size_y = 500.0, 500.0
        
        # Get cell positions for overlay
        cell_positions = []
        if show_cells and population:
            for cell_id, cell in population.state.cells.items():
                pos = cell.state.position
                cell_positions.append((pos[0], pos[1]))
        
        # Get all substances
        substances_state = getattr(simulator.state, 'substances', {}) if hasattr(simulator, 'state') else {}
        
        if not substances_state:
            print("[WARNING] No substance states in simulator")
            return True
        
        # Create coordinate arrays
        x = np.linspace(0, size_x, nx)
        y = np.linspace(0, size_y, ny)
        X, Y = np.meshgrid(x, y)
        
        # Plot each substance
        for substance_name, substance in substances_state.items():
            concentrations = substance.concentrations
            
            # Handle 3D data by taking middle slice
            if len(concentrations.shape) == 3:
                middle_z = concentrations.shape[0] // 2
                plot_data = concentrations[middle_z, :, :]
            else:
                plot_data = concentrations
            
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Plot heatmap
            im = ax.contourf(X, Y, plot_data, levels=20, cmap=colormap)
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label(f'{substance_name} Concentration')
            
            # Overlay cells
            if cell_positions:
                cell_x = [p[0] * size_x / nx for p in cell_positions]
                cell_y = [p[1] * size_y / ny for p in cell_positions]
                ax.scatter(cell_x, cell_y, c='white', s=30, edgecolors='black', 
                          linewidth=0.5, alpha=0.8, label='Cells')
            
            ax.set_xlabel('X (μm)')
            ax.set_ylabel('Y (μm)')
            ax.set_title(f'{substance_name} Concentration Field')
            ax.set_aspect('equal')
            
            # Save plot
            plot_path = output_path / f"{substance_name}_heatmap.png"
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"   [+] {substance_name}: {plot_path.name}")
        
        print(f"[FINALIZATION] Generated {len(substances_state)} heatmaps in {output_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to generate heatmaps: {e}")
        import traceback
        traceback.print_exc()
        return False

