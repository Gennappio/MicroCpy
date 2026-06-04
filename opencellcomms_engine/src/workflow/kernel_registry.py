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

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Type, Any, Callable, Optional, Union
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

    # Stable identifier (defaults to `name`) and version, stored in workflow
    # files for provenance.
    kernel_id: Optional[str] = None
    version: str = "1.0"

    # Optional dispatch hook. When set, the executor hands the whole workflow
    # off to this callable — `(workflow, context) -> context` — instead of
    # running the native Python stage loop. Facade kernels that delegate to an
    # external engine (e.g. PhysiCell's codegen→make→spawn backend) set this and
    # register themselves from their adapter, so the engine stays agnostic of
    # any specific external kernel. The native `biophysics` kernel leaves this
    # None and uses the stage executor.
    backend: Optional[Callable[[Any, Dict[str, Any]], Dict[str, Any]]] = None

    # Extra capability tokens this kernel provides beyond its core context keys.
    # Reserved ontology tokens use the form "substance:<name>", "gene:<name>",
    # "phenotype:<name>"; structural tokens are bare context keys.
    extra_provides: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.kernel_id is None:
            self.kernel_id = self.name

    def provides(self) -> Set[str]:
        """Capability tokens this kernel guarantees in the context.

        Structural tokens are derived from `core_keys` (the context keys the
        kernel sets up); `extra_provides` adds any further declared capabilities.
        A function is compatible when its `requires` is a subset of this set.
        """
        return set(self.core_keys.keys()) | set(self.extra_provides)


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
    """Register a kernel in the global registry.

    This runs at import time for the native `biophysics` kernel and again for
    each facade kernel when its adapter is imported, so it announces itself only
    under OCC_VERBOSE_STARTUP=1 — otherwise it's startup noise on every run.
    Registration is cheap (just storing the definition); the heavy backends are
    imported lazily when a workflow actually selects that kernel.
    """
    KERNEL_REGISTRY[kernel.name] = kernel
    if os.environ.get("OCC_VERBOSE_STARTUP", "0").lower() not in ("0", "", "false", "no"):
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
    compatible_categories=["INITIALIZATION", "INTRACELLULAR", "DIFFUSION", "INTERCELLULAR", "FINALIZATION", "UTILITY"],
    kernel_id="biophysics",
    version="1.0",
)

register_kernel(BIOPHYSICS_KERNEL)


# -- Facade kernels register themselves from their adapter -------------------
#
# The PhysiCell/PhysiBoSS facade kernel is NOT declared here: it sets a
# `backend` dispatch hook and lives entirely in its adapter
# (opencellcomms_adapters/PhysiBoSS/register.py), so the engine stays agnostic
# of any specific external engine. See docs/Physicell_Facade_plan.md.


# -- Data-file kernels -------------------------------------------------------
#
# Lightweight kernels declared as JSON so the default biological kernel can be
# modified or extended without editing engine code. A data kernel only needs to
# declare what it `provides`; it has no Python initializer or interfaces (those
# are only required by the built-in kernels above).

def _make_data_initializer(kernel_name: str) -> Callable[[Dict[str, Any], Dict[str, Any]], bool]:
    def _init(context: Dict[str, Any], params: Dict[str, Any]) -> bool:
        context['kernel_type'] = kernel_name
        return True
    return _init


def load_kernel_files(directory: Union[str, Path]) -> int:
    """Load and register data-file kernels from `directory`/*.json.

    Each file declares: {kernel_id, name, description, provides,
    compatible_categories, version}. Missing or malformed files are skipped
    with a warning. Returns the number of kernels registered.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return 0

    count = 0
    for path in sorted(directory.glob("*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[KERNEL REGISTRY] Skipping {path.name}: {e}")
            continue

        name = data.get("name") or data.get("kernel_id")
        if not name:
            print(f"[KERNEL REGISTRY] Skipping {path.name}: missing 'name'/'kernel_id'")
            continue

        register_kernel(KernelDefinition(
            name=name,
            description=data.get("description", ""),
            core_keys={},
            required_interfaces={},
            initializer=_make_data_initializer(name),
            compatible_categories=data.get("compatible_categories"),
            kernel_id=data.get("kernel_id", name),
            version=data.get("version", "1.0"),
            extra_provides=list(data.get("provides", [])),
        ))
        count += 1

    return count


# Load any data-file kernels shipped alongside the engine.
load_kernel_files(Path(__file__).parent / "kernels")


