"""
Workflow executor for MicroC.

Executes workflow definitions during simulation, mapping workflow functions
to actual Python implementations and managing execution order.
"""

import importlib
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from .schema import WorkflowDefinition, WorkflowStage, WorkflowFunction
from .registry import FunctionRegistry, get_default_registry


class WorkflowExecutor:
    """
    Executes workflow definitions during simulation.
    
    Maps workflow functions to actual Python implementations and handles
    parameter injection, execution order, and context passing.
    """
    
    def __init__(self, workflow: WorkflowDefinition, custom_functions_module=None, config=None):
        """
        Initialize the workflow executor.
        
        Args:
            workflow: WorkflowDefinition to execute
            custom_functions_module: Module containing custom function implementations
            config: Simulation configuration object
        """
        self.workflow = workflow
        self.custom_functions_module = custom_functions_module
        self.config = config
        self.registry = get_default_registry()
        self.function_cache: Dict[str, Callable] = {}
        
        # Validate workflow
        errors = workflow.validate()
        if errors:
            raise ValueError(f"Invalid workflow: {errors}")
    
    def _get_function_implementation(self, function_name: str) -> Optional[Callable]:
        """
        Get the actual Python function implementation for a workflow function.

        Args:
            function_name: Name of the function to get

        Returns:
            Callable function or None if not found
        """
        # Check cache first
        if function_name in self.function_cache:
            return self.function_cache[function_name]

        # Try to get from custom functions module first
        if self.custom_functions_module and hasattr(self.custom_functions_module, function_name):
            func = getattr(self.custom_functions_module, function_name)
            self.function_cache[function_name] = func
            return func

        # Try to get from standard functions module
        try:
            from . import standard_functions
            if hasattr(standard_functions, function_name):
                func = getattr(standard_functions, function_name)
                self.function_cache[function_name] = func
                return func
        except ImportError:
            pass

        # Function not found
        print(f"[WORKFLOW] Warning: Function '{function_name}' not found in custom or standard functions")
        return None
    
    def execute_stage(self, stage_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a workflow stage.

        Args:
            stage_name: Name of the stage to execute (e.g., "intracellular")
            context: Execution context containing data needed by functions

        Returns:
            Updated context with results from executed functions
        """
        stage = self.workflow.get_stage(stage_name)
        if not stage or not stage.enabled:
            return context

        # Get enabled functions in execution order
        functions = stage.get_enabled_functions_in_order()

        if not functions:
            return context

        # Execute each function in order
        for workflow_func in functions:
            try:
                result = self._execute_function(workflow_func, context)
                # Update context with results
                if result is not None:
                    context.update(result)
            except Exception as e:
                print(f"[WORKFLOW] Error executing function '{workflow_func.function_name}': {e}")
                import traceback
                traceback.print_exc()

        return context
    
    def _execute_function(self, workflow_func: WorkflowFunction, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a single workflow function.
        
        Args:
            workflow_func: WorkflowFunction to execute
            context: Execution context
            
        Returns:
            Dictionary with results or None
        """
        # Get function implementation
        func = self._get_function_implementation(workflow_func.function_name)
        if func is None:
            return None
        
        # Get function metadata from registry
        metadata = self.registry.get(workflow_func.function_name)
        
        # Prepare function arguments
        kwargs = {}

        # Add custom parameters from workflow (excluding metadata fields)
        metadata_fields = {'function_file', 'custom_name'}  # Fields that are metadata, not function parameters
        for key, value in workflow_func.parameters.items():
            if key not in metadata_fields:
                kwargs[key] = value

        # Add context data based on function inputs
        if metadata:
            for input_name in metadata.inputs:
                if input_name in context:
                    kwargs[input_name] = context[input_name]

        # Always add config if available
        if self.config is not None:
            kwargs['config'] = self.config
        
        # Execute function
        try:
            result = func(**kwargs)
            return {"result": result} if result is not None else None
        except TypeError as e:
            # Handle missing required arguments
            print(f"[WORKFLOW] Function '{workflow_func.function_name}' called with wrong arguments: {e}")
            return None
    
    def execute_initialization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute initialization stage."""
        return self.execute_stage("initialization", context)
    
    def execute_intracellular(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intracellular stage."""
        return self.execute_stage("intracellular", context)
    
    def execute_diffusion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute diffusion stage."""
        return self.execute_stage("diffusion", context)
    
    def execute_intercellular(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intercellular stage."""
        return self.execute_stage("intercellular", context)
    
    def execute_finalization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute finalization stage."""
        return self.execute_stage("finalization", context)


class WorkflowContext:
    """
    Helper class to manage workflow execution context.
    
    Provides a structured way to pass data between workflow functions.
    """
    
    def __init__(self, **kwargs):
        self.data = kwargs
    
    def get(self, key: str, default=None):
        """Get a value from context."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a value in context."""
        self.data[key] = value
    
    def update(self, updates: Dict[str, Any]):
        """Update context with multiple values."""
        self.data.update(updates)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return self.data.copy()

