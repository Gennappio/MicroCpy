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
        category="INTRACELLULAR",  # legacy registry metadata; graph controls execution
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
import warnings
from typing import Callable, List, Dict, Any, Optional, Union
from functools import wraps

from src.workflow.registry import (
    FunctionRegistry,
    FunctionMetadata,
    FunctionCategory,
    ParameterType,
    ParameterDefinition
)


# Migration policy for the typed `env: BiologicalContext` API.
#   False -> warn on legacy `context`-dict signatures (gradual migration).
#   True  -> reject them at registration (after migration is complete).
# Flip this single flag to make the typed env mandatory.
ENFORCE_TYPED_ENV = False

# Whether to actually emit the per-function "legacy context-dict signature"
# UserWarning. This nudge fires once for EVERY legacy function at import time,
# and ~90 functions across the engine + adapters still use that signature — so
# leaving it on floods stdout/stderr on every single run (and the GUI tags all
# stderr as "[ERROR]", making benign nudges look like failures). It is a
# developer-only migration aid, so default it OFF and let a developer opt in
# with `OCC_WARN_LEGACY_CONTEXT=1`. Has no effect when ENFORCE_TYPED_ENV is on
# (that path raises regardless).
WARN_LEGACY_CONTEXT = os.environ.get("OCC_WARN_LEGACY_CONTEXT", "0").lower() not in ("0", "", "false", "no")

# Whether an undeclared parameter is a HARD error. A typed-env function arg that
# is neither declared in parameters=[...] nor given a default is silently dropped
# by extraction, leaving a node the GUI can neither show nor wire (a socketless
# "bad node"). Default OFF: warn and flag the function (validation_errors) so one
# bad node never aborts a whole plugin import, and the GUI can render it as a
# "fix me" node. Opt in with OCC_ENFORCE_PARAM_DECLARATIONS=1 in CI to block bad
# code at merge. The typed-env codebase is clean today, so flipping this on in CI
# breaks nothing while preventing any future regression.
ENFORCE_PARAM_DECLARATIONS = os.environ.get("OCC_ENFORCE_PARAM_DECLARATIONS", "0").lower() not in ("0", "", "false", "no")


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


