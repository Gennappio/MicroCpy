from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional, Union
import numpy as np


class ISubstanceSimulator(ABC):
    """Interface for substance diffusion-reaction simulators"""
    
    @abstractmethod
    def solve_steady_state(self, cell_reactions: Dict[Tuple[float, float], float]) -> bool:
        """Solve diffusion-reaction to steady state"""
        pass
    
    @abstractmethod
    def evaluate_at_point(self, position: Tuple[float, float]) -> float:
        """Get concentration at specific position"""
        pass
    
    @abstractmethod
    def get_field_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get X, Y, Z arrays for visualization"""
        pass

class ICell(ABC):
    """Interface for individual cell behavior"""
    
    @abstractmethod
    def update_phenotype(self, local_environment: Dict[str, float], 
                        gene_states: Dict[str, bool]) -> str:
        """Update cell phenotype based on environment and genes"""
        pass
    
    @abstractmethod
    def calculate_metabolism(self, local_environment: Dict[str, float]) -> Dict[str, float]:
        """Calculate metabolic production/consumption rates"""
        pass
    
    @abstractmethod
    def should_divide(self) -> bool:
        """Check if cell should attempt division"""
        pass
    
    @abstractmethod
    def should_die(self, local_environment: Dict[str, float]) -> bool:
        """Check if cell should die"""
        pass

class ICellPopulation(ABC):
    """Interface for cell population management"""
    
    @abstractmethod
    def add_cell(self, position: Union[Tuple[int, int], Tuple[int, int, int]], phenotype: str = "normal") -> bool:
        """Add cell at lattice position"""
        pass
    
    @abstractmethod
    def attempt_division(self, parent_id: str) -> bool:
        """Attempt to divide a cell"""
        pass
    
    @abstractmethod
    def remove_dead_cells(self) -> List[str]:
        """Remove dead cells and return their IDs"""
        pass
    
    @abstractmethod
    def get_substance_reactions(self) -> Dict[Tuple[float, float], Dict[str, float]]:
        """Get all cell reactions for substances"""
        pass

class IGeneNetwork(ABC):
    """Interface for gene regulatory networks"""
    
    @abstractmethod
    def set_input_states(self, inputs: Dict[str, bool]):
        """Set input node states"""
        pass
    
    @abstractmethod
    def step(self, num_steps: int = 1) -> Dict[str, bool]:
        """Run network for specified steps"""
        pass
    
    @abstractmethod
    def get_output_states(self) -> Dict[str, bool]:
        """Get current output node states"""
        pass

class IVisualization(ABC):
    """Interface for visualization components"""
    
    @abstractmethod
    def plot_substance_field(self, substance_name: str, data: np.ndarray, 
                           metadata: Dict[str, Any]) -> str:
        """Plot substance concentration field"""
        pass
    
    @abstractmethod
    def plot_cell_population(self, cell_positions: List[Tuple[int, int]], 
                           cell_phenotypes: List[str], metadata: Dict[str, Any]) -> str:
        """Plot cell population distribution"""
        pass

class IDataExporter(ABC):
    """Interface for data export components"""
    
    @abstractmethod
    def export_simulation_data(self, timestep: int, substance_data: Dict[str, np.ndarray],
                             cell_data: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
        """Export simulation data for a timestep"""
        pass
    
    @abstractmethod
    def finalize_export(self) -> str:
        """Finalize export and return output path"""
        pass

class ITimescaleOrchestrator(ABC):
    """Interface for multi-timescale coordination"""
    
    @abstractmethod
    def should_update_diffusion(self, current_step: int) -> bool:
        """Check if diffusion should be updated this step"""
        pass
    
    @abstractmethod
    def should_update_intracellular(self, current_step: int) -> bool:
        """Check if intracellular processes should be updated"""
        pass
    
    @abstractmethod
    def should_update_intercellular(self, current_step: int) -> bool:
        """Check if intercellular processes should be updated"""
        pass

class IPerformanceProfiler(ABC):
    """Interface for performance monitoring"""
    
    @abstractmethod
    def start_timer(self, operation_name: str):
        """Start timing an operation"""
        pass
    
    @abstractmethod
    def end_timer(self, operation_name: str) -> float:
        """End timing and return duration"""
        pass
    
    @abstractmethod
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        pass
