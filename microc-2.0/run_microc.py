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
  
  # Analyze cell states from H5 file
  python run_microc.py --analyze initial_state_3D_S.h5
  
  # Visualize cell states
  python run_microc.py --visualize initial_state_3D_S.h5
  
  # Quick inspect H5 file
  python run_microc.py --inspect initial_state_3D_S.h5
  
  # Run FiPy standalone simulation
  python run_microc.py --fipy initial_state_3D_S.h5

  # Generate custom H5 files
  python run_microc.py --generate --cells 1000 --radius 50

  # Run all visualization tools
  python run_microc.py --all-viz initial_state_3D_S.h5
        """
    )
    
    # Main simulation
    parser.add_argument('--sim', metavar='CONFIG', 
                       help='Run main MicroC simulation with config file')
    
    # Tools in tools/ folder
    parser.add_argument('--analyze', metavar='H5_FILE',
                       help='Run cell state analyzer')
    parser.add_argument('--visualize', metavar='H5_FILE', 
                       help='Run cell state visualizer')
    parser.add_argument('--inspect', metavar='H5_FILE',
                       help='Quick inspect H5 file')
    parser.add_argument('--demo', action='store_true',
                       help='Run visualization demo')
    
    # Benchmarks
    parser.add_argument('--fipy', metavar='H5_FILE',
                       help='Run FiPy H5 reader simulation')
    
    # H5 file generation
    parser.add_argument('--generate', action='store_true',
                       help='Generate custom H5 files')
    parser.add_argument('--cells', type=int, default=1000,
                       help='Number of cells (for --generate)')
    parser.add_argument('--radius', type=float, default=50.0,
                       help='Sphere radius in um (for --generate)')
    parser.add_argument('--sparseness', type=float, default=0.3,
                       help='Sparseness 0-1 (for --generate)')
    parser.add_argument('--radial', type=float, default=0.5,
                       help='Radial distribution 0-1 (for --generate)')
    parser.add_argument('--biocell-size', type=float, default=5.0,
                       help='Biological cell size in um (for --generate, default: 5.0)')
    parser.add_argument('--gene-probs', default='gene_probs.txt',
                       help='Gene probabilities file (for --generate)')
    parser.add_argument('--output', default='generated_cells',
                       help='Output prefix (for --generate)')

    # Convenience flags
    parser.add_argument('--all-viz', metavar='H5_FILE',
                       help='Run all visualization tools on H5 file')
    
    args = parser.parse_args()
    
    # Check if no arguments provided
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    tools_dir = Path("tools")
    benchmarks_dir = Path("benchmarks")
    
    success_count = 0
    total_count = 0
    
    # Main simulation
    if args.sim:
        total_count += 1
        if run_tool(Path("run_sim.py") if Path("run_sim.py").exists() else tools_dir / "run_sim.py", [args.sim]):
            success_count += 1
    
    # Cell state analyzer
    if args.analyze:
        total_count += 1
        if run_tool(tools_dir / "cell_state_analyzer.py", [args.analyze]):
            success_count += 1
    
    # Cell state visualizer
    if args.visualize:
        total_count += 1
        if run_tool(tools_dir / "cell_state_visualizer.py", [args.visualize]):
            success_count += 1
    
    # Quick inspect
    if args.inspect:
        total_count += 1
        if run_tool(tools_dir / "quick_inspect.py", [args.inspect]):
            success_count += 1
    
    # Visualization demo
    if args.demo:
        total_count += 1
        if run_tool(tools_dir / "visualization_demo.py"):
            success_count += 1
    
    # FiPy simulation
    if args.fipy:
        total_count += 1
        if run_tool(benchmarks_dir / "standalone_steadystate_fipy_3D_h5_reader.py", [args.fipy]):
            success_count += 1

    # H5 file generation
    if args.generate:
        total_count += 1
        gen_args = [
            '--cells', str(args.cells),
            '--radius', str(args.radius),
            '--sparseness', str(args.sparseness),
            '--radial', str(args.radial),
            '--cell-size', str(args.biocell_size),
            '--gene-probs', args.gene_probs,
            '--output', args.output
        ]
        if run_tool(tools_dir / "h5_generator.py", gen_args):
            success_count += 1
    
    # All visualization tools
    if args.all_viz:
        viz_tools = [
            (tools_dir / "cell_state_analyzer.py", [args.all_viz]),
            (tools_dir / "cell_state_visualizer.py", [args.all_viz]),
            (tools_dir / "quick_inspect.py", [args.all_viz])
        ]
        
        for tool_path, tool_args in viz_tools:
            total_count += 1
            if run_tool(tool_path, tool_args):
                success_count += 1
    
    # Summary
    print(f"\n[CHART] Summary: {success_count}/{total_count} tools completed successfully")
    
    if success_count == total_count:
        print("[SUCCESS] All tools completed successfully!")
    else:
        print(f"[WARN]  {total_count - success_count} tools failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
