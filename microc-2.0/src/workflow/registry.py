"""
Function registry for MicroC workflow system.

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
    import tests.jayatilake_experiment.jayatilake_experiment_cell_functions
    import src.workflow.functions.macrostep  # Macrostep stage runner functions

    # Get the decorator registry (all functions registered via @register_function)
    from src.workflow.decorators import get_decorator_registry
    return get_decorator_registry()
