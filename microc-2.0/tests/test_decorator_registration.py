"""
Test script for decorator-based function registration system.

This script verifies that:
1. Decorated functions are properly registered
2. Metadata is correctly extracted
3. Manual and decorator registrations can coexist
4. The merged registry contains all functions
"""

import sys
import os

# Add microc-2.0 root to path
root_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.abspath(root_dir))

# Add tests directory to path
tests_dir = os.path.join(os.path.dirname(__file__), 'jayatilake_experiment')
sys.path.insert(0, os.path.abspath(tests_dir))

print("=" * 80)
print("TESTING DECORATOR-BASED FUNCTION REGISTRATION")
print("=" * 80)

# Test 1: Import decorator module
print("\n[TEST 1] Importing decorator module...")
try:
    from src.workflow.decorators import register_function, get_decorator_registry, merge_registries
    print("✅ Decorator module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import decorator module: {e}")
    sys.exit(1)

# Test 2: Check decorator registry before importing decorated functions
print("\n[TEST 2] Checking decorator registry before imports...")
decorator_registry = get_decorator_registry()
initial_count = len(decorator_registry.functions)
print(f"   Initial decorator registry has {initial_count} functions")

# Test 3: Import module with decorated functions
print("\n[TEST 3] Importing jayatilake_experiment_cell_functions...")
try:
    import jayatilake_experiment_cell_functions
    print("✅ Module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import module: {e}")
    sys.exit(1)

# Test 4: Check decorator registry after importing decorated functions
print("\n[TEST 4] Checking decorator registry after imports...")
decorator_registry = get_decorator_registry()
final_count = len(decorator_registry.functions)
print(f"   Decorator registry now has {final_count} functions")
print(f"   Added {final_count - initial_count} decorated functions")

if final_count > initial_count:
    print("\n   Decorated functions:")
    for name, metadata in decorator_registry.functions.items():
        print(f"   - {name}")
        print(f"     Display Name: {metadata.display_name}")
        print(f"     Category: {metadata.category.value}")
        print(f"     Parameters: {len(metadata.parameters)}")
        print(f"     Module: {metadata.module_path}")
        print(f"     Source: {metadata.source_file}")
        print()

# Test 5: Get default registry (which should merge manual + decorator registrations)
print("\n[TEST 5] Getting default registry (manual + decorator)...")
try:
    from src.workflow.registry import get_default_registry
    full_registry = get_default_registry()
    print(f"✅ Full registry has {len(full_registry.functions)} total functions")
except Exception as e:
    print(f"❌ Failed to get default registry: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Verify decorated functions are in the full registry
print("\n[TEST 6] Verifying decorated functions are in full registry...")
decorated_function_names = list(decorator_registry.functions.keys())
for func_name in decorated_function_names:
    if func_name in full_registry.functions:
        print(f"   ✅ {func_name} found in full registry")
    else:
        print(f"   ❌ {func_name} NOT found in full registry")

# Test 7: Test calling a decorated function
print("\n[TEST 7] Testing decorated function call...")
try:
    # Call one of the decorated functions
    result = jayatilake_experiment_cell_functions.advanced_metabolism_decorated(
        context={},
        ph_sensitivity=0.2,
        temperature_effect=1.5,
        enable_lactate_feedback=False
    )
    print(f"✅ Function called successfully")
    print(f"   Result: {result}")
except Exception as e:
    print(f"❌ Function call failed: {e}")
    import traceback
    traceback.print_exc()

# Test 8: Verify metadata is attached to function
print("\n[TEST 8] Verifying metadata is attached to function...")
try:
    func = jayatilake_experiment_cell_functions.advanced_metabolism_decorated
    if hasattr(func, '_workflow_metadata'):
        metadata = func._workflow_metadata
        print(f"✅ Metadata attached to function")
        print(f"   Name: {metadata.name}")
        print(f"   Display Name: {metadata.display_name}")
        print(f"   Category: {metadata.category.value}")
        print(f"   Parameters: {[p.name for p in metadata.parameters]}")
    else:
        print(f"❌ No metadata attached to function")
except Exception as e:
    print(f"❌ Error checking metadata: {e}")

print("\n" + "=" * 80)
print("DECORATOR REGISTRATION TESTS COMPLETE")
print("=" * 80)

