"""
Workflow schema definitions for OpenCellComms.

Defines the data structures for workflow configurations that can be
serialized to/from JSON and executed by the workflow executor.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum
import re


class WorkflowStageType(Enum):
    """Types of workflow stages in the simulation lifecycle (legacy)."""
    INITIALIZATION = "initialization"
    MACROSTEP = "macrostep"  # Configurable macro-step with custom execution order
    INTRACELLULAR = "intracellular"
    DIFFUSION = "diffusion"  # Legacy name
    MICROENVIRONMENT = "microenvironment"  # Preferred name for diffusion stage
    INTERCELLULAR = "intercellular"
    FINALIZATION = "finalization"


class NodeType(Enum):
    """Types of nodes in a sub-workflow."""
    CONTROLLER = "controller"  # Entry point node (one per sub-workflow)
    WORKFLOW_FUNCTION = "workflowFunction"  # Regular function node
    SUBWORKFLOW_CALL = "subworkflow_call"  # Call to another sub-workflow
    PARAMETER_NODE = "parameterNode"  # Parameter storage node
    LIST_PARAMETER_NODE = "listParameterNode"  # List parameter storage node
    DICT_PARAMETER_NODE = "dictParameterNode"  # Dictionary parameter storage node
    GROUP_NODE = "groupNode"  # Visual grouping node


@dataclass
class ParameterNode:
    """
    Represents a parameter storage node in the visual workflow.

    Attributes:
        id: Unique identifier for this parameter node
        label: Display name for this parameter node
        parameters: Dictionary of parameters stored in this node
        position: UI position for visual editor (x, y coordinates)
    """
    id: str
    label: str = "Parameters"
    parameters: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "label": self.label,
            "parameters": self.parameters,
            "position": self.position
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParameterNode":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            id=data["id"],
            label=data.get("label", "Parameters"),
            parameters=data.get("parameters", {}),
            position=data.get("position", {"x": 0, "y": 0})
        )


@dataclass
class ListParameterNode:
    """
    Represents a list parameter storage node in the visual workflow.

    Attributes:
        id: Unique identifier for this list parameter node
        label: Display name for this list parameter node
        list_type: Type of items in the list ('string' or 'float')
        items: List of items stored in this node
        target_param: Name of the function parameter this list maps to
        position: UI position for visual editor (x, y coordinates)
    """
    id: str
    label: str = "List"
    list_type: str = "string"  # 'string' or 'float'
    items: List[Any] = field(default_factory=list)
    target_param: str = "items"  # Default target parameter name
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "type": "listParameterNode",
            "label": self.label,
            "listType": self.list_type,
            "items": self.items,
            "position": self.position
        }
        if self.target_param != "items":
            result["targetParam"] = self.target_param
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ListParameterNode":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            id=data["id"],
            label=data.get("label", "List"),
            list_type=data.get("listType", data.get("list_type", "string")),
            items=data.get("items", []),
            target_param=data.get("targetParam", data.get("target_param", "items")),
            position=data.get("position", {"x": 0, "y": 0})
        )


@dataclass
class DictEntry:
    """
    Represents a single entry in a dictionary parameter node.

    Attributes:
        key: The key for this entry
        value: The value for this entry
        value_type: Type of the value ('string', 'float', 'int', 'bool', 'list', 'dict')
    """
    key: str
    value: Any
    value_type: str = "string"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "valueType": self.value_type
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DictEntry":
        """Create from dictionary (JSON deserialization)."""
        if data is None:
            return cls(key="", value="", value_type="string")
        return cls(
            key=data.get("key", ""),
            value=data.get("value", ""),
            value_type=data.get("valueType", data.get("value_type", "string"))
        )


@dataclass
class DictParameterNode:
    """
    Represents a dictionary parameter storage node in the visual workflow.

    Attributes:
        id: Unique identifier for this dict parameter node
        label: Display name for this dict parameter node
        entries: List of DictEntry objects stored in this node
        position: UI position for visual editor (x, y coordinates)
    """
    id: str
    label: str = "Dictionary"
    entries: List[DictEntry] = field(default_factory=list)
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": "dictParameterNode",
            "label": self.label,
            "entries": [e.to_dict() if isinstance(e, DictEntry) else e for e in self.entries],
            "position": self.position
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DictParameterNode":
        """Create from dictionary (JSON deserialization)."""
        entries_data = data.get("entries", [])
        entries = [
            DictEntry.from_dict(e) if isinstance(e, dict) else e
            for e in entries_data
        ]
        return cls(
            id=data["id"],
            label=data.get("label", "Dictionary"),
            entries=entries,
            position=data.get("position", {"x": 0, "y": 0})
        )


@dataclass
class WorkflowFunction:
    """
    Represents a single function in a workflow.

    Attributes:
        id: Unique identifier for this function instance
        function_name: Name of the function to execute (must be in registry)
        parameters: Custom parameters to pass to the function
        enabled: Whether this function should be executed
        position: UI position for visual editor (x, y coordinates)
        description: Optional description of what this function does
        function_file: Optional path to Python file containing custom function
        custom_name: Optional custom name for this function instance
        parameter_nodes: List of parameter node IDs connected to this function
        step_count: Number of times to execute this function (for macrostep stage nodes)
    """
    id: str
    function_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    description: str = ""
    function_file: Optional[str] = None
    custom_name: str = ""
    parameter_nodes: List[str] = field(default_factory=list)
    step_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "function_name": self.function_name,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "position": self.position,
            "description": self.description,
            "custom_name": self.custom_name,
            "parameter_nodes": self.parameter_nodes,
            "step_count": self.step_count
        }
        # Only include function_file if it's set
        if self.function_file:
            result["function_file"] = self.function_file
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowFunction":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            id=data["id"],
            function_name=data["function_name"],
            parameters=data.get("parameters", {}),
            enabled=data.get("enabled", True),
            position=data.get("position", {"x": 0, "y": 0}),
            description=data.get("description", ""),
            function_file=data.get("function_file"),
            custom_name=data.get("custom_name", ""),
            parameter_nodes=data.get("parameter_nodes", []),
            step_count=data.get("step_count", 1)
        )


@dataclass
class SubWorkflowCall:
    """
    Represents a call to another sub-workflow.

    Attributes:
        id: Unique identifier for this sub-workflow call
        subworkflow_name: Name of the sub-workflow to call
        iterations: Number of times to execute the sub-workflow (default: 1)
        parameters: Parameters to pass to the sub-workflow
        enabled: Whether this call should be executed
        position: UI position for visual editor (x, y coordinates)
        description: Optional description of this call
        parameter_nodes: List of parameter node IDs connected to this call
        context_mapping: Optional mapping of context variables to pass
    """
    id: str
    subworkflow_name: str
    iterations: int = 1
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    description: str = ""
    parameter_nodes: List[str] = field(default_factory=list)
    context_mapping: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": "subworkflow_call",
            "subworkflow_name": self.subworkflow_name,
            "iterations": self.iterations,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "position": self.position,
            "description": self.description,
            "parameter_nodes": self.parameter_nodes,
            "context_mapping": self.context_mapping
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubWorkflowCall":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            id=data["id"],
            subworkflow_name=data["subworkflow_name"],
            iterations=data.get("iterations", 1),
            parameters=data.get("parameters", {}),
            enabled=data.get("enabled", True),
            position=data.get("position", {"x": 0, "y": 0}),
            description=data.get("description", ""),
            parameter_nodes=data.get("parameter_nodes", []),
            context_mapping=data.get("context_mapping", {})
        )


@dataclass
class ControllerNode:
    """
    Represents the controller/entry point node for a sub-workflow.

    Attributes:
        id: Unique identifier for this controller
        label: Display label (default: "CONTROLLER")
        position: UI position for visual editor
        number_of_steps: Number of steps (for compatibility, usually 1)
    """
    id: str
    label: str = "CONTROLLER"
    position: Dict[str, float] = field(default_factory=lambda: {"x": 100, "y": 100})
    number_of_steps: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": "controller",
            "label": self.label,
            "position": self.position,
            "number_of_steps": self.number_of_steps
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ControllerNode":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            id=data["id"],
            label=data.get("label", "CONTROLLER"),
            position=data.get("position", {"x": 100, "y": 100}),
            number_of_steps=data.get("number_of_steps", 1)
        )


@dataclass
class WorkflowStage:
    """
    Represents a stage in the workflow (e.g., intracellular, diffusion).

    Attributes:
        functions: List of functions to execute in this stage
        parameters: List of parameter nodes in this stage
        execution_order: Ordered list of function IDs defining execution sequence
        enabled: Whether this stage should be executed
        steps: Number of times to execute this stage per macro-step (default: 1)
               For example, if intracellular.steps=3, microenvironment.steps=5, intercellular.steps=1,
               then at each macro-step:
               - intracellular functions run 3 times
               - microenvironment functions run 5 times
               - intercellular functions run 1 time
    """
    functions: List[WorkflowFunction] = field(default_factory=list)
    parameters: List[ParameterNode] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    enabled: bool = True
    steps: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "functions": [f.to_dict() for f in self.functions],
            "parameters": [p.to_dict() for p in self.parameters],
            "execution_order": self.execution_order,
            "enabled": self.enabled,
            "steps": self.steps
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowStage":
        """Create from dictionary (JSON deserialization)."""
        functions = [WorkflowFunction.from_dict(f) for f in data.get("functions", [])]
        parameters = [ParameterNode.from_dict(p) for p in data.get("parameters", [])]
        return cls(
            functions=functions,
            parameters=parameters,
            execution_order=data.get("execution_order", []),
            enabled=data.get("enabled", True),
            steps=data.get("steps", 1)
        )

    def get_function_by_id(self, function_id: str) -> Optional[WorkflowFunction]:
        """Get a function by its ID."""
        for func in self.functions:
            if func.id == function_id:
                return func
        return None

    def get_parameter_node_by_id(self, param_id: str) -> Optional[ParameterNode]:
        """Get a parameter node by its ID."""
        for param in self.parameters:
            if param.id == param_id:
                return param
        return None

    def get_enabled_functions_in_order(self) -> List[WorkflowFunction]:
        """Get enabled functions in execution order."""
        result = []
        for func_id in self.execution_order:
            func = self.get_function_by_id(func_id)
            if func and func.enabled:
                result.append(func)
        return result

    def merge_parameters_for_function(self, func: WorkflowFunction) -> Dict[str, Any]:
        """
        Merge parameters from connected parameter nodes with function's own parameters.
        Function's own parameters take precedence over parameter node values.

        Special handling for substance definitions:
        - If multiple parameter nodes have a 'name' key (indicating substance definitions),
          they are collected into a 'substances' list instead of overwriting each other.

        Args:
            func: The function to merge parameters for

        Returns:
            Merged parameter dictionary
        """
        merged = {}
        substances = []  # Collect substance definitions

        # First, add parameters from connected parameter nodes
        for param_node_id in func.parameter_nodes:
            param_node = self.get_parameter_node_by_id(param_node_id)
            if param_node:
                # Check if this parameter node defines a substance
                # (has 'name' and 'diffusion_coeff' keys)
                if 'name' in param_node.parameters and 'diffusion_coeff' in param_node.parameters:
                    # This is a substance definition - add to list
                    substances.append(param_node.parameters)
                else:
                    # Regular parameters - merge normally
                    merged.update(param_node.parameters)

        # Add collected substances to merged parameters
        if substances:
            merged['substances'] = substances

        # Then, overlay function's own parameters (these take precedence)
        merged.update(func.parameters)

        return merged


@dataclass
class InputParameter:
    """
    Represents an input parameter definition for a sub-workflow.

    Attributes:
        name: Parameter name
        type: Parameter type (e.g., "FLOAT", "INTEGER", "STRING")
        required: Whether this parameter is required
        default: Default value if not provided
        description: Description of the parameter
    """
    name: str
    type: str = "STRING"
    required: bool = False
    default: Any = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "description": self.description
        }
        if self.default is not None:
            result["default"] = self.default
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputParameter":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            name=data["name"],
            type=data.get("type", "STRING"),
            required=data.get("required", False),
            default=data.get("default"),
            description=data.get("description", "")
        )


@dataclass
class SubWorkflow:
    """
    Represents a sub-workflow in the new workflow system.

    A sub-workflow is a reusable workflow component that can be called
    from other sub-workflows. Each sub-workflow has:
    - A controller node (entry point)
    - Functions and sub-workflow calls
    - Parameter nodes (regular, list, and dict types)
    - Input parameter definitions
    - Execution order

    Attributes:
        name: Unique name for this sub-workflow
        description: Description of what this sub-workflow does
        controller: Controller node (entry point)
        functions: List of function nodes
        subworkflow_calls: List of calls to other sub-workflows
        parameters: List of regular parameter nodes
        list_parameters: List of list parameter nodes
        dict_parameters: List of dict parameter nodes
        execution_order: Ordered list of node IDs defining execution sequence
        input_parameters: List of input parameter definitions
        enabled: Whether this sub-workflow is enabled
        deletable: Whether this sub-workflow can be deleted (main is not deletable)
    """
    name: str
    description: str = ""
    controller: Optional[ControllerNode] = None
    functions: List[WorkflowFunction] = field(default_factory=list)
    subworkflow_calls: List[SubWorkflowCall] = field(default_factory=list)
    parameters: List[ParameterNode] = field(default_factory=list)
    list_parameters: List[ListParameterNode] = field(default_factory=list)
    dict_parameters: List[DictParameterNode] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    input_parameters: List[InputParameter] = field(default_factory=list)
    enabled: bool = True
    deletable: bool = True

    def __post_init__(self):
        """Initialize controller if not provided."""
        if self.controller is None:
            self.controller = ControllerNode(
                id=f"controller-{self.name}",
                label=f"{self.name.upper()} CONTROLLER"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "description": self.description,
            "enabled": self.enabled,
            "deletable": self.deletable,
            "execution_order": self.execution_order
        }

        if self.controller:
            result["controller"] = self.controller.to_dict()

        if self.functions:
            result["functions"] = [f.to_dict() for f in self.functions]

        if self.subworkflow_calls:
            result["subworkflow_calls"] = [s.to_dict() for s in self.subworkflow_calls]

        # Combine all parameter node types into a single list
        all_parameters = []
        all_parameters.extend([p.to_dict() for p in self.parameters])
        all_parameters.extend([p.to_dict() for p in self.list_parameters])
        all_parameters.extend([p.to_dict() for p in self.dict_parameters])
        if all_parameters:
            result["parameters"] = all_parameters

        if self.input_parameters:
            result["input_parameters"] = [ip.to_dict() for ip in self.input_parameters]

        return result

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "SubWorkflow":
        """Create from dictionary (JSON deserialization)."""
        controller = None
        if "controller" in data and data["controller"] is not None:
            controller = ControllerNode.from_dict(data["controller"])

        functions = [WorkflowFunction.from_dict(f) for f in data.get("functions", [])]
        subworkflow_calls = [SubWorkflowCall.from_dict(s) for s in data.get("subworkflow_calls", [])]
        input_parameters = [InputParameter.from_dict(ip) for ip in data.get("input_parameters", [])]

        # Parse parameter nodes based on type
        parameters = []
        list_parameters = []
        dict_parameters = []
        for p in data.get("parameters", []):
            if p is None:
                continue
            node_type = p.get("type", "parameterNode")
            if node_type == "listParameterNode":
                list_parameters.append(ListParameterNode.from_dict(p))
            elif node_type == "dictParameterNode":
                dict_parameters.append(DictParameterNode.from_dict(p))
            else:
                parameters.append(ParameterNode.from_dict(p))

        return cls(
            name=name,
            description=data.get("description", ""),
            controller=controller,
            functions=functions,
            subworkflow_calls=subworkflow_calls,
            parameters=parameters,
            list_parameters=list_parameters,
            dict_parameters=dict_parameters,
            execution_order=data.get("execution_order", []),
            input_parameters=input_parameters,
            enabled=data.get("enabled", True),
            deletable=data.get("deletable", True)
        )

    def get_function_by_id(self, function_id: str) -> Optional[WorkflowFunction]:
        """Get a function by its ID."""
        for func in self.functions:
            if func.id == function_id:
                return func
        return None

    def get_subworkflow_call_by_id(self, call_id: str) -> Optional[SubWorkflowCall]:
        """Get a sub-workflow call by its ID."""
        for call in self.subworkflow_calls:
            if call.id == call_id:
                return call
        return None

    def get_parameter_node_by_id(self, param_id: str) -> Optional[ParameterNode]:
        """Get a regular parameter node by its ID."""
        for param in self.parameters:
            if param.id == param_id:
                return param
        return None

    def get_list_parameter_node_by_id(self, param_id: str) -> Optional[ListParameterNode]:
        """Get a list parameter node by its ID."""
        for param in self.list_parameters:
            if param.id == param_id:
                return param
        return None

    def get_dict_parameter_node_by_id(self, param_id: str) -> Optional[DictParameterNode]:
        """Get a dict parameter node by its ID."""
        for param in self.dict_parameters:
            if param.id == param_id:
                return param
        return None

    def get_any_parameter_node_by_id(self, param_id: str):
        """Get any parameter node (regular, list, or dict) by its ID."""
        node = self.get_parameter_node_by_id(param_id)
        if node:
            return node
        node = self.get_list_parameter_node_by_id(param_id)
        if node:
            return node
        return self.get_dict_parameter_node_by_id(param_id)

    def get_all_nodes(self) -> List[Any]:
        """Get all nodes (functions, sub-workflow calls, parameters)."""
        nodes = []
        if self.controller:
            nodes.append(self.controller)
        nodes.extend(self.functions)
        nodes.extend(self.subworkflow_calls)
        nodes.extend(self.parameters)
        nodes.extend(self.list_parameters)
        nodes.extend(self.dict_parameters)
        return nodes

    def merge_parameters_for_function(self, func: WorkflowFunction) -> Dict[str, Any]:
        """
        Merge parameters from connected parameter nodes with function's own parameters.

        Handles three types of parameter nodes:
        - ParameterNode: Regular key-value parameters (merged as dict)
        - ListParameterNode: List of items, mapped to targetParam (e.g., substances)
        - DictParameterNode: Dictionary entries (merged as dict)

        Special handling for substance definitions:
        - If a regular parameter node has 'name' and 'diffusion_coeff' keys,
          it's treated as a substance definition and collected into 'substances' list.
        """
        merged = {}
        substances = []

        for param_node_id in func.parameter_nodes:
            # Check regular parameter nodes
            param_node = self.get_parameter_node_by_id(param_node_id)
            if param_node:
                if 'name' in param_node.parameters and 'diffusion_coeff' in param_node.parameters:
                    substances.append(param_node.parameters)
                else:
                    merged.update(param_node.parameters)
                continue

            # Check list parameter nodes
            list_node = self.get_list_parameter_node_by_id(param_node_id)
            if list_node:
                # Map list items to the target parameter name
                target_param = getattr(list_node, 'target_param', None) or 'substances'
                merged[target_param] = list_node.items
                continue

            # Check dict parameter nodes
            dict_node = self.get_dict_parameter_node_by_id(param_node_id)
            if dict_node:
                # Convert entries to a dictionary
                for entry in dict_node.entries:
                    merged[entry.key] = entry.value

        if substances:
            merged['substances'] = substances

        merged.update(func.parameters)
        return merged

    def merge_parameters_for_subworkflow_call(self, call: SubWorkflowCall) -> Dict[str, Any]:
        """
        Merge parameters from connected parameter nodes with sub-workflow call's own parameters.
        """
        merged = {}

        for param_node_id in call.parameter_nodes:
            param_node = self.get_parameter_node_by_id(param_node_id)
            if param_node:
                merged.update(param_node.parameters)

        merged.update(call.parameters)
        return merged


@dataclass
class WorkflowDefinition:
    """
    Complete workflow definition for an OpenCellComms simulation.

    Supports both legacy stage-based workflows and new sub-workflow-based workflows.

    Attributes:
        version: Workflow schema version (for future compatibility)
                 "1.0" = legacy stage-based
                 "2.0" = new sub-workflow-based
        name: Human-readable workflow name
        description: Detailed description of the workflow
        stages: Dictionary mapping stage types to stage definitions (legacy, v1.0)
        subworkflows: Dictionary mapping sub-workflow names to sub-workflow definitions (v2.0)
        metadata: Additional metadata (author, creation date, etc.)
    """
    version: str = "2.0"
    name: str = "Untitled Workflow"
    description: str = ""
    stages: Dict[str, WorkflowStage] = field(default_factory=dict)
    subworkflows: Dict[str, SubWorkflow] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default structure based on version."""
        if self.version == "2.0":
            # New sub-workflow-based system
            if not self.subworkflows:
                # Create default main sub-workflow
                self.subworkflows = {
                    "main": SubWorkflow(
                        name="main",
                        description="Main workflow entry point",
                        deletable=False
                    )
                }
        elif self.version == "1.0":
            # Legacy stage-based system
            if not self.stages:
                self.stages = {
                    "initialization": WorkflowStage(),
                    "intracellular": WorkflowStage(),
                    "diffusion": WorkflowStage(),
                    "intercellular": WorkflowStage(),
                    "finalization": WorkflowStage()
                }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata
        }

        if self.version == "2.0":
            result["subworkflows"] = {
                name: subworkflow.to_dict()
                for name, subworkflow in self.subworkflows.items()
            }
        else:
            result["stages"] = {
                stage_name: stage.to_dict()
                for stage_name, stage in self.stages.items()
            }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """Create from dictionary (JSON deserialization)."""
        version = data.get("version", "1.0")

        if version == "2.0":
            # New sub-workflow format
            subworkflows = {
                name: SubWorkflow.from_dict(name, subworkflow_data)
                for name, subworkflow_data in data.get("subworkflows", {}).items()
            }
            return cls(
                version=version,
                name=data.get("name", "Untitled Workflow"),
                description=data.get("description", ""),
                subworkflows=subworkflows,
                metadata=data.get("metadata", {})
            )
        else:
            # Legacy stage format
            stages = {
                stage_name: WorkflowStage.from_dict(stage_data)
                for stage_name, stage_data in data.get("stages", {}).items()
            }
            return cls(
                version=version,
                name=data.get("name", "Untitled Workflow"),
                description=data.get("description", ""),
                stages=stages,
                metadata=data.get("metadata", {})
            )

    def get_stage(self, stage_name: str) -> Optional[WorkflowStage]:
        """Get a workflow stage by name (legacy v1.0)."""
        return self.stages.get(stage_name)

    def get_subworkflow(self, subworkflow_name: str) -> Optional[SubWorkflow]:
        """Get a sub-workflow by name (v2.0)."""
        return self.subworkflows.get(subworkflow_name)
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate the workflow definition.

        Returns:
            Dictionary with:
                - 'valid': bool indicating if workflow is valid
                - 'errors': List of critical error messages
                - 'warnings': List of warning messages
        """
        errors = []
        warnings = []

        # Check version
        if self.version not in ["1.0", "2.0"]:
            errors.append(f"Unsupported workflow version: {self.version}")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        if self.version == "1.0":
            # Legacy stage-based validation
            errors.extend(self._validate_stages())
        else:
            # New sub-workflow-based validation
            stage_errors, stage_warnings = self._validate_subworkflows()
            errors.extend(stage_errors)
            warnings.extend(stage_warnings)

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def _validate_stages(self) -> List[str]:
        """Validate legacy stage-based workflow."""
        errors = []

        for stage_name, stage in self.stages.items():
            # Check that execution order references valid function IDs
            function_ids = {f.id for f in stage.functions}
            for func_id in stage.execution_order:
                if func_id not in function_ids:
                    errors.append(
                        f"Stage '{stage_name}': execution_order references "
                        f"unknown function ID '{func_id}'"
                    )

            # Check for duplicate function IDs
            if len(function_ids) != len(stage.functions):
                errors.append(f"Stage '{stage_name}': duplicate function IDs found")

        return errors

    def _validate_subworkflows(self) -> tuple[List[str], List[str]]:
        """Validate sub-workflow-based workflow."""
        errors = []
        warnings = []

        # 1. Main workflow validation
        if 'main' not in self.subworkflows:
            errors.append("CRITICAL: Main workflow is missing. Every workflow must have a 'main' entry point.")
            return errors, warnings

        main_workflow = self.subworkflows['main']
        if not main_workflow.controller:
            errors.append("Main workflow must have a controller node (entry point).")

        if main_workflow.deletable:
            errors.append("Main workflow must not be deletable.")

        # 2. Sub-workflow naming validation
        reserved_names = ['init', 'system']
        for name in self.subworkflows.keys():
            if name.lower() in reserved_names and name != 'main':
                errors.append(f"Sub-workflow name '{name}' is reserved. Please choose a different name.")

            # Check naming convention
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
                errors.append(
                    f"Sub-workflow name '{name}' is invalid. "
                    f"Must start with a letter and contain only letters, numbers, and underscores."
                )

            # Check name length
            if len(name) > 50:
                errors.append(f"Sub-workflow name '{name}' is too long (max 50 characters).")

        # Check for duplicate names (case-insensitive)
        names_lower = [n.lower() for n in self.subworkflows.keys()]
        if len(names_lower) != len(set(names_lower)):
            errors.append("Duplicate sub-workflow names detected (case-insensitive).")

        # 3. Controller node validation
        for subworkflow_name, subworkflow in self.subworkflows.items():
            if not subworkflow.controller:
                errors.append(
                    f"Sub-workflow '{subworkflow_name}' has no controller node. "
                    f"Each sub-workflow must have exactly one controller as entry point."
                )

        # 4. Sub-workflow reference validation
        available_subworkflows = set(self.subworkflows.keys())
        for subworkflow_name, subworkflow in self.subworkflows.items():
            for call in subworkflow.subworkflow_calls:
                target = call.subworkflow_name

                # Check if target exists
                if target not in available_subworkflows:
                    errors.append(
                        f"Sub-workflow '{subworkflow_name}' calls non-existent sub-workflow '{target}'. "
                        f"Available sub-workflows: {', '.join(available_subworkflows)}"
                    )

                # Check for self-reference (direct recursion)
                if target == subworkflow_name:
                    warnings.append(
                        f"⚠️  Sub-workflow '{subworkflow_name}' calls itself directly. "
                        f"This will cause infinite recursion unless iterations are limited."
                    )

        # 5. Circular dependency detection
        circular_warnings = self._detect_circular_dependencies()
        warnings.extend(circular_warnings)

        # 6. Execution order validation
        for subworkflow_name, subworkflow in self.subworkflows.items():
            all_node_ids = {f.id for f in subworkflow.functions}
            all_node_ids.update({c.id for c in subworkflow.subworkflow_calls})

            for node_id in subworkflow.execution_order:
                if node_id not in all_node_ids:
                    errors.append(
                        f"Sub-workflow '{subworkflow_name}': execution_order references "
                        f"unknown node ID '{node_id}'"
                    )

            # Check for duplicate IDs
            all_ids = [f.id for f in subworkflow.functions]
            all_ids.extend([c.id for c in subworkflow.subworkflow_calls])
            all_ids.extend([p.id for p in subworkflow.parameters])
            if subworkflow.controller:
                all_ids.append(subworkflow.controller.id)

            if len(all_ids) != len(set(all_ids)):
                errors.append(f"Sub-workflow '{subworkflow_name}': duplicate node IDs found")

        # 7. Iterations parameter validation
        for subworkflow_name, subworkflow in self.subworkflows.items():
            for call in subworkflow.subworkflow_calls:
                iterations = call.iterations

                try:
                    iterations_int = int(iterations)

                    if iterations_int < 1:
                        errors.append(
                            f"Sub-workflow call in '{subworkflow_name}' has invalid iterations: {iterations}. "
                            f"Must be >= 1."
                        )

                    if iterations_int > 1000:
                        warnings.append(
                            f"⚠️  Sub-workflow call in '{subworkflow_name}' has very high iterations: {iterations}. "
                            f"This may cause performance issues."
                        )

                except (ValueError, TypeError):
                    errors.append(
                        f"Sub-workflow call in '{subworkflow_name}' has invalid iterations value: {iterations}. "
                        f"Must be an integer >= 1."
                    )

        # 8. Description validation (warnings only)
        for subworkflow_name, subworkflow in self.subworkflows.items():
            if not subworkflow.description.strip():
                warnings.append(
                    f"⚠️  Sub-workflow '{subworkflow_name}' has no description. "
                    f"Add a description to help users understand what this sub-workflow does."
                )

        return errors, warnings

    def _detect_circular_dependencies(self) -> List[str]:
        """
        Detect circular dependencies using DFS-based cycle detection.
        Returns list of warning messages about circular dependencies.
        """
        warnings = []

        # Build dependency graph
        graph = {}
        for subworkflow_name, subworkflow in self.subworkflows.items():
            graph[subworkflow_name] = []
            for call in subworkflow.subworkflow_calls:
                if call.subworkflow_name:
                    graph[subworkflow_name].append(call.subworkflow_name)

        # DFS to detect cycles
        def dfs(node: str, visited: Set[str], rec_stack: Set[str], path: List[str]) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle = dfs(neighbor, visited, rec_stack, path[:])
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            rec_stack.remove(node)
            return None

        visited: Set[str] = set()
        for subworkflow_name in graph.keys():
            if subworkflow_name not in visited:
                cycle = dfs(subworkflow_name, visited, set(), [])
                if cycle:
                    cycle_str = ' → '.join(cycle)
                    warnings.append(
                        f"⚠️  CIRCULAR DEPENDENCY DETECTED: {cycle_str}\n"
                        f"   This will cause infinite recursion. Consider:\n"
                        f"   - Setting 'iterations' parameter to limit execution\n"
                        f"   - Adding conditional logic to break the cycle\n"
                        f"   - Restructuring your workflow to avoid the cycle"
                    )

        return warnings

