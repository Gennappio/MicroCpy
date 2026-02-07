"""
Decorator-based function registration system for OpenCellComms workflow.

This module provides decorators that allow functions to be defined and registered
in the same place, eliminating the need for manual registration in registry.py.

================================================================================
CONTEXT-BASED FUNCTION ARCHITECTURE
================================================================================

All workflow functions follow a unified context-based pattern:

1. SIGNATURE: Functions receive a single `context: Dict[str, Any]` parameter
   plus any function-specific parameters and **kwargs.

2. DECORATOR: Functions must declare `inputs=["context"]` in @register_function
   to receive the workflow context.

3. CONTEXT CONTENTS: The context dictionary contains:
   - population: Cell population object (mutable)
   - simulator: Diffusion simulator object (mutable)
   - config: Configuration object
   - dt: Time step (hours)
   - current_step: Current simulation step number
   - _executor: Reference to workflow executor (for macrostep functions)
   - Custom keys added by other functions

4. VALIDATION: Functions should validate required context items and handle
   missing items gracefully (skip with warning, not crash).

5. MODIFICATION: Functions modify context items in-place. The context is
   shared across all functions in a workflow execution.

Example:
    @register_function(
        display_name="My Function",
        description="Does something useful",
        category="INTRACELLULAR",
        parameters=[{"name": "threshold", "type": "FLOAT", "default": 0.5}],
        inputs=["context"],
        outputs=[],
        cloneable=True
    )
    def my_function(context: Dict[str, Any], threshold: float = 0.5, **kwargs) -> None:
        population = context.get('population')
        if population is None:
            print("[my_function] No population in context - skipping")
            return
        # ... function logic ...

See run_diffusion_solver.py for the canonical reference implementation.
================================================================================
"""

import inspect
import os
from typing import Callable, List, Dict, Any, Optional, Union
from functools import wraps

from src.workflow.registry import (
    FunctionRegistry,
    FunctionMetadata,
    FunctionCategory,
    ParameterType,
    ParameterDefinition
)


# Global registry instance for decorator-based registrations
_decorator_registry = FunctionRegistry()


def get_decorator_registry() -> FunctionRegistry:
    """Get the global decorator-based registry."""
    return _decorator_registry


def _infer_parameter_type(default_value: Any) -> ParameterType:
    """
    Infer parameter type from default value.
    
    Args:
        default_value: The default value of the parameter
        
    Returns:
        ParameterType: The inferred parameter type
    """
    if isinstance(default_value, bool):
        return ParameterType.BOOL
    elif isinstance(default_value, int):
        return ParameterType.INT
    elif isinstance(default_value, float):
        return ParameterType.FLOAT
    elif isinstance(default_value, str):
        return ParameterType.STRING
    elif isinstance(default_value, list):
        return ParameterType.LIST
    elif isinstance(default_value, dict):
        return ParameterType.DICT
    else:
        # Default to STRING for unknown types
        return ParameterType.STRING


def _extract_parameters_from_signature(func: Callable, param_definitions: Optional[List[Dict[str, Any]]] = None) -> List[ParameterDefinition]:
    """
    Extract parameter definitions from function signature.
    
    Args:
        func: The function to inspect
        param_definitions: Optional list of parameter definition dicts from decorator
        
    Returns:
        List of ParameterDefinition objects
    """
    sig = inspect.signature(func)
    parameters = []
    
    # Create a lookup dict for provided parameter definitions
    param_def_lookup = {}
    if param_definitions:
        for param_def in param_definitions:
            param_def_lookup[param_def['name']] = param_def
    
    for param_name, param in sig.parameters.items():
        # Skip **kwargs and *args
        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue
            
        # Skip 'context' parameter as it's automatically provided
        if param_name == 'context':
            continue
        
        # Check if we have a definition for this parameter
        if param_name in param_def_lookup:
            param_def = param_def_lookup[param_name]
            
            # Convert type string to ParameterType enum if needed
            param_type = param_def.get('type', ParameterType.STRING)
            if isinstance(param_type, str):
                param_type = ParameterType[param_type.upper()]
            
            parameters.append(ParameterDefinition(
                name=param_name,
                type=param_type,
                description=param_def.get('description', f"Parameter {param_name}"),
                default=param_def.get('default', param.default if param.default != inspect.Parameter.empty else None),
                required=param_def.get('required', param.default == inspect.Parameter.empty),
                min_value=param_def.get('min_value'),
                max_value=param_def.get('max_value'),
                options=param_def.get('options')
            ))
        elif param.default != inspect.Parameter.empty:
            # Auto-infer from default value
            param_type = _infer_parameter_type(param.default)
            parameters.append(ParameterDefinition(
                name=param_name,
                type=param_type,
                description=f"Parameter {param_name}",
                default=param.default,
                required=False
            ))
    
    return parameters


