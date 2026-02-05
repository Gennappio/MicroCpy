#!/usr/bin/env python
"""
Diagnostic script to check if update_gene_networks_hierarchical is properly registered.
"""

from src.workflow.registry import get_default_registry

def main():
    print("=" * 80)
    print("CHECKING HIERARCHICAL GENE NETWORK FUNCTION REGISTRATION")
    print("=" * 80)
    
    # Get registry
    registry = get_default_registry()
    
    # Check if function exists
    func_name = 'update_gene_networks_hierarchical'
    func_meta = registry.get(func_name)
    
    if not func_meta:
        print(f"\n❌ ERROR: Function '{func_name}' NOT found in registry!")
        print("\nAvailable intracellular functions:")
        for name, meta in registry.functions.items():
            if meta.category.value == 'INTRACELLULAR':
                print(f"  - {name}")
        return
    
    print(f"\n✅ Function '{func_name}' is registered!")
    print("\nFunction Metadata:")
    print(f"  Display Name: {func_meta.display_name}")
    print(f"  Description: {func_meta.description}")
    print(f"  Category: {func_meta.category.value}")
    print(f"  Source File: {func_meta.source_file}")
    print(f"  Module Path: {func_meta.module_path}")
    print(f"  Cloneable: {func_meta.cloneable}")
    
    print(f"\nInputs ({len(func_meta.inputs)}):")
    for inp in func_meta.inputs:
        print(f"  - {inp}")
    
    print(f"\nOutputs ({len(func_meta.outputs)}):")
    if func_meta.outputs:
        for out in func_meta.outputs:
            print(f"  - {out}")
    else:
        print("  (none)")
    
    print(f"\nParameters ({len(func_meta.parameters)}):")
    for param in func_meta.parameters:
        print(f"  - {param.name}")
        print(f"      Type: {param.type}")
        print(f"      Default: {param.default}")
        print(f"      Description: {param.description}")
        print(f"      Required: {param.required}")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS:")
    print("=" * 80)
    
    # Check if parameters look correct
    param_names = [p.name for p in func_meta.parameters]
    expected_params = ['propagation_steps', 'verbose']
    
    if set(param_names) == set(expected_params):
        print("✅ Parameters look correct")
    else:
        print(f"⚠️  Parameters mismatch!")
        print(f"   Expected: {expected_params}")
        print(f"   Got: {param_names}")
    
    # Check inputs
    if func_meta.inputs == ['population']:
        print("✅ Inputs look correct")
    else:
        print(f"⚠️  Inputs mismatch!")
        print(f"   Expected: ['population']")
        print(f"   Got: {func_meta.inputs}")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. If the function is registered correctly (✅ above), restart the GUI server")
    print("2. The GUI server caches the registry on startup")
    print("3. After restarting, the function should appear in the GUI")
    print("4. If still not working, check browser console for errors")
    print("=" * 80)

if __name__ == '__main__':
    main()

