"""
Generate ATP Source Plots

Visualizes cell positions in 2D/3D space colored by ATP production sources.
Creates scatter plots showing spatial distribution of cells, colored by their
ATP production strategy (mitoATP, glycoATP, both, or none).

Example:
    This function can be used in workflows like:
    - Metabolic strategy analysis
    - ATP production pattern visualization
    - Energy metabolism mapping

Notes:
    - Automatically detects 2D vs 3D based on cell positions
    - Saves plots to results/plots/ directory
    - Colors cells based on gene network states for mitoATP and glycoATP
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
    display_name="Generate ATP Source Plots",
    description="Generate spatial plots of cells colored by ATP production sources (mitoATP/glycoATP)",
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
        }
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"]
)
def generate_atp_plots(
    context: Dict[str, Any] = None,
    output_dir: str = "results/plots",
    plot_size: float = 10.0,
    marker_size: float = 50.0,
    **kwargs
) -> bool:
    """
    Generate spatial visualization of cells colored by ATP production sources.
    
    Creates scatter plots showing cell positions in 2D or 3D space,
    colored by their ATP production strategy:
    - Both: mitoATP ON and glycoATP ON (green)
    - mitoATP only: mitoATP ON, glycoATP OFF (blue)
    - glycoATP only: glycoATP ON, mitoATP OFF (orange)
    - None: both OFF (gray)
    
    Args:
        context: Workflow context containing population
        output_dir: Directory to save plots (relative to workspace root)
        plot_size: Figure size in inches
        marker_size: Size of cell markers
        **kwargs: Additional parameters (for forward compatibility)
        
    Returns:
        True if successful, False otherwise
    """
    # =========================================================================
    # CHECK DEPENDENCIES
    # =========================================================================
    if not MATPLOTLIB_AVAILABLE:
        print("[ERROR] [generate_atp_plots] matplotlib not available - cannot generate plots")
        print("       Install with: pip install matplotlib")
        return False
    
    # =========================================================================
    # VALIDATE CONTEXT
    # =========================================================================
    if not context:
        print("[ERROR] [generate_atp_plots] No context provided")
        return False
    
    # =========================================================================
    # GET REQUIRED ITEMS FROM CONTEXT
    # =========================================================================
    population = context.get('population')
    if population is None:
        print("[ERROR] [generate_atp_plots] No population in context")
        return False
    
    # PRIORITY 1: Use GUI results directory if available
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
    gui_results_dir = os.path.join(workspace_root, 'opencellcomms_gui', 'GUI_results')
    
    if os.path.exists(gui_results_dir):
        output_dir = gui_results_dir
        print(f"[ATP_PLOTS] Using GUI results directory: {output_dir}")
    elif 'plots_dir' in context:
        output_dir = context['plots_dir']
        print(f"[ATP_PLOTS] Using plots_dir from context: {output_dir}")
    else:
        print(f"[ATP_PLOTS] Using parameter output_dir: {output_dir}")
    
    # =========================================================================
    # EXTRACT CELL DATA
    # =========================================================================
    cells = population.state.cells
    num_cells = len(cells)
    
    if num_cells == 0:
        print("[WARNING] [generate_atp_plots] No cells to plot")
        return True
    
    print(f"[ATP_PLOTS] Generating ATP source plots for {num_cells} cells")

    # Collect cell positions and ATP sources
    positions = []
    atp_sources = []
    is_3d = None

    for cell_id, cell in cells.items():
        pos = cell.state.position
        positions.append(pos)

        # Detect dimensionality from first cell
        if is_3d is None:
            is_3d = (len(pos) == 3)

        # Get ATP source from gene states
        gene_states = getattr(cell.state, 'gene_states', {})
        mito_atp = gene_states.get('mitoATP', False)
        glyco_atp = gene_states.get('glycoATP', False)

        # Classify ATP source
        if mito_atp and glyco_atp:
            atp_source = 'Both'
        elif mito_atp:
            atp_source = 'mitoATP only'
        elif glyco_atp:
            atp_source = 'glycoATP only'
        else:
            atp_source = 'None'

        atp_sources.append(atp_source)

    # Count ATP sources
    atp_source_counts = Counter(atp_sources)

    # =========================================================================
    # CREATE OUTPUT DIRECTORY
    # =========================================================================
    os.makedirs(output_dir, exist_ok=True)

    # =========================================================================
    # GENERATE PLOTS
    # =========================================================================
    print(f"[ATP_PLOTS] Generating {'3D' if is_3d else '2D'} scatter plot")

    # Define colors for ATP sources
    atp_colors = {
        'Both': '#2ecc71',           # Green - using both sources
        'mitoATP only': '#3498db',   # Blue - oxidative metabolism
        'glycoATP only': '#f39c12',  # Orange - glycolytic metabolism
        'None': '#95a5a6'            # Gray - no ATP production
    }

    # Create figure
    fig = plt.figure(figsize=(plot_size, plot_size))

    if is_3d:
        ax = fig.add_subplot(111, projection='3d')

        # Plot cells by ATP source
        for atp_source in set(atp_sources):
            # Filter positions for this ATP source
            source_positions = [pos for pos, src in zip(positions, atp_sources) if src == atp_source]
            if source_positions:
                xs, ys, zs = zip(*source_positions)
                color = atp_colors.get(atp_source, '#34495e')
                ax.scatter(xs, ys, zs, c=color, s=marker_size,
                          label=f"{atp_source} ({atp_source_counts[atp_source]})",
                          alpha=0.7, edgecolors='black', linewidth=0.5)
        ax.legend(loc='upper right', fontsize=8)

        ax.set_xlabel('X Position', fontsize=10)
        ax.set_ylabel('Y Position', fontsize=10)
        ax.set_zlabel('Z Position', fontsize=10)
        ax.set_title(f'ATP Production Sources (n = {num_cells} cells)', fontsize=14, fontweight='bold', pad=20)

    else:  # 2D
        ax = fig.add_subplot(111)

        # Plot cells by ATP source
        for atp_source in set(atp_sources):
            # Filter positions for this ATP source
            source_positions = [pos for pos, src in zip(positions, atp_sources) if src == atp_source]
            if source_positions:
                xs, ys = zip(*source_positions)
                color = atp_colors.get(atp_source, '#34495e')
                ax.scatter(xs, ys, c=color, s=marker_size,
                          label=f"{atp_source} ({atp_source_counts[atp_source]})",
                          alpha=0.7, edgecolors='black', linewidth=0.5)
        ax.legend(loc='upper right', fontsize=10)

        ax.set_xlabel('X Position', fontsize=12)
        ax.set_ylabel('Y Position', fontsize=12)
        ax.set_title(f'ATP Production Sources (n = {num_cells} cells)', fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

    # Add ATP source breakdown to title
    if len(atp_source_counts) > 1:
        breakdown = ", ".join([f"{src}: {cnt}" for src, cnt in sorted(atp_source_counts.items())])
        ax.set_title(f'ATP Production Sources (n = {num_cells} cells)\n{breakdown}',
                    fontsize=12, fontweight='bold', pad=15)

    # =========================================================================
    # SAVE PLOT
    # =========================================================================
    output_file = os.path.join(output_dir, f"atp_sources_{'3d' if is_3d else '2d'}.png")
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"[ATP_PLOTS] Saved plot to: {output_file}")
    print(f"[ATP_PLOTS] ATP source breakdown:")
    for atp_source, count in sorted(atp_source_counts.items(), key=lambda x: -x[1]):
        percentage = 100 * count / num_cells
        print(f"   {atp_source}: {count}/{num_cells} ({percentage:.1f}%)")

    return True

