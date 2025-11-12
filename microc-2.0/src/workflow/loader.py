"""
Workflow loader for MicroC.

Handles loading and saving workflow definitions from/to JSON files.
"""

import json
from pathlib import Path
from typing import Union, Optional
from .schema import WorkflowDefinition


class WorkflowLoader:
    """Loads and saves workflow definitions from/to JSON files."""
    
    @staticmethod
    def load(file_path: Union[str, Path]) -> WorkflowDefinition:
        """
        Load a workflow definition from a JSON file.
        
        Args:
            file_path: Path to the workflow JSON file
            
        Returns:
            WorkflowDefinition object
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the JSON is invalid or workflow validation fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in workflow file: {e}")
        
        # Create workflow from dictionary
        workflow = WorkflowDefinition.from_dict(data)
        
        # Validate workflow
        errors = workflow.validate()
        if errors:
            error_msg = "Workflow validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
        
        return workflow
    
    @staticmethod
    def save(workflow: WorkflowDefinition, file_path: Union[str, Path], indent: int = 2):
        """
        Save a workflow definition to a JSON file.
        
        Args:
            workflow: WorkflowDefinition to save
            file_path: Path where to save the JSON file
            indent: JSON indentation level (default: 2)
            
        Raises:
            ValueError: If workflow validation fails
        """
        # Validate before saving
        errors = workflow.validate()
        if errors:
            error_msg = "Cannot save invalid workflow:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
        
        file_path = Path(file_path)
        
        # Create parent directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary and save
        data = workflow.to_dict()
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=indent)
    
    @staticmethod
    def load_or_none(file_path: Union[str, Path]) -> Optional[WorkflowDefinition]:
        """
        Load a workflow definition, returning None if file doesn't exist or is invalid.
        
        Args:
            file_path: Path to the workflow JSON file
            
        Returns:
            WorkflowDefinition object or None if loading fails
        """
        try:
            return WorkflowLoader.load(file_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"[WORKFLOW] Could not load workflow: {e}")
            return None

