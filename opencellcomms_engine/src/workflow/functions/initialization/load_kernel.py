"""
Kernel loading workflow function.

This function loads a simulation kernel (biophysics, physics, economics, etc.)
and initializes the context with kernel-specific core keys and interfaces.
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.workflow.kernel_registry import get_kernel, list_kernels


@register_function(
    display_name="Load Kernel",
    description="Load a simulation kernel (biophysics, physics, economics, etc.) and initialize context",
    category="INITIALIZATION",
    parameters=[
        {
            "name": "kernel_name",
            "type": "STRING",
            "description": "Name of the kernel to load (biophysics, physics, economics, etc.)",
            "default": "biophysics",
            "required": True
        },
        {
            "name": "kernel_params",
            "type": "DICT",
            "description": "Kernel-specific initialization parameters",
            "default": {},
            "required": False
        }
    ],
    inputs=["context"],
    outputs=["kernel_type"],
    compatible_kernels=["*"]  # This function works with all kernels (it's the loader!)
)
def load_kernel(
    context: Dict[str, Any],
    kernel_name: str = "biophysics",
    kernel_params: Optional[Dict[str, Any]] = None,
    **kwargs
) -> bool:
    """
    Load a simulation kernel and initialize the context.
    
    This function:
    1. Retrieves the kernel definition from the registry
    2. Registers core context keys with write policies
    3. Calls the kernel's initialization function
    4. Validates that required interfaces are available (optional)
    
    Args:
        context: Workflow context dictionary
        kernel_name: Name of the kernel to load (default: "biophysics")
        kernel_params: Kernel-specific parameters (default: {})
        **kwargs: Additional arguments (ignored)
        
    Returns:
        True if kernel loaded successfully, False otherwise
    """
    if kernel_params is None:
        kernel_params = {}
    
    print(f"\n{'='*80}")
    print(f"[LOAD_KERNEL] Loading kernel: {kernel_name}")
    print(f"{'='*80}")
    
    # Get kernel definition from registry
    kernel = get_kernel(kernel_name)
    
    if kernel is None:
        available_kernels = list_kernels()
        print(f"[LOAD_KERNEL] ERROR: Kernel '{kernel_name}' not found in registry")
        print(f"[LOAD_KERNEL] Available kernels: {available_kernels}")
        return False
    
    print(f"[LOAD_KERNEL] Kernel found: {kernel.description}")
    print(f"[LOAD_KERNEL] Core keys: {list(kernel.core_keys.keys())}")
    print(f"[LOAD_KERNEL] Required interfaces: {list(kernel.required_interfaces.keys())}")
    
    # Call kernel initializer
    print(f"[LOAD_KERNEL] Calling kernel initializer...")
    success = kernel.initializer(context, kernel_params)
    
    if not success:
        print(f"[LOAD_KERNEL] ERROR: Kernel initialization failed")
        return False
    
    print(f"[LOAD_KERNEL] Kernel '{kernel_name}' loaded successfully")
    print(f"{'='*80}\n")
    
    return True


@register_function(
    display_name="Validate Kernel Interfaces",
    description="Validate that all required kernel interfaces are present in context",
    category="UTILITY",
    parameters=[
        {
            "name": "kernel_name",
            "type": "STRING",
            "description": "Name of the kernel to validate",
            "default": "biophysics",
            "required": True
        }
    ],
    inputs=["context"],
    outputs=[],
    compatible_kernels=["*"]
)
def validate_kernel_interfaces(
    context: Dict[str, Any],
    kernel_name: str = "biophysics",
    **kwargs
) -> bool:
    """
    Validate that all required kernel interfaces are present in context.
    
    This is an optional validation function that can be called after
    initialization to ensure all required objects implement the correct interfaces.
    
    Args:
        context: Workflow context dictionary
        kernel_name: Name of the kernel to validate
        **kwargs: Additional arguments (ignored)
        
    Returns:
        True if all interfaces are valid, False otherwise
    """
    print(f"\n[VALIDATE_KERNEL] Validating interfaces for kernel: {kernel_name}")
    
    # Get kernel definition
    kernel = get_kernel(kernel_name)
    
    if kernel is None:
        print(f"[VALIDATE_KERNEL] ERROR: Kernel '{kernel_name}' not found")
        return False
    
    # Check each required interface
    all_valid = True
    for context_key, interface_class in kernel.required_interfaces.items():
        obj = context.get(context_key)
        
        if obj is None:
            print(f"[VALIDATE_KERNEL] WARNING: Required key '{context_key}' not found in context")
            all_valid = False
            continue
        
        if not isinstance(obj, interface_class):
            print(f"[VALIDATE_KERNEL] ERROR: Object at '{context_key}' does not implement {interface_class.__name__}")
            print(f"[VALIDATE_KERNEL]   Expected: {interface_class}")
            print(f"[VALIDATE_KERNEL]   Got: {type(obj)}")
            all_valid = False
        else:
            print(f"[VALIDATE_KERNEL] ✓ '{context_key}' implements {interface_class.__name__}")
    
    if all_valid:
        print(f"[VALIDATE_KERNEL] All interfaces valid for kernel '{kernel_name}'")
    else:
        print(f"[VALIDATE_KERNEL] Some interfaces are invalid or missing")
    
    return all_valid

