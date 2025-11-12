"""
Workflow schema definitions for MicroC.

Defines the data structures for workflow configurations that can be
serialized to/from JSON and executed by the workflow executor.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class WorkflowStageType(Enum):
    """Types of workflow stages in the simulation lifecycle."""
    INITIALIZATION = "initialization"
    INTRACELLULAR = "intracellular"
    DIFFUSION = "diffusion"
    INTERCELLULAR = "intercellular"
    FINALIZATION = "finalization"


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
    """
    id: str
    function_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "function_name": self.function_name,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "position": self.position,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowFunction":
        """Create from dictionary (JSON deserialization)."""
        return cls(
            id=data["id"],
            function_name=data["function_name"],
            parameters=data.get("parameters", {}),
            enabled=data.get("enabled", True),
            position=data.get("position", {"x": 0, "y": 0}),
            description=data.get("description", "")
        )


@dataclass
class WorkflowStage:
    """
    Represents a stage in the workflow (e.g., intracellular, diffusion).
    
    Attributes:
        functions: List of functions to execute in this stage
        execution_order: Ordered list of function IDs defining execution sequence
        enabled: Whether this stage should be executed
    """
    functions: List[WorkflowFunction] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "functions": [f.to_dict() for f in self.functions],
            "execution_order": self.execution_order,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowStage":
        """Create from dictionary (JSON deserialization)."""
        functions = [WorkflowFunction.from_dict(f) for f in data.get("functions", [])]
        return cls(
            functions=functions,
            execution_order=data.get("execution_order", []),
            enabled=data.get("enabled", True)
        )
    
    def get_function_by_id(self, function_id: str) -> Optional[WorkflowFunction]:
        """Get a function by its ID."""
        for func in self.functions:
            if func.id == function_id:
                return func
        return None
    
    def get_enabled_functions_in_order(self) -> List[WorkflowFunction]:
        """Get enabled functions in execution order."""
        result = []
        for func_id in self.execution_order:
            func = self.get_function_by_id(func_id)
            if func and func.enabled:
                result.append(func)
        return result


@dataclass
class WorkflowDefinition:
    """
    Complete workflow definition for a MicroC simulation.
    
    Attributes:
        version: Workflow schema version (for future compatibility)
        name: Human-readable workflow name
        description: Detailed description of the workflow
        stages: Dictionary mapping stage types to stage definitions
        metadata: Additional metadata (author, creation date, etc.)
    """
    version: str = "1.0"
    name: str = "Untitled Workflow"
    description: str = ""
    stages: Dict[str, WorkflowStage] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default stages if not provided."""
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
        return {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "stages": {
                stage_name: stage.to_dict() 
                for stage_name, stage in self.stages.items()
            },
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """Create from dictionary (JSON deserialization)."""
        stages = {
            stage_name: WorkflowStage.from_dict(stage_data)
            for stage_name, stage_data in data.get("stages", {}).items()
        }
        return cls(
            version=data.get("version", "1.0"),
            name=data.get("name", "Untitled Workflow"),
            description=data.get("description", ""),
            stages=stages,
            metadata=data.get("metadata", {})
        )
    
    def get_stage(self, stage_name: str) -> Optional[WorkflowStage]:
        """Get a workflow stage by name."""
        return self.stages.get(stage_name)
    
    def validate(self) -> List[str]:
        """
        Validate the workflow definition.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check version
        if self.version != "1.0":
            errors.append(f"Unsupported workflow version: {self.version}")
        
        # Check each stage
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

