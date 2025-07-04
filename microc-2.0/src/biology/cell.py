"""
Cell implementation for MicroC 2.0

Provides a modular cell system with customizable behavior through hooks.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import uuid

from interfaces.base import ICell, CustomizableComponent
from interfaces.hooks import get_hook_manager

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

class Cell(ICell, CustomizableComponent):
    """
    Modular cell implementation with customizable behavior
    
    All cell behaviors can be customized via the hook system without
    modifying this core implementation.
    """
    
    def __init__(self, position: tuple[int, int], phenotype: str = "Growth_Arrest",
                 cell_id: Optional[str] = None, custom_functions_module=None):
        super().__init__(custom_functions_module)

        self.state = CellState(
            id=cell_id or str(uuid.uuid4()),
            position=position,
            phenotype=phenotype,
            age=0.0,
            division_count=0,
            tq_wait_time=0.0
        )
        
        self.hook_manager = get_hook_manager()
        
        # No default parameters - all values must come from configuration
        # This ensures proper configuration and prevents hidden hardcoded values
        self.default_params = {}
    
    def update_phenotype(self, local_environment: Dict[str, float], 
                        gene_states: Dict[str, bool]) -> str:
        """Update cell phenotype based on environment and genes"""
        try:
            # Try custom function first
            new_phenotype = self.hook_manager.call_hook(
                "custom_update_cell_phenotype",
                local_environment=local_environment,
                gene_states=gene_states,
                current_phenotype=self.state.phenotype
            )
            
            # Update state
            self.state = self.state.with_updates(
                phenotype=new_phenotype,
                gene_states=gene_states
            )
            
            return new_phenotype
            
        except NotImplementedError:
            # Fall back to default implementation
            return self._default_update_phenotype(local_environment, gene_states)
    
    def _default_update_phenotype(self, local_environment: Dict[str, float],
                                 gene_states: Dict[str, bool]) -> str:
        """Default phenotype update logic based on gene network outputs"""

        # Use gene network outputs to determine phenotype
        # Priority order (highest to lowest):
        # 1. Necrosis (immediate death condition)
        # 2. Apoptosis (programmed death)
        # 3. Proliferation (active growth)
        # 4. Growth_Arrest (quiescent state)
        new_phenotype = "Quiescent"
       
        if gene_states.get('Apoptosis', False):
            new_phenotype = "Apoptosis"
        if gene_states.get('Proliferation', False):
            new_phenotype = "Proliferation"
        if gene_states.get('Growth_Arrest', False):
            new_phenotype = "Growth_Arrest"
        if gene_states.get('Necrosis', False):
            new_phenotype = "Necrosis"

        # Update state
        self.state = self.state.with_updates(
            phenotype=new_phenotype,
            gene_states=gene_states
        )

        return new_phenotype
    
    def calculate_metabolism(self, local_environment: Dict[str, float], config=None) -> Dict[str, float]:
        """Calculate metabolic production/consumption rates"""
        try:
            # Try custom function first
            return self.hook_manager.call_hook(
                "custom_calculate_cell_metabolism",
                local_environment=local_environment,
                cell_state=self.state.__dict__,
                config=config
            )

        except NotImplementedError:
            # Fall back to default implementation
            return self._default_calculate_metabolism(local_environment, config)
    
    def _default_calculate_metabolism(self, local_environment: Dict[str, float], config=None) -> Dict[str, float]:
        """Default metabolism calculation - uses production_rate and uptake_rate from substance configs"""

        # Initialize reactions dictionary
        reactions = {}

        # Get substance configurations from config
        if not hasattr(config, 'substances') or not config.substances:
            raise ValueError(
                "❌ No substance configurations found!\n"
                "The config must have a 'substances' section with production_rate and uptake_rate for each substance."
            )

        # For each substance, use the production_rate and uptake_rate from config
        for substance_name, substance_config in config.substances.items():
            # Get production and uptake rates from substance config
            production_rate = getattr(substance_config, 'production_rate', 0.0)
            uptake_rate = getattr(substance_config, 'uptake_rate', 0.0)

            # Net reaction rate = production - uptake
            net_rate = production_rate - uptake_rate
            reactions[substance_name] = net_rate

        return reactions



    def should_divide(self, config=None) -> bool:
        """Check if cell should attempt division"""
        try:
            # Try custom function first
            return self.hook_manager.call_hook(
                "custom_should_divide",
                cell=self,
                config=config or {}
            )

        except NotImplementedError:
            # Fall back to default implementation
            return self._default_should_divide(config)
    
    def _default_should_divide(self, config=None) -> bool:
        """Default division logic - uses biological default behaviors"""

        # Default biological behavior: only proliferative cells can divide
        # Custom experiments can override this in custom functions
        default_dividing_phenotypes = ['Proliferation']

        # Get dividing phenotypes from config (optional override)
        dividing_phenotypes = self._get_parameter_from_config(config, 'dividing_phenotypes', default_dividing_phenotypes)

        # Check if current phenotype can divide
        if self.state.phenotype not in dividing_phenotypes:
            return False

        # Age-based division for proliferative cells
        # Get cell cycle time threshold - use config or reasonable default
        cell_cycle_time = self._get_parameter_from_config(config, 'cell_cycle_time', 240)  # 240 iterations default (24h at dt=0.1)

        return self.state.age >= cell_cycle_time
    
    def should_die(self, local_environment: Dict[str, float], config=None) -> bool:
        """Check if cell should die"""
        try:
            # Try custom function first
            return self.hook_manager.call_hook(
                "custom_check_cell_death",
                cell_state=self.state.__dict__,
                local_environment=local_environment
            )

        except NotImplementedError:
            # Fall back to default implementation
            return self._default_check_cell_death(local_environment, config)
    
    def _default_check_cell_death(self, local_environment: Dict[str, float], config=None) -> bool:
        """Default death logic - uses biological default behaviors"""

        # Default biological behaviors:
        # - Apoptotic cells die immediately (programmed cell death)
        # - Necrotic cells persist as necrotic mass (don't get removed)
        # - Other phenotypes follow age-based death only
        default_death_phenotypes = ['Apoptosis']
        default_persistent_phenotypes = ['Necrosis']

        # Get phenotype behaviors from config (optional override)
        death_phenotypes = self._get_parameter_from_config(config, 'death_phenotypes', default_death_phenotypes)
        persistent_phenotypes = self._get_parameter_from_config(config, 'persistent_phenotypes', default_persistent_phenotypes)

        # Check if current phenotype causes immediate death
        if self.state.phenotype in death_phenotypes:
            return True

        # Check if current phenotype should persist (not be removed)
        if self.state.phenotype in persistent_phenotypes:
            return False

        # Age-related death (very old cells) - backup mechanism
        # Get max age from config - use reasonable default if not specified
        max_age = self._get_parameter_from_config(config, 'max_cell_age', 500.0)  # 500 hours default

        if self.state.age > max_age:
            return True

        # Default: cells don't die from phenotype alone (except death/persistent phenotypes above)
        return False

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
