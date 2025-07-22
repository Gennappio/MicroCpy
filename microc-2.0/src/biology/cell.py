"""
Cell implementation for MicroC 2.0

Provides a modular cell system with customizable behavior through hooks.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import uuid

from interfaces.base import ICell
# Import custom functions directly
import importlib.util
from pathlib import Path

@dataclass
class CellState:
    """Immutable cell state representation"""
    id: str
    position: tuple[int, int]
    phenotype: str
    age: float
    division_count: int
    metabolic_state: Dict[str, float] = field(default_factory=dict)
    gene_states: Dict[str, bool] = field(default_factory=dict)
    tq_wait_time: float = 0.0  # Time waiting in Growth_Arrest state (TQ time)
    
    def with_updates(self, **kwargs) -> 'CellState':
        """Create new CellState with updates (immutable pattern)"""
        updates = {
            'id': self.id,
            'position': self.position,
            'phenotype': self.phenotype,
            'age': self.age,
            'division_count': self.division_count,
            'metabolic_state': self.metabolic_state.copy(),
            'gene_states': self.gene_states.copy(),
            'tq_wait_time': self.tq_wait_time
        }
        updates.update(kwargs)
        return CellState(**updates)

class Cell(ICell):
    """
    Modular cell implementation with customizable behavior

    All cell behaviors are implemented via direct function calls to custom functions.
    """

    def __init__(self, position: tuple[int, int], phenotype: str = "Growth_Arrest",
                 cell_id: Optional[str] = None, custom_functions_module=None):

        self.state = CellState(
            id=cell_id or str(uuid.uuid4()),
            position=position,
            phenotype=phenotype,
            age=0.0,
            division_count=0,
            tq_wait_time=0.0
        )

        # Load custom functions module
        self.custom_functions = self._load_custom_functions(custom_functions_module)

        # No default parameters - all values must come from configuration
        # This ensures proper configuration and prevents hidden hardcoded values
        self.default_params = {}

    def _load_custom_functions(self, custom_functions_module):
        """Load custom functions from module"""
        if custom_functions_module is None:
            return None

        try:
            if isinstance(custom_functions_module, str):
                # Load from file path
                spec = importlib.util.spec_from_file_location("custom_functions", custom_functions_module)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    return module
            else:
                # Already a module
                return custom_functions_module
        except Exception as e:
            print(f"Warning: Could not load custom functions: {e}")
            return None
    
    def update_phenotype(self, local_environment: Dict[str, float],
                        gene_states: Dict[str, bool], config=None) -> str:
        """Update cell phenotype based on environment and genes"""
        if self.custom_functions and hasattr(self.custom_functions, 'update_cell_phenotype'):
            # Call custom function
            new_phenotype = self.custom_functions.update_cell_phenotype(
                cell_state=self.state.__dict__,
                local_environment=local_environment,
                gene_states=gene_states,
                current_phenotype=self.state.phenotype,
                config=config
            )
        else:
            # Fail explicitly if custom function is not provided
            raise RuntimeError(
                f"❌ Custom function 'update_cell_phenotype' is required but not found!\n"
                f"   Please ensure your custom functions module defines this function.\n"
                f"   Custom functions module: {self.custom_functions}"
            )

        # Update state
        self.state = self.state.with_updates(
            phenotype=new_phenotype,
            gene_states=gene_states
        )

        return new_phenotype
    

    
    def calculate_metabolism(self, local_environment: Dict[str, float], config=None) -> Dict[str, float]:
        """Calculate metabolic production/consumption rates"""
        if self.custom_functions and hasattr(self.custom_functions, 'calculate_cell_metabolism'):
            # Call custom function
            return self.custom_functions.calculate_cell_metabolism(
                local_environment=local_environment,
                cell_state=self.state.__dict__,
                config=config
            )
        else:
            # Fail explicitly if custom function is not provided
            raise RuntimeError(
                f"❌ Custom function 'calculate_cell_metabolism' is required but not found!\n"
                f"   Please ensure your custom functions module defines this function.\n"
                f"   Custom functions module: {self.custom_functions}"
            )
    




    def should_divide(self, config=None) -> bool:
        """Check if cell should attempt division"""
        if self.custom_functions and hasattr(self.custom_functions, 'should_divide'):
            # Call custom function
            return self.custom_functions.should_divide(
                cell=self,
                config=config or {}
            )
        else:
            # Fail explicitly if custom function is not provided
            raise RuntimeError(
                f"❌ Custom function 'should_divide' is required but not found!\n"
                f"   Please ensure your custom functions module defines this function.\n"
                f"   Custom functions module: {self.custom_functions}"
            )
    

    
    def should_die(self, local_environment: Dict[str, float], config=None) -> bool:
        """Check if cell should die"""
        if self.custom_functions and hasattr(self.custom_functions, 'check_cell_death'):
            # Call custom function
            return self.custom_functions.check_cell_death(
                cell_state=self.state.__dict__,
                local_environment=local_environment
            )
        else:
            # Fail explicitly if custom function is not provided
            raise RuntimeError(
                f"❌ Custom function 'check_cell_death' is required but not found!\n"
                f"   Please ensure your custom functions module defines this function.\n"
                f"   Custom functions module: {self.custom_functions}"
            )
    


    def _get_parameter_from_config(self, config, param_name: str, default_value=None):
        """Get parameter from config - requires explicit location"""
        if not config:
            return default_value

        # Direct access only - no path searching
        if hasattr(config, param_name):
            return getattr(config, param_name)
        elif isinstance(config, dict) and param_name in config:
            return config[param_name]
        else:
            return default_value

    # Environmental modulation removed - belongs in custom functions only
    # Default cell behavior should not make assumptions about environmental effects

    def age(self, dt: float):
        """Age the cell by dt hours"""
        self.state = self.state.with_updates(age=self.state.age + dt)
    
    def divide(self) -> 'Cell':
        """Create daughter cell (returns new cell, updates this cell)"""
        # Create daughter cell
        daughter = Cell(
            position=self.state.position,  # Same position initially
            phenotype=self.state.phenotype,
            custom_functions_module=self.custom_functions
        )
        
        # Update parent cell
        self.state = self.state.with_updates(
            division_count=self.state.division_count + 1,
            age=0.0  # Reset age after division
        )
        
        return daughter
    
    def move_to(self, new_position: tuple[int, int]):
        """Move cell to new position"""
        self.state = self.state.with_updates(position=new_position)
    
    def get_state(self) -> CellState:
        """Get current cell state (immutable)"""
        return self.state
    
    def __repr__(self) -> str:
        return (f"Cell(id={self.state.id[:8]}, pos={self.state.position}, "
                f"phenotype={self.state.phenotype}, age={self.state.age:.1f}h)")
