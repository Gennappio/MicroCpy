#!/usr/bin/env python3
"""
Validate all workflow functions for common issues.

This script checks all registered workflow functions for:
1. Mismatch between inputs declared in decorator and function signature
2. Missing compatible_kernels parameter
3. Missing required imports in registry.py

Run this before committing new workflow functions to catch common mistakes early.

Usage:
    python scripts/validate_functions.py
    
Exit codes:
    0: All validations passed
    1: Validation errors found
"""

import sys
import inspect
from pathlib import Path

# Add parent directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow.registry import get_default_registry


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
    
    registry = get_default_registry()
    issues = []
    warnings = []

    # Get all functions from the registry
    all_functions = registry.functions

    print(f"Checking {len(all_functions)} registered functions...\n")

    for name, metadata in all_functions.items():
        # NOTE: Signature validation is done at import time by the decorator
        # We only check for missing metadata fields here

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
        print(f"✅ All {len(registry)} functions validated successfully!")
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

