"""
Workflow migration utility for MicroC.

Provides tools to migrate v1.0 stage-based workflows to v2.0 sub-workflow format.
"""

from typing import Dict, Any
from .schema import (
    WorkflowDefinition,
    SubWorkflow,
    WorkflowFunction,
    SubWorkflowCall,
    ParameterNode,
    ControllerNode
)


class WorkflowMigrator:
    """Migrates v1.0 workflows to v2.0 format."""
    
    @staticmethod
    def migrate_to_v2(workflow: WorkflowDefinition) -> WorkflowDefinition:
        """
        Migrate a v1.0 workflow to v2.0 format.
        
        Args:
            workflow: v1.0 WorkflowDefinition
            
        Returns:
            v2.0 WorkflowDefinition with sub-workflows
            
        Raises:
            ValueError: If workflow is already v2.0 or invalid
        """
        if workflow.version == "2.0":
            raise ValueError("Workflow is already v2.0 format")
        
        if workflow.version != "1.0":
            raise ValueError(f"Unsupported workflow version: {workflow.version}")
        
        # Create sub-workflows from stages
        subworkflows = {}
        
        # Standard stage names in v1.0
        stage_names = [
            "initialization",
            "macrostep",
            "intracellular",
            "microenvironment",
            "intercellular",
            "finalization"
        ]
        
        for stage_name in stage_names:
            stage = workflow.stages.get(stage_name)
            if stage and (stage.functions or stage.parameters):
                # Create controller node for this sub-workflow
                controller = ControllerNode(
                    id=f"controller-{stage_name}",
                    label=f"{stage_name.upper()} CONTROLLER",
                    position={"x": 100, "y": 100},
                    number_of_steps=stage.steps
                )
                
                # Create sub-workflow
                subworkflows[stage_name] = SubWorkflow(
                    name=stage_name,
                    description=f"Migrated from v1.0 {stage_name} stage",
                    controller=controller,
                    functions=stage.functions.copy(),
                    subworkflow_calls=[],
                    parameters=stage.parameters.copy(),
                    execution_order=stage.execution_order.copy(),
                    enabled=stage.enabled,
                    deletable=False  # Standard stages are not deletable
                )
        
        # Create main sub-workflow that calls the standard stages in order
        main_calls = []
        main_execution_order = []
        
        for i, stage_name in enumerate(stage_names):
            if stage_name in subworkflows:
                call_id = f"call-{stage_name}"
                main_calls.append(SubWorkflowCall(
                    id=call_id,
                    subworkflow_name=stage_name,
                    iterations=1,
                    parameters={},
                    enabled=True,
                    description=f"Execute {stage_name}",
                    parameter_nodes=[],
                    context_mapping={}
                ))
                main_execution_order.append(call_id)
        
        # Create main controller
        main_controller = ControllerNode(
            id="controller-main",
            label="MAIN CONTROLLER",
            position={"x": 100, "y": 100},
            number_of_steps=1
        )
        
        # Create main sub-workflow
        subworkflows["main"] = SubWorkflow(
            name="main",
            description="Main workflow - migrated from v1.0",
            controller=main_controller,
            functions=[],
            subworkflow_calls=main_calls,
            parameters=[],
            execution_order=main_execution_order,
            enabled=True,
            deletable=False
        )
        
        # Create new v2.0 workflow
        return WorkflowDefinition(
            version="2.0",
            name=workflow.name,
            description=workflow.description + " (Migrated to v2.0)",
            subworkflows=subworkflows,
            metadata={
                **workflow.metadata,
                "migrated_from": "1.0",
                "original_version": "1.0"
            }
        )
    
    @staticmethod
    def migrate_file(input_path: str, output_path: str):
        """
        Migrate a v1.0 workflow file to v2.0 format.
        
        Args:
            input_path: Path to v1.0 workflow JSON file
            output_path: Path where to save v2.0 workflow JSON file
        """
        from .loader import WorkflowLoader
        
        # Load v1.0 workflow
        workflow_v1 = WorkflowLoader.load(input_path)
        
        # Migrate to v2.0
        workflow_v2 = WorkflowMigrator.migrate_to_v2(workflow_v1)
        
        # Save v2.0 workflow
        WorkflowLoader.save(workflow_v2, output_path)
        
        print(f"[MIGRATE] Successfully migrated workflow from {input_path} to {output_path}")

