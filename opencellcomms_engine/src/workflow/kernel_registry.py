"""
Kernel registry system for OpenCellComms workflow manager.

This module provides a formal registry system for simulation kernels, allowing
OpenCellComms to support different simulation domains (biophysics, physics, economics, etc.).

A kernel defines:
- Core context keys and their write policies
- Required interfaces for type checking
- Initialization logic
- Compatible function categories
"""

from dataclasses import dataclass
from typing import Dict, List, Type, Any, Callable, Optional
from abc import ABC

from src.workflow.observability.validated_context import (
    WRITE_POLICY_READ_ONLY,
    WRITE_POLICY_WRITE_ONCE,
    WRITE_POLICY_MUTABLE
)


@dataclass
class KernelDefinition:
    """
    Metadata and initialization logic for a simulation kernel.
    
    A kernel defines the core objects and context structure for a specific
    simulation domain (biophysics, physics, economics, etc.).
    """
    name: str
    description: str
    
    # Context keys this kernel uses and their write policies
    core_keys: Dict[str, str]  # {key_name: write_policy}
    
    # Interfaces this kernel requires (for type validation)
    required_interfaces: Dict[str, Type[ABC]]  # {context_key: InterfaceClass}
    
    # Initialization function that sets up the kernel
    # Returns True if successful, False otherwise
    initializer: Callable[[Dict[str, Any], Dict[str, Any]], bool]
    
    # Compatible function categories (optional - for filtering in GUI)
    compatible_categories: Optional[List[str]] = None


def _initialize_biophysics(context: Dict[str, Any], params: Dict[str, Any]) -> bool:
    """
    Initialize biophysics kernel - registers context keys only.
    
    This is Option A (minimal) - just registers the core keys that the biophysics
    kernel uses. The actual objects (population, simulator, gene_network, etc.)
    are created by existing setup functions (setup_domain, setup_population, etc.).
    
    Args:
        context: Workflow context dictionary (should be ValidatedContext)
        params: Kernel-specific parameters (unused for biophysics)
        
    Returns:
        True if initialization successful
    """
    # Register core keys with write policies
    if hasattr(context, 'register_core_key'):
        # Write-once keys (set during initialization, never changed)
        context.register_core_key('population', WRITE_POLICY_WRITE_ONCE)
        context.register_core_key('simulator', WRITE_POLICY_WRITE_ONCE)
        context.register_core_key('gene_network', WRITE_POLICY_WRITE_ONCE)
        context.register_core_key('mesh_manager', WRITE_POLICY_WRITE_ONCE)
        
        # Mutable keys (can be modified during simulation)
        context.register_core_key('gene_networks', WRITE_POLICY_MUTABLE)
    
    # Mark which kernel is loaded
    context['kernel_type'] = 'biophysics'
    
    print("[KERNEL] Biophysics kernel initialized - core keys registered")
    return True


# Global kernel registry
KERNEL_REGISTRY: Dict[str, KernelDefinition] = {}


def register_kernel(kernel: KernelDefinition) -> None:
    """Register a kernel in the global registry."""
    KERNEL_REGISTRY[kernel.name] = kernel
    print(f"[KERNEL REGISTRY] Registered kernel: {kernel.name}")


def get_kernel(kernel_name: str) -> Optional[KernelDefinition]:
    """
    Get a kernel definition by name.
    
    Args:
        kernel_name: Name of the kernel to retrieve
        
    Returns:
        KernelDefinition if found, None otherwise
    """
    return KERNEL_REGISTRY.get(kernel_name)


def list_kernels() -> List[str]:
    """
    List all registered kernel names.
    
    Returns:
        List of kernel names
    """
    return list(KERNEL_REGISTRY.keys())


# Register the biophysics kernel
from src.interfaces.base import (
    ICellPopulation,
    ISubstanceSimulator,
    IGeneNetwork,
    IMeshManager
)

BIOPHYSICS_KERNEL = KernelDefinition(
    name="biophysics",
    description="Biophysics simulation kernel for cell-based models with gene networks and diffusion",
    core_keys={
        'population': WRITE_POLICY_WRITE_ONCE,
        'simulator': WRITE_POLICY_WRITE_ONCE,
        'gene_network': WRITE_POLICY_WRITE_ONCE,
        'mesh_manager': WRITE_POLICY_WRITE_ONCE,
        'gene_networks': WRITE_POLICY_MUTABLE,
    },
    required_interfaces={
        'population': ICellPopulation,
        'simulator': ISubstanceSimulator,
        'gene_network': IGeneNetwork,
        'mesh_manager': IMeshManager,
    },
    initializer=_initialize_biophysics,
    compatible_categories=["INITIALIZATION", "INTRACELLULAR", "DIFFUSION", "INTERCELLULAR", "FINALIZATION", "UTILITY"]
)

register_kernel(BIOPHYSICS_KERNEL)

