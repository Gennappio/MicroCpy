#!/usr/bin/env python3
"""
Validate all workflow functions for common issues.

This script checks all registered workflow functions for:
1. Adapter import failures (e.g., missing sys.path after refactoring)
2. Missing compatible_kernels parameter
3. Legacy input patterns
4. Parameter type validity
5. Signature-decorator parameter consistency

Run this before committing new workflow functions to catch common mistakes early.

Usage:
    python scripts/validate_functions.py

Exit codes:
    0: All validations passed
    1: Validation errors found
"""

import sys
import inspect
import io
from pathlib import Path
from contextlib import redirect_stdout

# Add engine directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add parent directory so opencellcomms_adapters can be imported
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def validate_functions():
    """
    Validate all registered workflow functions.

    Returns:
        bool: True if all validations passed, False otherwise
    """
    print("=" * 80)
    print("WORKFLOW FUNCTION VALIDATION")
    print("=" * 80)
    print()

    issues = []
    warnings = []

    # =========================================================================
    # Check 0: Adapter import — capture registry output to detect silent failures
    # =========================================================================
    captured = io.StringIO()
    with redirect_stdout(captured):
        from src.workflow.registry import get_default_registry
        registry = get_default_registry()

    registry_output = captured.getvalue()
    if "not available" in registry_output:
        for line in registry_output.strip().split("\n"):
            if "not available" in line:
                issues.append(
                    f"❌ Adapter import failed: {line.strip()}\n"
                    f"   This means adapter functions are NOT registered.\n"
                    f"   Fix: Ensure the parent directory of opencellcomms_adapters is on sys.path"
                )

    # Get all functions from the registry
    all_functions = registry.functions

    # Check if adapter functions are present
    adapter_functions = [
        name for name, m in all_functions.items()
        if "opencellcomms_adapters" in (m.source_file or "") or "opencellcomms_adapters" in (m.module_path or "")
    ]
    if not adapter_functions:
        warnings.append(
            "⚠️  No adapter functions found in registry\n"
            "   Expected functions from opencellcomms_adapters/ to be registered.\n"
            "   This may indicate a silent import failure."
        )
    else:
        print(f"Found {len(adapter_functions)} adapter functions")

    print(f"Checking {len(all_functions)} registered functions...\n")

    from src.workflow.registry import ParameterType

    for name, metadata in all_functions.items():
        # NOTE: Signature validation is done at import time by the decorator
        # We add additional checks here for completeness

        # =====================================================================
        # Check 1: missing compatible_kernels
        # =====================================================================
        if not hasattr(metadata, 'compatible_kernels') or metadata.compatible_kernels is None:
            warnings.append(
                f"⚠️  {name}: missing compatible_kernels\n"
                f"   File: {metadata.source_file}\n"
                f"   Fix: Add compatible_kernels=['biophysics'] to @register_function"
            )

        # =====================================================================
        # Check 2: Using legacy pattern (inputs != ["context"])
        # =====================================================================
        if metadata.inputs != ["context"] and metadata.inputs != []:
            warnings.append(
                f"⚠️  {name}: using legacy input pattern {metadata.inputs}\n"
                f"   File: {metadata.source_file}\n"
                f"   Recommendation: Use inputs=['context'] and access items from context manually"
            )

        # =====================================================================
        # Check 3: Parameter type validity
        # =====================================================================
        valid_types = {t.value for t in ParameterType}
        for param in metadata.parameters:
            if hasattr(param.type, 'value'):
                param_type_str = param.type.value
            else:
                param_type_str = str(param.type)
            if param_type_str not in valid_types:
                issues.append(
                    f"❌ {name}: parameter '{param.name}' has invalid type '{param_type_str}'\n"
                    f"   File: {metadata.source_file}\n"
                    f"   Valid types: {', '.join(sorted(valid_types))}"
                )

        # =====================================================================
        # Check 4: Signature-decorator parameter consistency
        # =====================================================================
        # Find the actual function object to inspect its signature
        try:
            module_path = metadata.module_path
            if module_path:
                import importlib
                mod = importlib.import_module(module_path)
                func = getattr(mod, name, None)
                if func and callable(func):
                    # Get the original function if wrapped
                    original = getattr(func, '__wrapped__', func)
                    sig = inspect.signature(original)
                    sig_params = set(sig.parameters.keys()) - {'kwargs', 'self', 'cls'}

                    declared_params = {p.name for p in metadata.parameters}
                    missing_in_sig = declared_params - sig_params
                    if missing_in_sig:
                        issues.append(
                            f"❌ {name}: decorator declares parameters not in function signature: {missing_in_sig}\n"
                            f"   File: {metadata.source_file}\n"
                            f"   Fix: Add these parameters to the function signature"
                        )
        except Exception:
            pass  # If we can't inspect, skip — decorator already validates at import time

    # =========================================================================
    # Print results
    # =========================================================================
    print()
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print()

    if issues:
        print("ERRORS (must fix):")
        print()
        for issue in issues:
            print(issue)
            print()

    if warnings:
        print("WARNINGS (should fix):")
        print()
        for warning in warnings:
            print(warning)
            print()

    if not issues and not warnings:
        print(f"✅ All {len(all_functions)} functions validated successfully!")
        print()
        return True
    else:
        print(f"Found {len(issues)} errors and {len(warnings)} warnings")
        print()
        if issues:
            print("❌ Validation FAILED - fix errors before committing")
            return False
        else:
            print("⚠️  Validation passed with warnings - consider fixing")
            return True


if __name__ == "__main__":
    success = validate_functions()
    sys.exit(0 if success else 1)
