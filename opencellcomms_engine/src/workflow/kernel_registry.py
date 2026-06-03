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
    compatible_categories=["INITIALIZATION", "INTRACELLULAR", "DIFFUSION", "INTERCELLULAR", "FINALIZATION", "UTILITY"],
    kernel_id="biophysics",
    version="1.0",
)

register_kernel(BIOPHYSICS_KERNEL)


# -- PhysiCell black-box facade kernel ---------------------------------------
#
# Routing signal for the codegen→make→spawn pipeline (see
# docs/Physicell_Facade_plan.md). Unlike biophysics, the simulation lives in
# a generated C++ project; the Python "kernel" is just the dispatch token.

def _initialize_physicell(context: Dict[str, Any], params: Dict[str, Any]) -> bool:
    context['kernel_type'] = 'physicell'
    print("[KERNEL] PhysiCell facade kernel selected — simulation will run via codegen + native binary")
    return True


PHYSICELL_KERNEL = KernelDefinition(
    name="physicell",
    description=(
        "PhysiCell / PhysiBoSS black-box facade. Workflow nodes describe a "
        "domain spec (substrates, cell types, Hill rules); the engine "
        "generates a project, builds it against unmodified PhysiBoSS-master, "
        "and runs the native binary while streaming occ_events.jsonl."
    ),
    core_keys={},
    required_interfaces={},
    initializer=_initialize_physicell,
    compatible_categories=["INITIALIZATION"],
    kernel_id="physicell",
    version="1.0",
)

register_kernel(PHYSICELL_KERNEL)


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


