#!/usr/bin/env python3
"""
Test the workflow system infrastructure.

This test verifies:
1. Workflow schema and data structures
2. Workflow loader (JSON serialization/deserialization)
3. Function registry
4. Workflow executor initialization
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow.schema import WorkflowDefinition, WorkflowStage, WorkflowFunction
from src.workflow.loader import WorkflowLoader
from src.workflow.registry import get_default_registry
from src.workflow.executor import WorkflowExecutor


def test_workflow_schema():
    """Test workflow schema creation and validation."""
    print("\n" + "=" * 60)
    print("TEST 1: Workflow Schema")
    print("=" * 60)
    
    # Create a simple workflow
    workflow = WorkflowDefinition(
        name="Test Workflow",
        description="A test workflow"
    )
    
    # Add a function to intracellular stage
    intracellular_stage = workflow.get_stage("intracellular")
    test_func = WorkflowFunction(
        id="test_1",
        function_name="calculate_cell_metabolism",
        parameters={"oxygen_vmax": 1.0e-16}
    )
    intracellular_stage.functions.append(test_func)
    intracellular_stage.execution_order.append("test_1")
    
    # Validate
    errors = workflow.validate()
    if errors:
        print(f"❌ Validation failed: {errors}")
        return False
    
    print("✅ Workflow schema creation and validation successful")
    print(f"   Name: {workflow.name}")
    print(f"   Stages: {list(workflow.stages.keys())}")
    print(f"   Intracellular functions: {len(intracellular_stage.functions)}")
    return True


def test_workflow_loader():
    """Test workflow JSON loading."""
    print("\n" + "=" * 60)
    print("TEST 2: Workflow Loader")
    print("=" * 60)
    
    # Load the Jayatilake workflow
    workflow_path = Path(__file__).parent / "jayatilake_experiment" / "jaya_workflow.json"
    
    if not workflow_path.exists():
        print(f"❌ Workflow file not found: {workflow_path}")
        return False
    
    try:
        workflow = WorkflowLoader.load(workflow_path)
        print("✅ Workflow loaded successfully")
        print(f"   Name: {workflow.name}")
        print(f"   Version: {workflow.version}")
        print(f"   Description: {workflow.description[:80]}...")
        
        # Check stages
        for stage_name, stage in workflow.stages.items():
            if stage.functions:
                print(f"   {stage_name}: {len(stage.functions)} functions")
        
        return True
    except Exception as e:
        print(f"❌ Failed to load workflow: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_function_registry():
    """Test function registry."""
    print("\n" + "=" * 60)
    print("TEST 3: Function Registry")
    print("=" * 60)
    
    registry = get_default_registry()
    
    print(f"✅ Registry created with {len(registry.functions)} functions")
    
    # Check some key functions
    key_functions = [
        "initialize_cell_placement",
        "calculate_cell_metabolism",
        "should_divide",
        "update_cell_phenotype"
    ]
    
    for func_name in key_functions:
        metadata = registry.get(func_name)
        if metadata:
            print(f"   ✓ {func_name}: {metadata.display_name}")
            print(f"     Category: {metadata.category.value}")
            print(f"     Parameters: {len(metadata.parameters)}")
        else:
            print(f"   ✗ {func_name}: NOT FOUND")
            return False
    
    return True


def test_workflow_executor():
    """Test workflow executor initialization."""
    print("\n" + "=" * 60)
    print("TEST 4: Workflow Executor")
    print("=" * 60)
    
    # Load workflow
    workflow_path = Path(__file__).parent / "jayatilake_experiment" / "jaya_workflow.json"
    
    try:
        workflow = WorkflowLoader.load(workflow_path)
        
        # Create executor (without custom functions for now)
        executor = WorkflowExecutor(workflow, custom_functions_module=None, config=None)
        
        print("✅ Workflow executor created successfully")
        print(f"   Workflow: {executor.workflow.name}")
        print(f"   Registry: {len(executor.registry.functions)} functions")
        
        # Test stage execution (dry run)
        context = {"test": "data"}
        result = executor.execute_stage("initialization", context)
        
        print(f"   Stage execution test: {type(result)}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create executor: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("WORKFLOW SYSTEM TESTS")
    print("=" * 60)
    
    tests = [
        ("Schema", test_workflow_schema),
        ("Loader", test_workflow_loader),
        ("Registry", test_function_registry),
        ("Executor", test_workflow_executor),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