def _extract_inputs_from_signature(func: Callable) -> List[str]:
    """
    Extract input parameter names from function signature (excluding **kwargs).
    
    Args:
        func: The function to inspect
        
    Returns:
        List of input parameter names
    """
    sig = inspect.signature(func)
    inputs = []
    
    for param_name, param in sig.parameters.items():
        # Skip **kwargs and *args
        if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue
        inputs.append(param_name)
    
    return inputs


def register_function(
    display_name: str,
    description: str,
    category: Union[str, FunctionCategory],
    parameters: Optional[List[Dict[str, Any]]] = None,
    inputs: Optional[List[str]] = None,
    outputs: Optional[List[str]] = None,
    cloneable: bool = False,
    compatible_kernels: Optional[List[str]] = None
) -> Callable:
    """
    Decorator for registering workflow functions.

    Usage:
        @register_function(
            display_name="Advanced Metabolism",
            description="Sophisticated metabolism model with pH effects",
            category="INTRACELLULAR",
            parameters=[
                {"name": "ph_sensitivity", "type": "FLOAT", "default": 0.1},
                {"name": "temperature_effect", "type": "FLOAT", "default": 1.0}
            ],
            compatible_kernels=["biophysics"]
        )
        def advanced_metabolism(context, ph_sensitivity=0.1, temperature_effect=1.0, **kwargs):
            # Function implementation
            pass

    Args:
        display_name: Human-readable name for the GUI
        description: Description of what the function does
        category: Function category (INITIALIZATION, INTRACELLULAR, DIFFUSION, INTERCELLULAR, FINALIZATION, UTILITY)
        parameters: Optional list of parameter definitions (auto-inferred if not provided)
        inputs: Optional list of input names (auto-detected from signature if not provided)
        outputs: Optional list of output names
        cloneable: Whether the function can be cloned/customized in the GUI
        compatible_kernels: List of kernel names this function is compatible with (None or ["*"] = all kernels)

    Returns:
        Decorated function with registration metadata
    """
    def decorator(func: Callable) -> Callable:
        # Convert category string to enum if needed
        if isinstance(category, str):
            category_enum = FunctionCategory[category.upper()]
        else:
            category_enum = category

        # Extract function name
        func_name = func.__name__

        # Get module path
        module_path = func.__module__

        # Get source file path
        try:
            source_file = inspect.getfile(func)
            # Make it relative to the project root (opencellcomms_engine)
            if 'opencellcomms_engine' in source_file:
                source_file = source_file.split('opencellcomms_engine/')[-1]
            elif 'opencellcomms_engine' in source_file:
                # Legacy fallback
                source_file = source_file.split('opencellcomms_engine/')[-1]
        except (TypeError, OSError):
            source_file = ""

        # Extract or use provided parameters
        if parameters is not None:
            param_definitions = _extract_parameters_from_signature(func, parameters)
        else:
            param_definitions = _extract_parameters_from_signature(func)

        # Extract or use provided inputs
        if inputs is not None:
            input_list = inputs
        else:
            input_list = _extract_inputs_from_signature(func)

        # Create metadata
        metadata = FunctionMetadata(
            name=func_name,
            display_name=display_name,
            description=description,
            category=category_enum,
            parameters=param_definitions,
            inputs=input_list,
            outputs=outputs or [],
            cloneable=cloneable,
            module_path=module_path,
            source_file=source_file
        )

        # Register in the decorator registry
        _decorator_registry.register(metadata)

        # Add metadata to function for introspection
        func._workflow_metadata = metadata

        return func

    return decorator


def merge_registries(manual_registry: FunctionRegistry, decorator_registry: FunctionRegistry) -> FunctionRegistry:
    """
    Merge manual and decorator-based registries.

    Decorator-based registrations take precedence over manual ones if there's a conflict.

    Args:
        manual_registry: Registry with manual registrations
        decorator_registry: Registry with decorator-based registrations

    Returns:
        Merged registry
    """
    merged = FunctionRegistry()

    # Add all manual registrations first
    for name, metadata in manual_registry.functions.items():
        merged.register(metadata)

    # Add decorator registrations (overwriting manual ones if they exist)
    for name, metadata in decorator_registry.functions.items():
        merged.register(metadata)

    return merged

