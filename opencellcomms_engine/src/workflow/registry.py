"""
Function registry for OpenCellComms workflow system.

Catalogs all available simulation functions with metadata for the UI and executor.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Optional
from enum import Enum


class FunctionCategory(Enum):
    """Categories of workflow functions."""
    INITIALIZATION = "initialization"
    INTRACELLULAR = "intracellular"
    DIFFUSION = "diffusion"
    INTERCELLULAR = "intercellular"
    FINALIZATION = "finalization"
    UTILITY = "utility"


class ParameterType(Enum):
    """Types of function parameters."""
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    DICT = "dict"
    LIST = "list"


@dataclass
class ParameterDefinition:
    """Definition of a function parameter."""
    name: str
    type: ParameterType
    description: str
    default: Any = None
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Optional[List[Any]] = None  # For enum-like parameters


@dataclass
class FunctionMetadata:
    """Metadata for a registered function."""
    name: str
    display_name: str
    description: str
    category: FunctionCategory
    parameters: List[ParameterDefinition] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)  # What data this function needs
    outputs: List[str] = field(default_factory=list)  # What data this function produces
    cloneable: bool = False  # Can this function be cloned/customized?
    module_path: str = ""  # Where to find this function
    source_file: str = ""  # Path to source file (for GUI code viewer)
    compatible_kernels: Optional[List[str]] = None  # Which kernels this function works with (None = all kernels, ["*"] = all kernels, ["biophysics"] = only biophysics)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "default": p.default,
                    "required": p.required,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "options": p.options
                }
                for p in self.parameters
            ],
            "inputs": self.inputs,
            "outputs": self.outputs,
            "cloneable": self.cloneable,
            "module_path": self.module_path,
            "source_file": self.source_file
        }


class FunctionRegistry:
    """Registry of all available workflow functions."""

    def __init__(self):
        self.functions: Dict[str, FunctionMetadata] = {}

    def register(self, metadata: FunctionMetadata):
        """Register a function with its metadata."""
        self.functions[metadata.name] = metadata

    def get(self, function_name: str) -> Optional[FunctionMetadata]:
        """Get metadata for a function by name."""
        return self.functions.get(function_name)

    def get_by_category(self, category: FunctionCategory) -> List[FunctionMetadata]:
        """Get all functions in a category."""
        return [f for f in self.functions.values() if f.category == category]

    def list_all(self) -> List[FunctionMetadata]:
        """Get all registered functions."""
        return list(self.functions.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary for JSON export."""
        return {
            "functions": {
                name: metadata.to_dict()
                for name, metadata in self.functions.items()
            }
        }


def get_default_registry() -> FunctionRegistry:
    """
    Get the default function registry with all decorator-based functions.

    This registry is populated automatically by importing modules that use
    the @register_function decorator.
    """
    # Import all modules with decorated functions to trigger registration
    import src.workflow.standard_functions

    # Import kernel loading functions
    import src.workflow.functions.initialization.load_kernel
    import src.workflow.functions.initialization.store_simulation_dimensions

    # Biology functions (gene networks, metabolism, cell division/death,
    # population/gene-network/MaBoSS setup) now live in the `common` adapter and
    # are registered via opencellcomms_adapters.common.register below.

    # Import adapter functions (experiment-specific). Adapters live in
    # `opencellcomms_adapters/` at the repository root (sibling of the engine),
    # so ensure that root is importable regardless of cwd / entry point
    # (CLI subprocess, GUI in-process, tests). registry.py is at
    # <repo>/opencellcomms_engine/src/workflow/registry.py → parents[3] == <repo>.
    import sys
    from pathlib import Path
    repo_root = str(Path(__file__).resolve().parents[3])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Shared biology / ABM primitives (gene networks, metabolism, cell
    # lifecycle, population/gene-network setup). Imported first because the
    # experiment adapters below may depend on it.
    try:
        import opencellcomms_adapters.common.register  # noqa: F401
    except ImportError as e:
        print(f"[Registry] Common adapter not available: {e}")

    try:
        import opencellcomms_adapters.jayatilake.register  # noqa: F401
    except ImportError as e:
        print(f"[Registry] Jayatilake adapter not available: {e}")

    try:
        import opencellcomms_adapters.MicroC.register  # noqa: F401
    except ImportError as e:
        print(f"[Registry] MicroC adapter not available: {e}")

    try:
        import opencellcomms_adapters.Test_GUI.register  # noqa: F401
    except ImportError as e:
        print(f"[Registry] Test_GUI adapter not available: {e}")

    # PhysiBoSS / PhysiCell adapter — codegen-only node functions
    # (define_substrate / define_cell_type / define_hill_rule /
    # run_physicell_simulation / select_project_template / summarize_*).
    try:
        import opencellcomms_adapters.PhysiBoSS.register  # noqa: F401
    except ImportError as e:
        print(f"[Registry] PhysiBoSS adapter not available: {e}")

    # Get the decorator registry (all functions registered via @register_function)
    from src.workflow.decorators import get_decorator_registry
    return get_decorator_registry()