def _validate_parameter_declarations(func, param_definitions, func_name, source_file) -> List[str]:
    """Catch the 'badly written node' that silently loses its GUI socket.

    For a typed-env function (first arg ``env``) the context is reached via
    ``env.x``, so every OTHER signature argument is a user parameter and must end
    up as an editable socket. ``_extract_parameters_from_signature`` already turns
    a declared param OR a defaulted arg into a socket, but it SILENTLY DROPS an
    undeclared argument that has no default — leaving the node with a parameter the
    GUI can neither display nor wire. Flag exactly that case.

    Legacy ``context``-dict functions are grandfathered: they inject context
    objects (population, simulator, ...) as named args, which are not user
    parameters, so the same rule would false-positive.
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    if not params or params[0].name != 'env':
        return []
    socketed = {p.name for p in param_definitions}
    errors = []
    for p in params[1:]:
        if p.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue
        if p.name in ('context', 'self'):
            continue
        if p.name not in socketed:
            errors.append(
                f"'{func_name}' ({source_file}): parameter '{p.name}' is in the "
                f"signature but is neither declared in @register_function(parameters=[...]) "
                f"nor given a default, so it has no editable socket in the GUI. "
                f"Add it to parameters=[...] (or give it a default)."
            )
    return errors


def _defaults_equal(a: Any, b: Any) -> bool:
    """Compare two parameter defaults, treating int/float as numerically equal
    (so 2 == 2.0) but keeping bool distinct from int (True != 1)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or a == b and type(a) is type(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return a == b


def _validate_parameter_defaults(func, param_definitions, func_name, source_file) -> List[str]:
    """Catch a decorator/signature default mismatch — a silent correctness bug.

    The GUI shows (and a removed parameter node falls back to) the default declared
    in ``@register_function(parameters=[...])``, while Python actually runs the
    *signature* default. If those disagree, a node left at "its default" runs with a
    different value than the GUI displays (e.g. setup_domain showed dimensions=2 but
    ran dimensions=3). They must be identical.

    The ``None`` sentinel is allowed: ``def f(x=None)`` with a declared dict/list/
    scalar default is the standard pattern for mutable defaults (the real default is
    resolved inside the function), so a signature default of ``None`` never conflicts.
    """
    sig = inspect.signature(func)
    errors = []
    for pd in param_definitions:
        if pd.name not in sig.parameters:
            continue
        sig_default = sig.parameters[pd.name].default
        if sig_default is inspect.Parameter.empty or sig_default is None:
            continue
        if not _defaults_equal(sig_default, pd.default):
            errors.append(
                f"'{func_name}' ({source_file}): parameter '{pd.name}' default mismatch — "
                f"@register_function declares {pd.default!r} but the signature default is "
                f"{sig_default!r}. The GUI shows the declared default while the function runs "
                f"the signature default, so they must be identical. Set the signature default "
                f"to {pd.default!r} (or update the declared default to match)."
            )
    return errors


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


def _validate_function_signature(
    func: Callable,
    input_list: List[str],
    func_name: str,
    source_file: str
) -> None:
    """
    Validate function signature against declared inputs to catch common mistakes.

    This catches the most common error: declaring inputs in the decorator that
    don't have matching parameters in the function signature.

    Args:
        func: The function to validate
        input_list: List of inputs declared in @register_function
        func_name: Name of the function (for error messages)
        source_file: Source file path (for error messages)

    Raises:
        ValueError: If validation fails
    """
    # Get function signature
    sig = inspect.signature(func)
    params = set(sig.parameters.keys())

    # Remove special parameters that don't need to match inputs
    params.discard('kwargs')
    params.discard('args')

    # Check for mismatches
    declared_inputs = set(input_list)

    # Special case: 'context' can be in inputs even if not in signature
    # (for legacy compatibility)
    declared_inputs_to_check = declared_inputs - {'context'}

    # Find inputs that are declared but not in signature
    missing_params = declared_inputs_to_check - params

    if missing_params:
        # Build helpful error message
        error_msg = (
            f"\n{'='*80}\n"
            f"❌ WORKFLOW FUNCTION VALIDATION ERROR\n"
            f"{'='*80}\n"
            f"Function: {func_name}\n"
            f"File: {source_file}\n"
            f"\n"
            f"Problem: The @register_function decorator declares inputs that are\n"
            f"         missing from the function signature.\n"
            f"\n"
            f"Declared inputs: {sorted(declared_inputs)}\n"
            f"Missing from signature: {sorted(missing_params)}\n"
            f"\n"
            f"This is a common mistake! The executor will try to pass these as\n"
            f"kwargs, but they won't be received by the function.\n"
            f"\n"
            f"RECOMMENDED FIX (Pattern 1 - Simplest):\n"
            f"  Change decorator to: inputs=['context']\n"
            f"  Change signature to: def {func_name}(context=None, ...)\n"
            f"  Access items manually: population = context.get('population')\n"
            f"\n"
            f"ALTERNATIVE FIX (Pattern 2 - Legacy):\n"
            f"  Add missing parameters to signature:\n"
            f"  def {func_name}({', '.join(sorted(missing_params))}=None, context=None, ...)\n"
            f"\n"
            f"See src/workflow/functions/_TEMPLATE.py for the recommended pattern.\n"
            f"{'='*80}\n"
        )
        raise ValueError(error_msg)


def register_function(
    display_name: str,
    description: str,
    category: Union[str, FunctionCategory],
    parameters: Optional[List[Dict[str, Any]]] = None,
    inputs: Optional[List[str]] = None,
    outputs: Optional[List[str]] = None,
    cloneable: bool = False,
    compatible_kernels: Optional[List[str]] = None,
    requires: Optional[List[str]] = None,
    operates_on: Optional[List[str]] = None,
    contract: Optional[Dict[str, Any]] = None,
    typed_env_exempt: bool = False
) -> Callable:
    """
    Decorator for registering workflow functions.

    Usage:
        @register_function(
            display_name="Advanced Metabolism",
            description="Sophisticated metabolism model with pH effects",
            category="INTRACELLULAR",  # legacy registry metadata
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
        category: Legacy registry category. This is compatibility metadata for
            older registry consumers; v2 execution is graph/subworkflow-driven.
        parameters: Optional list of parameter definitions (auto-inferred if not provided)
        inputs: Optional list of input names (auto-detected from signature if not provided)
        outputs: Optional list of output names
        cloneable: Whether the function can be cloned/customized in the GUI
        compatible_kernels: List of kernel names this function is compatible with (None or ["*"] = all kernels)
        typed_env_exempt: Set True for functions that intentionally use the raw
            `context` dict (e.g. PhysiCell-facade functions with no biological
            context, or core functions doing low-level population/state surgery).
            Suppresses the migration-to-`env` warning. Prefer `env` for new and
            cell/substance/gene-centric functions.
        requires: Capability tokens this function needs from the active kernel.
            A workflow fails to load (loudly) if its kernel does not provide all
            of these. Structural tokens are bare context keys the function reads
            (e.g. "population", "simulator", "gene_networks"). Reserved ontology
            tokens use the form "substance:<name>", "gene:<name>",
            "phenotype:<name>". None/[] means the function runs under any kernel.
        contract: Optional read/write contract used by the GUI and workflow
            validator. This is warning-mode metadata; it does not change runtime
            permissions yet.

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

        # =====================================================================
        # VALIDATION: Check for common mistakes
        # =====================================================================
        _validate_function_signature(func, input_list, func_name, source_file)

        # A declared default that disagrees with the signature default is always a
        # bug (the GUI would show one value while the function runs another), so
        # fail registration loudly — same policy as the input/signature check above.
        default_mismatches = _validate_parameter_defaults(func, param_definitions, func_name, source_file)
        if default_mismatches:
            raise ValueError(
                "\n" + "=" * 80 + "\n❌ PARAMETER DEFAULT MISMATCH\n" + "=" * 80 + "\n"
                + "\n".join(default_mismatches)
            )

        # Nudge migration toward the typed `env: BiologicalContext` API. Legacy
        # `context`-dict functions keep working (they get no type safety and
        # access the context by string key), so warn rather than break — unless
        # ENFORCE_TYPED_ENV is on, in which case reject.
        first_param = next(iter(inspect.signature(func).parameters.values()), None)
        if not typed_env_exempt and first_param is not None and first_param.name == 'context':
            message = (
                f"'{func_name}' ({source_file}) uses the legacy context-dict "
                f"signature. Prefer 'env: BiologicalContext' for typed, "
                f"duck-typing-free access to cells/substances/genes."
            )
            if ENFORCE_TYPED_ENV:
                raise ValueError(
                    f"\n{'='*80}\n❌ TYPED ENV REQUIRED\n{'='*80}\n{message}\n{'='*80}\n"
                )
            if WARN_LEGACY_CONTEXT:
                warnings.warn(message, stacklevel=2)

        # Catch undeclared parameters that would silently lose their GUI socket.
        # Warn + flag by default; raise only under OCC_ENFORCE_PARAM_DECLARATIONS.
        param_validation_errors = _validate_parameter_declarations(
            func, param_definitions, func_name, source_file
        )
        if param_validation_errors:
            message = "\n".join(param_validation_errors)
            if ENFORCE_PARAM_DECLARATIONS:
                raise ValueError(
                    f"\n{'='*80}\n❌ UNDECLARED PARAMETER(S)\n{'='*80}\n{message}\n{'='*80}\n"
                )
            warnings.warn(message, stacklevel=2)

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
            source_file=source_file,
            compatible_kernels=compatible_kernels,
            requires=requires,
            operates_on=operates_on,
            contract=contract,
            validation_errors=param_validation_errors
        )

        # Detect silent function-name collisions. Re-registering the same name
        # from the SAME source file is fine (a module reload re-runs the
        # decorator). A *different* file claiming an already-registered name is
        # a conflict: hard-error when a plugin (adapter) is involved — the case
        # the plugin system must never allow silently — and warn for
        # engine-core vs engine-core duplicates (pre-existing, tracked).
        existing = _decorator_registry.get(func_name)
        if existing is not None and existing.source_file != source_file:
            involves_plugin = (
                'opencellcomms_adapters' in (existing.source_file or '')
                or 'opencellcomms_adapters' in (source_file or '')
            )
            collision_msg = (
                f"Function name '{func_name}' is already registered from "
                f"{existing.source_file!r}; {source_file!r} would overwrite it. "
                f"Function names must be unique across plugins."
            )
            if involves_plugin:
                raise ValueError(
                    f"\n{'='*80}\n❌ DUPLICATE FUNCTION NAME\n{'='*80}\n"
                    f"{collision_msg}\n{'='*80}\n"
                )
            warnings.warn(collision_msg, stacklevel=2)

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
