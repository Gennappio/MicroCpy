#!/usr/bin/env python3
"""
Test script for the ecosystem simulation workflow.
Tests that the updated function signatures work correctly.
"""

import sys
import os
from pathlib import Path

# Add microc-2.0 to path
microc_path = Path(__file__).parent / "microc-2.0"
sys.path.insert(0, str(microc_path))
sys.path.insert(0, str(microc_path / "src"))

# Change to microc-2.0 directory so relative imports work
os.chdir(str(microc_path))

from workflow.loader import WorkflowLoader
from workflow.executor import WorkflowExecutor


def main():
    """Run the ecosystem simulation workflow."""
    
    print("=" * 80)
    print("ECOSYSTEM SIMULATION TEST")
    print("=" * 80)
    print()
    
    # Load workflow (relative to original working directory)
    original_dir = Path(__file__).parent
    workflow_path = original_dir / "example_projects/ecosystem_sim/workflows/ecosystem_workflow.json"
    
    if not workflow_path.exists():
        print(f"❌ Workflow file not found: {workflow_path}")
        return False
    
    print(f"Loading workflow: {workflow_path.name}")
    
    try:
        loader = WorkflowLoader()
        workflow = loader.load(workflow_path)
        print(f"✓ Loaded: {workflow.name}")
        print()
    except Exception as e:
        print(f"❌ Failed to load workflow: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Create executor
    try:
        executor = WorkflowExecutor(workflow)
        print("✓ Executor created successfully")
        print()
    except Exception as e:
        print(f"❌ Failed to create executor: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Create initial context with parameters
    context = {
        'params.grid_size': 50,
        'params.initial_prey': 100,
        'params.initial_predators': 20,
        'params.predation_rate': 0.4,
        'params.prey_reproduction_rate': 0.05,
        'params.predator_reproduction_rate': 0.3,
        'params.predator_starve_time': 10,
        'results_dir': 'results/ecosystem_sim',
    }
    
    print("Initial context:")
    for key, value in context.items():
        print(f"  {key}: {value}")
    print()
    
    # Execute the main workflow
    try:
        print("-" * 80)
        print("EXECUTING WORKFLOW")
        print("-" * 80)
        print()
        
        result_context = executor.execute_main(context)
        
        print()
        print("-" * 80)
        print("WORKFLOW EXECUTION COMPLETED")
        print("-" * 80)
        print()
        
        # Print results
        if 'output.population_history' in result_context:
            history = result_context['output.population_history']
            print(f"✓ Simulation completed {len(history)} steps")
            if history:
                print(f"  Initial: {history[0]['predators']} predators, {history[0]['prey']} prey")
                print(f"  Final: {history[-1]['predators']} predators, {history[-1]['prey']} prey")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

