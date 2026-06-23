"""
Function registry for OpenCellComms workflow system.

Catalogs all available simulation functions with metadata for the UI and executor.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Optional
from enum import Enum


class FunctionCategory(Enum):
    """
    Legacy registry categories for workflow functions.

    These tags are compatibility metadata for the function registry. In v2
    workflows, execution is determined by the graph/subworkflow structure, not
    by this enum.
    """
    INITIALIZATION = "initialization"
    INTRACELLULAR = "intracellular"
    DIFFUSION = "diffusion"
    INTERCELLULAR = "intercellular"
    WORLD = "world"  # World / tile-grid resource behaviors (growback, decay, ...)
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
    requires: Optional[List[str]] = None  # Capability tokens this function needs from the kernel (None/[] = no requirement). A workflow fails to load if its kernel does not provide all of these.
    operates_on: Optional[List[str]] = None  # Purely descriptive: resource field(s) this function reads/writes (e.g. ["sugar"]). Not validated; a hook for the GUI to link a behavior back to the resource it acts on.
    contract: Optional[Dict[str, Any]] = None  # Optional read/write contract for GUI placement and workflow validation.
    validation_errors: List[str] = field(default_factory=list)  # Authoring problems found at registration (e.g. an undeclared parameter). Empty = clean. Surfaced in the GUI so the node shows a "fix me" state instead of silently losing a socket.

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
            "source_file": self.source_file,
            "compatible_kernels": self.compatible_kernels,
            "requires": self.requires,
            "operates_on": self.operates_on,
            "contract": self.contract,
            "validation_errors": self.validation_errors
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


def discover_adapter_names(adapters_root) -> List[str]:
    """
    Discover installed adapters (plugins) under `adapters_root`.

    Returns the sorted names of every folder that has a `register.py` and a
    Python-importable name. Folders whose names aren't valid module identifiers
    (e.g. 'jayatilake_(legacy)', 'maboss_(legacy)') are skipped — they're kept
    on disk for reference only. `common` is included; callers that need load
    ordering should import it first.
    """
    import keyword
    from pathlib import Path
    root = Path(adapters_root)
    names = []
    if root.is_dir():
        for child in sorted(root.iterdir()):
            name = child.name
            if not child.is_dir():
                continue
            if not name.isidentifier() or keyword.iskeyword(name):
                continue
            if (child / 'register.py').is_file():
                names.append(name)
    return names


def get_default_registry() -> FunctionRegistry:
    """
    Get the default function registry with all decorator-based functions.

    This registry is populated automatically by importing modules that use
    the @register_function decorator.
    """
    # Import all modules with decorated functions to trigger registration
    import src.workflow.standard_functions

    # Import built-in workflow functions so the GUI palette can expose core
    # setup/plot nodes without requiring a workflow/plugin import first.
    import src.workflow.functions.initialization
    import src.workflow.functions.finalization

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

    # Auto-discover adapters (plugins). Any folder under opencellcomms_adapters/
    # that has a `register.py` and a Python-importable name is loaded — no need
    # to hand-maintain a list here, so a newly created plugin works on restart.
    import importlib

    def _load_adapter(pkg_name):
        try:
            importlib.import_module(f'opencellcomms_adapters.{pkg_name}.register')
        except ImportError as e:
            print(f"[Registry] Adapter '{pkg_name}' not available: {e}")

    adapters_root = Path(repo_root) / 'opencellcomms_adapters'
    names = discover_adapter_names(adapters_root)

    # `common` (shared biology / ABM primitives) must load first because the
    # experiment adapters import from it.
    for name in ['common'] + [n for n in names if n != 'common']:
        if name == 'common' and 'common' not in names:
            continue
        _load_adapter(name)

    # Get the decorator registry (all functions registered via @register_function)
    from src.workflow.decorators import get_decorator_registry
    return get_decorator_registry()
