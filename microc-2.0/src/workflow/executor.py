"""
Workflow executor for MicroC.

Executes workflow definitions during simulation, mapping workflow functions
to actual Python implementations and managing execution order.
"""

import importlib
import importlib.util
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
from .schema import (
    WorkflowDefinition,
    WorkflowStage,
    WorkflowFunction,
    SubWorkflow,
    SubWorkflowCall,
    ControllerNode
)
from .registry import FunctionRegistry, get_default_registry

# Observability imports (optional - graceful degradation if not available)
try:
    from .observability import NodeEventEmitter, TrackedContext, ContextSnapshotManager
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False


class WorkflowExecutor:
    """
    Executes workflow definitions during simulation.
    
    Maps workflow functions to actual Python implementations and handles
    parameter injection, execution order, and context passing.
    """
    
    def __init__(self, workflow: WorkflowDefinition, custom_functions_module=None, config=None,
                 observability_enabled: bool = True, results_dir: Optional[Path] = None):
        """
        Initialize the workflow executor.

        Args:
            workflow: WorkflowDefinition to execute
            custom_functions_module: Module containing custom function implementations
            config: Simulation configuration object
            observability_enabled: Whether to enable node observability (default True)
            results_dir: Results directory for observability artifacts (default: Path('results'))
        """
        self.workflow = workflow
        self.custom_functions_module = custom_functions_module
        self.config = config
        self.registry = get_default_registry()
        self.function_cache: Dict[str, Callable] = {}

        # Call stack tracking for sub-workflows
        self.call_stack: List[Dict[str, Any]] = []
        self.max_call_depth = 100  # Prevent stack overflow

        # Observability setup
        self._results_dir = results_dir or Path('results')
        self._observability_enabled = observability_enabled and OBSERVABILITY_AVAILABLE
        self._event_emitter: Optional['NodeEventEmitter'] = None
        self._snapshot_manager: Optional['ContextSnapshotManager'] = None
        self._current_execution_id: Optional[str] = None

        if self._observability_enabled:
            self._event_emitter = NodeEventEmitter(self._results_dir, enabled=True)
            self._snapshot_manager = ContextSnapshotManager(self._results_dir, enabled=True)

        # Validate workflow
        validation_result = workflow.validate()
        if not validation_result['valid']:
            error_msg = "Invalid workflow:\n"
            error_msg += "\n".join(f"  ERROR: {e}" for e in validation_result['errors'])
            if validation_result['warnings']:
                error_msg += "\n\nWarnings:\n"
                error_msg += "\n".join(f"  WARNING: {w}" for w in validation_result['warnings'])
            raise ValueError(error_msg)

    def initialize_observability(self) -> None:
        """Initialize observability systems. Call once before execution starts."""
        if self._event_emitter:
            self._event_emitter.initialize()
        if self._snapshot_manager:
            self._snapshot_manager.initialize()

    def finalize_observability(self, status: str = "completed") -> None:
        """Finalize observability systems. Call once after execution completes."""
        if self._event_emitter:
            self._event_emitter.finalize(status)
    
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

        # Try to get from the registry (decorator-based functions)
        if function_name in self.registry.functions:
            metadata = self.registry.functions[function_name]
            # Import the function from its module
            try:
                module = importlib.import_module(metadata.module_path)
                if hasattr(module, function_name):
                    func = getattr(module, function_name)
                    self.function_cache[cache_key] = func
                    return func
            except ImportError as e:
                print(f"[WORKFLOW] Failed to import {metadata.module_path}: {e}")

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

    def execute_subworkflow(self, subworkflow_name: str, context: Dict[str, Any],
                           iterations: int = 1, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a sub-workflow.

        Args:
            subworkflow_name: Name of the sub-workflow to execute
            context: Execution context
            iterations: Number of times to execute the sub-workflow
            parameters: Additional parameters to pass to the sub-workflow

        Returns:
            Updated context
        """
        # Check if we're using the new sub-workflow system
        if self.workflow.version != "2.0":
            print(f"[WORKFLOW] Warning: Sub-workflow execution only supported in version 2.0")
            return context

        # Get the sub-workflow
        subworkflow = self.workflow.get_subworkflow(subworkflow_name)
        if not subworkflow or not subworkflow.enabled:
            print(f"[WORKFLOW] Warning: Sub-workflow '{subworkflow_name}' not found or disabled")
            return context

        # Check call depth to prevent infinite recursion
        if len(self.call_stack) >= self.max_call_depth:
            raise RecursionError(
                f"Maximum call depth ({self.max_call_depth}) exceeded. "
                f"Possible infinite recursion in sub-workflow calls. "
                f"Call stack: {' -> '.join(c['name'] for c in self.call_stack)}"
            )

        # Add to call stack
        call_info = {
            'name': subworkflow_name,
            'iteration': 0,
            'total_iterations': iterations
        }
        self.call_stack.append(call_info)

        try:
            # Execute the sub-workflow 'iterations' times
            for iteration in range(iterations):
                call_info['iteration'] = iteration + 1

                if iterations > 1:
                    print(f"[WORKFLOW] Executing sub-workflow '{subworkflow_name}' (iteration {iteration + 1}/{iterations})")
                else:
                    print(f"[WORKFLOW] Executing sub-workflow '{subworkflow_name}'")

                # Merge input parameters into context
                if parameters:
                    context = {**context, **parameters}

                # Set context keys for results directory (v2.0 spec Section 10.3)
                subworkflow_kind = self._get_subworkflow_kind(subworkflow_name)
                context['subworkflow_name'] = subworkflow_name
                context['subworkflow_kind'] = subworkflow_kind
                context['results_dir'] = Path('results')

                # Set subworkflow_results_dir based on kind
                kind_plural = 'composers' if subworkflow_kind == 'composer' else 'subworkflows'
                context['subworkflow_results_dir'] = Path('results') / kind_plural / subworkflow_name

                # Get nodes in execution order
                nodes_to_execute = []
                for node_id in subworkflow.execution_order:
                    # Find the node
                    func = subworkflow.get_function_by_id(node_id)
                    if func:
                        nodes_to_execute.append(('function', func))
                        continue

                    call = subworkflow.get_subworkflow_call_by_id(node_id)
                    if call:
                        nodes_to_execute.append(('subworkflow_call', call))
                        continue

                # Fallback: if execution_order is empty but functions/calls exist, execute them in definition order
                # This handles workflows where execution_order wasn't properly computed (e.g., controller ID mismatch)
                if not nodes_to_execute:
                    if subworkflow.functions or subworkflow.subworkflow_calls:
                        print(f"[WORKFLOW] Warning: Sub-workflow '{subworkflow_name}' has empty execution_order but contains nodes. Using definition order.")
                        for func in subworkflow.functions:
                            nodes_to_execute.append(('function', func))
                        for call in subworkflow.subworkflow_calls:
                            nodes_to_execute.append(('subworkflow_call', call))

                # Execute each node in order
                for node_type, node in nodes_to_execute:
                    if node_type == 'function':
                        if node.enabled:
                            try:
                                result = self._execute_function_in_subworkflow(node, context, subworkflow)
                                if result is not None:
                                    context.update(result)
                            except Exception as e:
                                print(f"[WORKFLOW] Error executing function '{node.function_name}' in sub-workflow '{subworkflow_name}': {e}")
                                import traceback
                                traceback.print_exc()

                    elif node_type == 'subworkflow_call':
                        if node.enabled:
                            try:
                                # Merge parameters for the sub-workflow call
                                merged_params = subworkflow.merge_parameters_for_subworkflow_call(node)

                                # Get iterations (from parameters or default)
                                call_iterations = merged_params.get('iterations', node.iterations)
                                try:
                                    call_iterations = int(call_iterations)
                                except (TypeError, ValueError):
                                    call_iterations = 1

                                # Recursively execute the called sub-workflow
                                context = self.execute_subworkflow(
                                    node.subworkflow_name,
                                    context,
                                    iterations=call_iterations,
                                    parameters=merged_params
                                )
                            except Exception as e:
                                print(f"[WORKFLOW] Error executing sub-workflow call to '{node.subworkflow_name}': {e}")
                                import traceback
                                traceback.print_exc()

        finally:
            # Remove from call stack
            self.call_stack.pop()

        return context

    def _execute_function_in_subworkflow(self, workflow_func: WorkflowFunction,
                                         context: Dict[str, Any],
                                         subworkflow: SubWorkflow) -> Optional[Dict[str, Any]]:
        """
        Execute a function within a sub-workflow.

        Similar to _execute_function but uses SubWorkflow for parameter merging.
        Includes observability instrumentation (events + snapshots).
        """
        node_id = workflow_func.id
        function_name = workflow_func.function_name
        subworkflow_name = subworkflow.name
        subworkflow_kind = self._get_subworkflow_kind(subworkflow_name)
        scope_key = f"{subworkflow_kind}:{subworkflow_name}"
        call_path = [c['name'] for c in self.call_stack]

        # Get function_file from top-level attribute or parameters
        function_file = workflow_func.function_file or workflow_func.parameters.get('function_file')

        # Get function implementation
        func = self._get_function_implementation(function_name, function_file)
        if func is None:
            return None

        # Get function metadata from registry
        metadata = self.registry.get(function_name)

        # Prepare function arguments
        kwargs = {}

        # Merge parameters from parameter nodes and function's own parameters
        merged_params = subworkflow.merge_parameters_for_function(workflow_func)

        # Add custom parameters from merged parameters (excluding metadata fields)
        metadata_fields = {'function_file', 'custom_name'}
        for key, value in merged_params.items():
            if key not in metadata_fields:
                kwargs[key] = value

        # === OBSERVABILITY: Take before snapshot ===
        before_version = None
        if self._snapshot_manager:
            before_version = self._snapshot_manager.take_snapshot(
                scope_key, context, node_id=node_id
            )

        # === OBSERVABILITY: Wrap context for tracking ===
        tracked_context = None
        if self._observability_enabled and OBSERVABILITY_AVAILABLE:
            tracked_context = TrackedContext(context)
            tracked_context.start_tracking()
        else:
            tracked_context = context

        # Add context data based on function inputs
        if metadata:
            for input_name in metadata.inputs:
                if input_name == 'context':
                    kwargs['context'] = tracked_context
                elif input_name in tracked_context:
                    kwargs[input_name] = tracked_context[input_name]

        # For custom functions, ensure context is first
        if function_file and 'context' not in kwargs:
            kwargs = {'context': tracked_context, **kwargs}

        # Always add config if available
        if self.config is not None and not function_file and 'config' not in kwargs:
            kwargs['config'] = self.config

        # === OBSERVABILITY: Emit node_start ===
        execution_id = None
        start_time = time.perf_counter()
        if self._event_emitter:
            execution_id = self._event_emitter.emit_node_start(
                node_id=node_id,
                function_name=function_name,
                subworkflow_kind=subworkflow_kind,
                subworkflow_name=subworkflow_name,
                before_context_version=before_version,
                call_path=call_path,
                step_index=context.get('current_step'),
            )

        # Execute function
        status = "ok"
        error_message = None
        result = None
        try:
            result = func(**kwargs)
        except TypeError as e:
            status = "error"
            error_message = str(e)
            print(f"[WORKFLOW] Function '{function_name}' called with wrong arguments: {e}")
            import traceback
            traceback.print_exc()
        except Exception as e:
            status = "error"
            error_message = str(e)
            print(f"[WORKFLOW] Function '{function_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()

        # === OBSERVABILITY: Stop tracking and get reads/writes ===
        read_keys = []
        written_keys = []
        if isinstance(tracked_context, TrackedContext):
            read_keys, written_keys = tracked_context.stop_tracking()
            # Sync tracked context back to original context
            context.clear()
            context.update(tracked_context.to_dict())

        # === OBSERVABILITY: Take after snapshot ===
        after_version = None
        if self._snapshot_manager and written_keys:
            after_version = self._snapshot_manager.take_snapshot(
                scope_key, context, node_id=node_id, execution_id=execution_id
            )

        # === OBSERVABILITY: Emit node_end ===
        duration_ms = (time.perf_counter() - start_time) * 1000
        if self._event_emitter:
            self._event_emitter.emit_node_end(
                node_id=node_id,
                function_name=function_name,
                subworkflow_kind=subworkflow_kind,
                subworkflow_name=subworkflow_name,
                execution_id=execution_id or "",
                status=status,
                duration_ms=duration_ms,
                after_context_version=after_version,
                written_keys=written_keys,
                read_keys=read_keys,
                call_path=call_path,
                error_message=error_message,
            )

        if status == "error":
            return None

        return {"result": result} if result is not None else None

    def _get_subworkflow_kind(self, subworkflow_name: str) -> str:
        """
        Get the kind of a subworkflow (composer or subworkflow).

        Args:
            subworkflow_name: Name of the subworkflow

        Returns:
            'composer' or 'subworkflow'
        """
        # Check metadata for explicit kind
        if hasattr(self.workflow, 'metadata') and self.workflow.metadata:
            gui_metadata = self.workflow.metadata.get('gui', {})
            subworkflow_kinds = gui_metadata.get('subworkflow_kinds', {})
            if subworkflow_name in subworkflow_kinds:
                return subworkflow_kinds[subworkflow_name]

        # Default: 'main' is a composer, others are subworkflows
        return 'composer' if subworkflow_name == 'main' else 'subworkflow'

    def get_call_stack(self) -> List[Dict[str, Any]]:
        """
        Get the current call stack for debugging.

        Returns:
            List of call stack entries with name, iteration, and total_iterations
        """
        return self.call_stack.copy()

    def execute_main(self, context: Dict[str, Any], entry_subworkflow: str = "main") -> Dict[str, Any]:
        """
        Execute the main workflow (for version 2.0 sub-workflow system).

        Args:
            context: Initial execution context
            entry_subworkflow: Name of the subworkflow to start from (default: "main").
                              Section 9.2: Allows running from any composer as entry point.

        Returns:
            Updated context after executing workflow
        """
        # Initialize observability at the start
        self.initialize_observability()

        status = "completed"
        try:
            if self.workflow.version == "2.0":
                # Section 9.2: Support arbitrary entry point for composers
                print(f"[WORKFLOW] Starting execution from entry subworkflow: {entry_subworkflow}")
                result = self.execute_subworkflow(entry_subworkflow, context)
            else:
                # For version 1.0, execute initialization as the entry point
                result = self.execute_initialization(context)
            return result
        except Exception as e:
            status = "failed"
            raise
        finally:
            # Finalize observability at the end
            self.finalize_observability(status)

    def execute_initialization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute initialization stage (legacy v1.0)."""
        if self.workflow.version == "2.0":
            # In v2.0, check if there's an 'initialization' sub-workflow
            if 'initialization' in self.workflow.subworkflows:
                return self.execute_subworkflow("initialization", context)
            return context
        return self.execute_stage("initialization", context)

    def execute_macrostep(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute macrostep stage ONCE per engine step.

        The macrostep stage allows users to configure a custom execution order
        of intracellular, microenvironment, intercellular, and custom functions.
        Each function node in the macrostep canvas can have its own step_count.

        NOTE: Unlike other stages, macrostep.steps controls the ENGINE loop count,
        not the internal repetition. The macrostep executes once per engine step.
        """
        if self.workflow.version == "2.0":
            # In v2.0, check if there's a 'macrostep' sub-workflow
            if 'macrostep' in self.workflow.subworkflows:
                return self.execute_subworkflow("macrostep", context)
            return context

        stage = self.workflow.get_stage("macrostep")
        if not stage or not stage.enabled:
            return context

        # Get enabled functions in execution order
        functions = stage.get_enabled_functions_in_order()
        if not functions:
            return context

        # Execute each function in order (NO internal repetition - macrostep.steps controls engine loop)
        for workflow_func in functions:
            # Determine this function's step count
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

            # Execute function 'func_step_count' times
            for _ in range(func_step_count):
                try:
                    result = self._execute_function(workflow_func, context, stage)
                    # Update context with results (don't replace it)
                    if result is not None:
                        context.update(result)
                except Exception as e:
                    print(f"[WORKFLOW] Error executing function '{workflow_func.function_name}': {e}")
                    import traceback
                    traceback.print_exc()

        return context

    def execute_intracellular(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intracellular stage."""
        if self.workflow.version == "2.0":
            if 'intracellular' in self.workflow.subworkflows:
                return self.execute_subworkflow("intracellular", context)
            return context
        return self.execute_stage("intracellular", context)

    def execute_diffusion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute diffusion stage (legacy name)."""
        if self.workflow.version == "2.0":
            # Try microenvironment or diffusion sub-workflow
            if 'microenvironment' in self.workflow.subworkflows:
                return self.execute_subworkflow("microenvironment", context)
            if 'diffusion' in self.workflow.subworkflows:
                return self.execute_subworkflow("diffusion", context)
            return context

        # Try microenvironment first, fall back to diffusion for backward compatibility
        if "microenvironment" in self.workflow.stages:
            return self.execute_stage("microenvironment", context)
        return self.execute_stage("diffusion", context)

    def execute_microenvironment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute microenvironment stage (preferred name for diffusion)."""
        if self.workflow.version == "2.0":
            if 'microenvironment' in self.workflow.subworkflows:
                return self.execute_subworkflow("microenvironment", context)
            if 'diffusion' in self.workflow.subworkflows:
                return self.execute_subworkflow("diffusion", context)
            return context

        # Try microenvironment first, fall back to diffusion for backward compatibility
        if "microenvironment" in self.workflow.stages:
            return self.execute_stage("microenvironment", context)
        return self.execute_stage("diffusion", context)

    def execute_intercellular(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intercellular stage."""
        if self.workflow.version == "2.0":
            if 'intercellular' in self.workflow.subworkflows:
                return self.execute_subworkflow("intercellular", context)
            return context
        return self.execute_stage("intercellular", context)

    def execute_finalization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute finalization stage."""
        if self.workflow.version == "2.0":
            if 'finalization' in self.workflow.subworkflows:
                return self.execute_subworkflow("finalization", context)
            return context
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

