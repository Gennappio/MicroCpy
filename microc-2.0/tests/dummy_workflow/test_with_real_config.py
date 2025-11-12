#!/usr/bin/env python3
"""
Test script to run simple_workflow.json with dummy_config.yaml

This demonstrates how to run a workflow with a real simulation config.
The simple_workflow.json uses dummy logging functions, so it won't do
anything useful - it will just print function names and parameters.

For a real simulation, you need a workflow with actual simulation functions.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run simple workflow with dummy config."""
    
    # Get paths
    test_dir = Path(__file__).parent
    microc_root = test_dir.parent.parent
    run_microc = microc_root / "run_microc.py"
    
    # Use dummy config (minimal config for testing)
    config_path = test_dir / "dummy_config.yaml"
    workflow_path = test_dir / "simple_workflow.json"
    
    print("=" * 80)
    print("TESTING WORKFLOW WITH REAL SIMULATION")
    print("=" * 80)
    print()
    print(f"Config:   {config_path}")
    print(f"Workflow: {workflow_path}")
    print()
    print("NOTE: This uses dummy logging functions, so it will just print")
    print("      function names and parameters. For a real simulation, use")
    print("      a workflow with actual simulation functions.")
    print()
    print("=" * 80)
    print()
    
    # Build command
    cmd = [
        sys.executable,
        str(run_microc),
        "--sim", str(config_path),
        "--workflow", str(workflow_path)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Run simulation
    try:
        result = subprocess.run(cmd, check=True)
        print()
        print("=" * 80)
        print("✓ Simulation completed successfully")
        print("=" * 80)
        return 0
    except subprocess.CalledProcessError as e:
        print()
        print("=" * 80)
        print(f"✗ Simulation failed with exit code {e.returncode}")
        print("=" * 80)
        return e.returncode

if __name__ == '__main__':
    sys.exit(main())

