"""
Workflow executor for MicroC.

Executes workflow definitions during simulation, mapping workflow functions
to actual Python implementations and managing execution order.
"""

import importlib
import importlib.util
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
    
    def _load_function_from_file(self, function_file: str, function_name: str) -> Optional[Callable]:
        """
        Dynamically load a function from a Python file.

        Args:
            function_file: Path to Python file containing the function
            function_name: Name of the function to load

        Returns:
            Callable function or None if not found
        """
        try:
            # Convert relative path to absolute
            file_path = Path(function_file)
            if not file_path.is_absolute():
                # Try multiple resolution strategies
                # 1. Relative to current working directory
                if not file_path.exists():
                    # 2. Relative to microc-2.0 directory (go up from src/workflow)
                    microc_root = Path(__file__).parent.parent.parent
                    file_path = microc_root / function_file

            if not file_path.exists():
                print(f"[WORKFLOW] Warning: Function file not found: {function_file}")
                print(f"[WORKFLOW]   Tried: {file_path}")
                return None

            # Create module name from file path
            module_name = f"workflow_custom_{file_path.stem}_{id(function_file)}"

            # Load module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                print(f"[WORKFLOW] Warning: Could not load module from {function_file}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Get function from module
            if hasattr(module, function_name):
                func = getattr(module, function_name)
                return func
            else:
                print(f"[WORKFLOW] Warning: Function '{function_name}' not found in {function_file}")
                return None

        except Exception as e:
            print(f"[WORKFLOW] Error loading function from {function_file}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_function_implementation(self, function_name: str, function_file: Optional[str] = None) -> Optional[Callable]:
        """
        Get the actual Python function implementation for a workflow function.

        Args:
            function_name: Name of the function to get
            function_file: Optional path to Python file containing the function

        Returns:
            Callable function or None if not found
        """
        # Create cache key
        cache_key = f"{function_file}::{function_name}" if function_file else function_name

        # Check cache first
        if cache_key in self.function_cache:
            return self.function_cache[cache_key]

        # If function_file is specified, load from that file
        if function_file:
            func = self._load_function_from_file(function_file, function_name)
            if func is not None:
                self.function_cache[cache_key] = func
                return func

        # Try to get from custom functions module first
        if self.custom_functions_module and hasattr(self.custom_functions_module, function_name):
            func = getattr(self.custom_functions_module, function_name)
            self.function_cache[cache_key] = func
            return func

        # Try to get from standard functions module
        try:
            from . import standard_functions
            if hasattr(standard_functions, function_name):
                func = getattr(standard_functions, function_name)
                self.function_cache[cache_key] = func
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

        # Get number of steps for this stage (default: 1)
        num_steps = max(1, stage.steps)  # Ensure at least 1 step

        # Log if stage will execute multiple times
        if num_steps > 1:
            print(f"[WORKFLOW] Stage '{stage_name}' will execute {num_steps} times")

        # Execute the stage 'num_steps' times
        for step_iteration in range(num_steps):
            # Execute each function in order
            for workflow_func in functions:
                # Determine this function's step count.
                #
                # Primary source: a "step_count" parameter coming from connected
                # blue parameter nodes or the function's own parameters. This
                # allows the GUI to drive repetitions via a parameter socket.
                #
                # Fallback: the WorkflowFunction.step_count field stored in the
                # workflow JSON (editable via the node's Step Count field).
                merged_params = stage.merge_parameters_for_function(workflow_func)

                param_step_count = merged_params.get("step_count")
                func_step_count = None
                if param_step_count is not None:
                    try:
                        func_step_count = int(param_step_count)
                    except (TypeError, ValueError):
                        func_step_count = None

                if func_step_count is None or func_step_count <= 0:
                    func_step_count = getattr(workflow_func, "step_count", 1)

                func_step_count = max(1, int(func_step_count))

                if func_step_count > 1:
                    print(
                        f"[WORKFLOW] Function '{workflow_func.function_name}' will execute {func_step_count} times"
                    )

                # Execute this function 'func_step_count' times
                for func_iteration in range(func_step_count):
                    try:
                        result = self._execute_function(workflow_func, context, stage)
                        # Update context with results
                        if result is not None:
                            context.update(result)
                    except Exception as e:
                        print(f"[WORKFLOW] Error executing function '{workflow_func.function_name}': {e}")
                        import traceback
                        traceback.print_exc()

        return context
    
    def _execute_function(self, workflow_func: WorkflowFunction, context: Dict[str, Any], stage: 'WorkflowStage') -> Optional[Dict[str, Any]]:
        """
        Execute a single workflow function.

        Args:
            workflow_func: WorkflowFunction to execute
            context: Execution context
            stage: WorkflowStage containing this function (for parameter merging)

        Returns:
            Dictionary with results or None
        """
        # Get function_file from top-level attribute (preferred) or parameters (fallback)
        function_file = workflow_func.function_file or workflow_func.parameters.get('function_file')

        # Get function implementation
        func = self._get_function_implementation(workflow_func.function_name, function_file)
        if func is None:
            return None

        # Get function metadata from registry
        metadata = self.registry.get(workflow_func.function_name)

        # Prepare function arguments
        kwargs = {}

        # Merge parameters from parameter nodes and function's own parameters
        merged_params = stage.merge_parameters_for_function(workflow_func)

        # Add custom parameters from merged parameters (excluding metadata fields)
        metadata_fields = {'function_file', 'custom_name'}  # Fields that are metadata, not function parameters
        for key, value in merged_params.items():
            if key not in metadata_fields:
                kwargs[key] = value

        # Add context data based on function inputs
        if metadata:
            for input_name in metadata.inputs:
                # Special handling for 'context' - pass the whole context dict
                if input_name == 'context':
                    kwargs['context'] = context
                elif input_name in context:
                    kwargs[input_name] = context[input_name]

        # For custom functions (with function_file), ensure context is first
        if function_file and 'context' not in kwargs:
            kwargs = {'context': context, **kwargs}

        # Always add config if available (for standard functions that need it)
        if self.config is not None and not function_file and 'config' not in kwargs:
            kwargs['config'] = self.config

        # Execute function
        try:
            result = func(**kwargs)
            return {"result": result} if result is not None else None
        except TypeError as e:
            # Handle missing required arguments
            print(f"[WORKFLOW] Function '{workflow_func.function_name}' called with wrong arguments: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def execute_initialization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute initialization stage."""
        return self.execute_stage("initialization", context)

    def execute_macrostep(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute macrostep stage.

        The macrostep stage allows users to configure a custom execution order
        of intracellular, microenvironment, intercellular, and custom functions.
        Each function node in the macrostep canvas can have its own step_count.
        """
        return self.execute_stage("macrostep", context)

    def execute_intracellular(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intracellular stage."""
        return self.execute_stage("intracellular", context)
    
    def execute_diffusion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute diffusion stage (legacy name)."""
        # Try microenvironment first, fall back to diffusion for backward compatibility
        if "microenvironment" in self.workflow.stages:
            return self.execute_stage("microenvironment", context)
        return self.execute_stage("diffusion", context)

    def execute_microenvironment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute microenvironment stage (preferred name for diffusion)."""
        # Try microenvironment first, fall back to diffusion for backward compatibility
        if "microenvironment" in self.workflow.stages:
            return self.execute_stage("microenvironment", context)
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

