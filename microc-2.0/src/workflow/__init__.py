"""
Workflow system for MicroC - allows visual customization of simulation workflows.

This module provides:
- Function registry: Catalog of available simulation functions
- Workflow schema: Data structures for workflow definitions
- Workflow executor: Runtime execution of workflow configurations
- Workflow loader: JSON file loading and validation
"""

from .schema import WorkflowDefinition, WorkflowStage, WorkflowFunction
from .registry import FunctionRegistry, get_default_registry
from .executor import WorkflowExecutor
from .loader import WorkflowLoader

__all__ = [
    'WorkflowDefinition',
    'WorkflowStage',
    'WorkflowFunction',
    'FunctionRegistry',
    'get_default_registry',
    'WorkflowExecutor',
    'WorkflowLoader',
]

