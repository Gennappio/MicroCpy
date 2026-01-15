#!/usr/bin/env python3
"""
Test the workflow system infrastructure.

This test verifies:
1. Workflow schema and data structures
2. Workflow loader (JSON serialization/deserialization)
3. Function registry
4. Workflow executor initialization
5. Context registry requirement for execution
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow.schema import WorkflowDefinition, WorkflowStage, WorkflowFunction
from src.workflow.loader import WorkflowLoader
from src.workflow.registry import get_default_registry
from src.workflow.executor import WorkflowExecutor
from src.workflow.validated_context import ContextRegistryRequired


def create_test_context_registry():
    """Create a minimal context registry for testing."""
    return {
        "schema_version": 1,
        "project_id": "test-project",
        "revision": 1,
        "keys": [
            {"id": "test-key-1", "name": "test", "type": {"kind": "primitive", "name": "string"}},
            {"id": "test-key-2", "name": "timestep", "type": {"kind": "primitive", "name": "int"}},
            {"id": "test-key-3", "name": "population", "type": {"kind": "primitive", "name": "object"}, "nullable": True},
            {"id": "test-key-4", "name": "mesh", "type": {"kind": "primitive", "name": "object"}, "nullable": True},
            {"id": "test-key-5", "name": "output_dir", "type": {"kind": "primitive", "name": "string"}},
        ]
    }


def test_workflow_schema():
    """Test workflow schema creation and validation."""
    print("\n" + "=" * 60)
    print("TEST 1: Workflow Schema")
    print("=" * 60)

    # Create a simple v1.0 workflow (uses stages)
    workflow = WorkflowDefinition(
        version="1.0",  # Use v1.0 for stage-based workflow
        name="Test Workflow",
        description="A test workflow"
    )

    # Add a function to intracellular stage
    intracellular_stage = workflow.get_stage("intracellular")
    if intracellular_stage is None:
        print("❌ intracellular stage not found")
        return False

    test_func = WorkflowFunction(
        id="test_1",
        function_name="calculate_cell_metabolism",
        parameters={"oxygen_vmax": 1.0e-16}
    )
    intracellular_stage.functions.append(test_func)
    intracellular_stage.execution_order.append("test_1")

    # Validate (v1.0 returns list of errors or empty list)
    errors = workflow.validate()
    # Handle both dict and list return types from validate()
    if isinstance(errors, dict):
        if not errors.get('valid', True):
            print(f"❌ Validation failed: {errors.get('errors', [])}")
            return False
    elif errors:  # list of errors
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
    """Test workflow executor initialization with context registry."""
    print("\n" + "=" * 60)
    print("TEST 4: Workflow Executor")
    print("=" * 60)

    # Load workflow
    workflow_path = Path(__file__).parent / "jayatilake_experiment" / "jaya_workflow.json"

    try:
        workflow = WorkflowLoader.load(workflow_path)

        # Create test context registry
        context_registry = create_test_context_registry()

        # Create executor with context registry (REQUIRED)
        executor = WorkflowExecutor(
            workflow,
            custom_functions_module=None,
            config=None,
            context_registry=context_registry,
            enforcement_mode='warn'  # Use warn mode for testing (allows unknown keys)
        )

        print("✅ Workflow executor created successfully")
        print(f"   Workflow: {executor.workflow.name}")
        print(f"   Registry: {len(executor.registry.functions)} functions")
        print(f"   Context registry: loaded with {len(context_registry['keys'])} keys")

        # Test stage execution (dry run) using validated context
        context = executor.create_validated_context({"test": "data"})
        result = executor.execute_stage("initialization", context)

        print(f"   Stage execution test: {type(result)}")

        return True
    except Exception as e:
        print(f"❌ Failed to create executor: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_registry_requirement():
    """Test that executor requires context registry for execution."""
    print("\n" + "=" * 60)
    print("TEST 5: Context Registry Requirement")
    print("=" * 60)

    # Load workflow
    workflow_path = Path(__file__).parent / "jayatilake_experiment" / "jaya_workflow.json"

    try:
        workflow = WorkflowLoader.load(workflow_path)

        # Try to create executor WITHOUT context registry - should fail
        try:
            executor = WorkflowExecutor(workflow)
            print("❌ Expected ContextRegistryRequired exception but none raised")
            return False
        except ContextRegistryRequired as e:
            print(f"✅ Correctly raised ContextRegistryRequired: {e}")

        # Test structural validation works without registry
        print("   Testing structural validation (no registry needed)...")
        result = workflow.validate_structure()
        if result['valid']:
            print("✅ Structural validation passed without registry")
        else:
            print(f"   Structural validation errors: {result['errors']}")

        return True

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
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
        ("Context Registry Requirement", test_context_registry_requirement),
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

