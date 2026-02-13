"""
Generate Cell Position Plots

Visualizes cell positions in 2D/3D space with population count overlays.
Creates scatter plots showing spatial distribution of cells, colored by phenotype,
with population size displayed in the title.

Example:
    This function can be used in workflows like:
    - Population growth analysis
    - Spatial pattern visualization
    - Phenotype distribution mapping

Notes:
    - Automatically detects 2D vs 3D based on cell positions
    - Saves plots to results/plots/ directory
    - Creates both per-phenotype and combined visualizations
"""

from typing import Dict, Any, Optional
import os
from collections import Counter
from src.workflow.decorators import register_function

# Conditionally import matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for server environments
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[WARNING] matplotlib not available - plots will not be generated")


@register_function(
    display_name="Generate Cell Plots",
    description="Generate spatial plots of cell positions with population count labels",
    category="FINALIZATION",
    parameters=[
        {
            "name": "output_dir",
            "type": "STRING",
            "description": "Output directory for plots (relative to workspace root)",
            "default": "results/plots"
        },
        {
            "name": "plot_size",
            "type": "FLOAT",
            "description": "Figure size in inches",
            "default": 10.0,
            "min_value": 5.0,
            "max_value": 20.0
        },
        {
            "name": "marker_size",
            "type": "FLOAT",
            "description": "Size of cell markers in plot",
            "default": 50.0,
            "min_value": 10.0,
            "max_value": 200.0
        },
        {
            "name": "show_phenotypes",
            "type": "BOOL",
            "description": "Color cells by phenotype",
            "default": True
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def generate_cell_plots(
    context: Dict[str, Any] = None,
    output_dir: str = "results/plots",
    plot_size: float = 10.0,
    marker_size: float = 50.0,
    show_phenotypes: bool = True,
    **kwargs
) -> bool:
    """
    Generate spatial visualization of cell positions with population count.
    
    Creates scatter plots showing cell positions in 2D or 3D space,
    colored by phenotype (if enabled), with total population count
    displayed in the plot title.
    
    Args:
        context: Workflow context containing population
        output_dir: Directory to save plots (relative to workspace root)
        plot_size: Figure size in inches
        marker_size: Size of cell markers
        show_phenotypes: Whether to color cells by phenotype
        **kwargs: Additional parameters (for forward compatibility)
        
    Returns:
        True if successful, False otherwise
    """
    # =========================================================================
    # CHECK DEPENDENCIES
    # =========================================================================
    if not MATPLOTLIB_AVAILABLE:
        print("[ERROR] [generate_cell_plots] matplotlib not available - cannot generate plots")
        print("       Install with: pip install matplotlib")
        return False
    
    # =========================================================================
    # VALIDATE CONTEXT
    # =========================================================================
    if not context:
        print("[ERROR] [generate_cell_plots] No context provided")
        return False
    
    # =========================================================================
    # GET REQUIRED ITEMS FROM CONTEXT
    # =========================================================================
    population = context.get('population')
    if population is None:
        print("[ERROR] [generate_cell_plots] No population in context")
        return False
    
    config = context.get('config')
    
    # =========================================================================
    # EXTRACT CELL DATA
    # =========================================================================
    cells = population.state.cells
    num_cells = len(cells)
    
    if num_cells == 0:
        print("[WARNING] [generate_cell_plots] No cells to plot")
        return True
    
    print(f"[CELL_PLOTS] Generating plots for {num_cells} cells")
    
    # Collect cell positions and phenotypes
    positions = []
    phenotypes = []
    is_3d = None
    
    for cell_id, cell in cells.items():
        pos = cell.state.position
        positions.append(pos)
        
        # Detect dimensionality from first cell
        if is_3d is None:
            is_3d = (len(pos) == 3)
        
        # Get phenotype if available
        phenotype = getattr(cell.state, 'phenotype', 'Unknown')
        phenotypes.append(phenotype)
    
    # Count phenotypes
    phenotype_counts = Counter(phenotypes)
    
    # =========================================================================
    # CREATE OUTPUT DIRECTORY
    # =========================================================================
    os.makedirs(output_dir, exist_ok=True)
    
    # =========================================================================
    # GENERATE PLOTS
    # =========================================================================
    print(f"[CELL_PLOTS] Generating {'3D' if is_3d else '2D'} scatter plot")
    
    # Define colors for phenotypes
    phenotype_colors = {
        'Proliferation': '#2ecc71',  # Green
        'Apoptosis': '#e74c3c',       # Red
        'Necrosis': '#8e44ad',        # Purple
        'Growth_Arrest': '#f39c12',   # Orange
        'Quiescent': '#95a5a6',       # Gray
        'Unknown': '#34495e'           # Dark gray
    }
    
    # Create figure
    fig = plt.figure(figsize=(plot_size, plot_size))
    
    if is_3d:
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot cells by phenotype
        if show_phenotypes:
            for phenotype in set(phenotypes):
                # Filter positions for this phenotype
                pheno_positions = [pos for pos, ph in zip(positions, phenotypes) if ph == phenotype]
                if pheno_positions:
                    xs, ys, zs = zip(*pheno_positions)
                    color = phenotype_colors.get(phenotype, '#34495e')
                    ax.scatter(xs, ys, zs, c=color, s=marker_size, 
                              label=f"{phenotype} ({phenotype_counts[phenotype]})",
                              alpha=0.7, edgecolors='black', linewidth=0.5)
            ax.legend(loc='upper right', fontsize=8)
        else:
            xs, ys, zs = zip(*positions)
            ax.scatter(xs, ys, zs, c='#3498db', s=marker_size, alpha=0.7, 
                      edgecolors='black', linewidth=0.5)
        
        ax.set_xlabel('X Position', fontsize=10)
        ax.set_ylabel('Y Position', fontsize=10)
        ax.set_zlabel('Z Position', fontsize=10)
        ax.set_title(f'Cell Positions (n = {num_cells} cells)', fontsize=14, fontweight='bold', pad=20)
        
    else:  # 2D
        ax = fig.add_subplot(111)
        
        # Plot cells by phenotype
        if show_phenotypes:
            for phenotype in set(phenotypes):
                # Filter positions for this phenotype
                pheno_positions = [pos for pos, ph in zip(positions, phenotypes) if ph == phenotype]
                if pheno_positions:
                    xs, ys = zip(*pheno_positions)
                    color = phenotype_colors.get(phenotype, '#34495e')
                    ax.scatter(xs, ys, c=color, s=marker_size,
                              label=f"{phenotype} ({phenotype_counts[phenotype]})",
                              alpha=0.7, edgecolors='black', linewidth=0.5)
            ax.legend(loc='upper right', fontsize=10)
        else:
            xs, ys = zip(*positions)
            ax.scatter(xs, ys, c='#3498db', s=marker_size, alpha=0.7,
                      edgecolors='black', linewidth=0.5)
        
        ax.set_xlabel('X Position', fontsize=12)
        ax.set_ylabel('Y Position', fontsize=12)
        ax.set_title(f'Cell Positions (n = {num_cells} cells)', fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
    
    # Add phenotype breakdown to title if showing phenotypes
    if show_phenotypes and len(phenotype_counts) > 1:
        breakdown = ", ".join([f"{ph}: {cnt}" for ph, cnt in sorted(phenotype_counts.items())])
        ax.set_title(f'Cell Positions (n = {num_cells} cells)\n{breakdown}', 
                    fontsize=12, fontweight='bold', pad=15)
    
    # =========================================================================
    # SAVE PLOT
    # =========================================================================
    output_file = os.path.join(output_dir, f"cell_positions_{'3d' if is_3d else '2d'}.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[CELL_PLOTS] Saved plot to: {output_file}")
    print(f"[CELL_PLOTS] Population breakdown:")
    for phenotype, count in sorted(phenotype_counts.items(), key=lambda x: -x[1]):
        percentage = 100 * count / num_cells
        print(f"   {phenotype}: {count}/{num_cells} ({percentage:.1f}%)")
    
    return True
