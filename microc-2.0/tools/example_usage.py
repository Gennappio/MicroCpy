#!/usr/bin/env python3
"""
Example Usage of MicroC Cell State Analysis Tools

This script demonstrates how to use the cell state analysis tools
to inspect and analyze MicroC simulation files.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and display its output"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"[!] Error: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
    except FileNotFoundError:
        print(f"[!] Command not found: {cmd[0]}")

def main():
    print("[CELL] MicroC Cell State Analysis Tools - Example Usage")
    print("=" * 80)
    
    # Check if we have the initial state file
    initial_state_file = "initial_state_3D_S.h5"
    if not Path(initial_state_file).exists():
        print(f"[!] Initial state file not found: {initial_state_file}")
        print("Please run MicroC with save_initial_state: true first")
        return
    
    # Example 1: Quick inspection
    run_command(
        ["python", "tools/quick_inspect.py", initial_state_file],
        "Quick Inspection of Initial State File"
    )
    
    # Example 2: Detailed analysis
    run_command(
        ["python", "tools/cell_state_analyzer.py", initial_state_file, "--detailed-cells", "2"],
        "Detailed Analysis with Sample Cells"
    )
    
    # Example 3: Gene network analysis
    run_command(
        ["python", "tools/cell_state_analyzer.py", initial_state_file, "--gene-analysis", "--no-summary"],
        "Gene Network Analysis"
    )
    
    # Example 4: Export data
    run_command(
        ["python", "tools/cell_state_analyzer.py", initial_state_file, "--export-csv", "--no-summary"],
        "Export Data to CSV"
    )
    
    # Example 5: Multiple file inspection
    cell_states_pattern = "results/jayatilake_experiment/cell_states/*.h5"
    run_command(
        ["python", "tools/quick_inspect.py"] + [cell_states_pattern],
        "Inspect Multiple Cell State Files"
    )
    
    print(f"\n{'='*80}")
    print("[+] Example usage completed!")
    print("[FILE] Check the 'exports' folder for CSV files")
    print("[STATS] Check for JSON summary files in the current directory")
    print("💡 Use --help with any tool for more options")
    print("=" * 80)

if __name__ == "__main__":
    main()
