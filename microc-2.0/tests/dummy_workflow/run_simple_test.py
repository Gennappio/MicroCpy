#!/usr/bin/env python3
"""
Simple test script for workflow validation.

This script runs a simple workflow where each function just prints
its name and parameters. This makes it easy to verify that:
1. Functions are being called
2. Parameters are being passed correctly
3. Execution order is correct
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_path))

from workflow.loader import WorkflowLoader
from workflow.executor import WorkflowExecutor


def main():
    """Run the simple logging workflow test."""
    
    print("=" * 80)
    print("SIMPLE WORKFLOW TEST - Function Logging")
    print("=" * 80)
    print()
    print("This test validates that:")
    print("  1. Functions are loaded from external file")
    print("  2. Functions are called in correct order")
    print("  3. Parameters are passed correctly")
    print()
    
    # Load workflow
    workflow_path = Path(__file__).parent / 'simple_workflow.json'
    print(f"Loading workflow: {workflow_path.name}")
    
    loader = WorkflowLoader()
    workflow = loader.load(workflow_path)
    
    print(f"✓ Loaded: {workflow.name}")
    print()
    
    # Create executor
    executor = WorkflowExecutor(workflow)
    
    # Create dummy context
    context = {
        'timestep': 0,
        'population': None,
        'mesh': None,
        'output_dir': 'results/simple_test',
    }
    
    # Execute each stage
    stages = ['initialization', 'intracellular', 'diffusion', 'intercellular', 'finalization']
    
    for stage_name in stages:
        stage = workflow.stages.get(stage_name)
        if stage and stage.enabled:
            print("-" * 80)
            print(f"STAGE: {stage_name.upper()}")
            print("-" * 80)
            
            try:
                context = executor.execute_stage(stage_name, context)
                print()
            except Exception as e:
                print(f"✗ Error in stage '{stage_name}': {e}")
                import traceback
                traceback.print_exc()
                print()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print("If you see function calls above with their parameters,")
    print("the workflow system is working correctly!")
    print()


if __name__ == '__main__':
    main()

