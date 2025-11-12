#!/usr/bin/env python3
"""
MicroC Master Runner
Run all MicroC tools and simulations via command line flags
"""

import argparse
import subprocess
import sys
from pathlib import Path

def run_tool(tool_path, args=None):
    """Run a tool with optional arguments"""
    cmd = [sys.executable, str(tool_path)]
    if args:
        cmd.extend(args)

    print(f"[RUN] Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"[+] {tool_path.name} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] {tool_path.name} failed with error:")
        print(e.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="MicroC Master Runner - Run all MicroC tools and simulations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run main simulation
  python run_microc.py --sim tests/jayatilake_experiment/jayatilake_experiment_config.yaml

  # Run simulation with custom workflow
  python run_microc.py --sim tests/jayatilake_experiment/jayatilake_experiment_config.yaml --workflow tests/jayatilake_experiment/jaya_workflow.json

  # Generate CSV cell files for 2D simulations
  python run_microc.py --generate-csv --pattern spheroid --count 50 --output cells.csv
  python run_microc.py --generate-csv --pattern grid --grid_size 5x5 --output grid_cells.csv

  # Generate CSV with complete gene network from BND file
  python run_microc.py --generate-csv --pattern spheroid --count 25 --genes tests/jayatilake_experiment/jaya_microc.bnd --output full_genes.csv

  # Generate plots from CSV simulation results (decoupled plotting)
  python run_microc.py --plot-csv --cells-dir results/csv_cells --plot-output plots --snapshots

  # Generate comprehensive plots with substances and statistics
  python run_microc.py --plot-csv --cells-dir results/csv_cells --substances-dir results/csv_substances --plot-output plots --snapshots --animation --statistics
        """
    )

    # Main simulation
    parser.add_argument('--sim', metavar='CONFIG',
                       help='Run main MicroC simulation with config file')
    parser.add_argument('--workflow', metavar='WORKFLOW_JSON',
                       help='Optional workflow JSON file to customize simulation behavior')

    # CSV generation for 2D simulations
    parser.add_argument('--generate-csv', action='store_true',
                       help='Generate CSV file with cell positions for 2D simulations')
    parser.add_argument('--pattern', choices=['spheroid', 'grid', 'random'], default='spheroid',
                       help='Cell placement pattern (default: spheroid)')
    parser.add_argument('--count', type=int, default=25,
                       help='Number of cells to generate (default: 25)')
    parser.add_argument('--grid_size', default='5x5',
                       help='Grid size for grid pattern (e.g., 5x5, default: 5x5)')
    parser.add_argument('--output', default='generated_cells.csv',
                       help='Output CSV file name (default: generated_cells.csv)')
    parser.add_argument('--cell_size_um', type=float, default=20.0,
                       help='Cell size in micrometers (default: 20.0)')
    parser.add_argument('--domain_size', type=int, default=25,
                       help='Domain size in grid units (default: 25)')
    parser.add_argument('--domain_size_um', type=float, default=500.0,
                       help='Domain size in micrometers (default: 500.0)')
    parser.add_argument('--genes', metavar='BND_FILE',
                       help='Path to .bnd file to read gene network nodes for complete gene state initialization')

    # CSV plotting for post-simulation visualization
    parser.add_argument('--plot-csv', action='store_true',
                       help='Generate plots from CSV simulation results (decoupled plotting)')
    parser.add_argument('--cells-dir', metavar='DIR',
                       help='Directory containing CSV cell state files (required for --plot-csv)')
    parser.add_argument('--substances-dir', metavar='DIR',
                       help='Directory containing CSV substance field files (optional for --plot-csv)')
    parser.add_argument('--plot-output', metavar='DIR', default='plots',
                       help='Output directory for generated plots (default: plots)')
    parser.add_argument('--snapshots', action='store_true',
                       help='Generate snapshot plots for each time step')
    parser.add_argument('--animation', action='store_true',
                       help='Generate animation from time series data')
    parser.add_argument('--statistics', action='store_true',
                       help='Generate population statistics plots')

    args = parser.parse_args()

    # Check if no arguments provided
    if not any(vars(args).values()):
        parser.print_help()
        return

    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    tools_dir = script_dir / "tools"

    success_count = 0
    total_count = 0

    # Main simulation
    if args.sim:
        total_count += 1
        run_sim_path = script_dir / "run_sim.py" if (script_dir / "run_sim.py").exists() else tools_dir / "run_sim.py"
        sim_args = [args.sim]
        if args.workflow:
            sim_args.extend(['--workflow', args.workflow])
        if run_tool(run_sim_path, sim_args):
            success_count += 1

    # CSV file generation for 2D simulations
    if args.generate_csv:
        total_count += 1
        csv_args = [
            '--output', args.output,
            '--pattern', args.pattern,
            '--cell_size_um', str(args.cell_size_um),
            '--domain_size', str(args.domain_size),
            '--domain_size_um', str(args.domain_size_um)
        ]

        if args.pattern == 'grid':
            csv_args.extend(['--grid_size', args.grid_size])
        else:
            csv_args.extend(['--count', str(args.count)])

        # Add genes file if specified
        if args.genes:
            csv_args.extend(['--genes', args.genes])

        if run_tool(tools_dir / "csv_cell_generator.py", csv_args):
            success_count += 1

    # CSV plotting for post-simulation visualization
    if args.plot_csv:
        total_count += 1

        # Validate required arguments
        if not args.cells_dir:
            print("[!] Error: --cells-dir is required when using --plot-csv")
            print("    Specify the directory containing CSV cell state files")
            return

        # Build plotting arguments
        plot_args = [
            '--cells-dir', args.cells_dir,
            '--output', args.plot_output
        ]

        # Add optional arguments
        if args.substances_dir:
            plot_args.extend(['--substances-dir', args.substances_dir])

        if args.snapshots:
            plot_args.append('--snapshots')

        if args.animation:
            plot_args.append('--animation')

        if args.statistics:
            plot_args.append('--statistics')

        # Default to snapshots if no plot type specified
        if not any([args.snapshots, args.animation, args.statistics]):
            plot_args.append('--snapshots')
            print("[INFO] No plot type specified, defaulting to --snapshots")

        if run_tool(tools_dir / "csv_plotter.py", plot_args):
            success_count += 1

    # Summary
    if total_count > 0:
        print(f"\n[DONE] Completed {success_count}/{total_count} tasks")
    else:
        print("\n[INFO] No tasks were run")

if __name__ == "__main__":
    main()
