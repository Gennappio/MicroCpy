"""
Diffusion solver ports (interfaces) - no implementation details.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np
from dataclasses import dataclass

from ...core.domain.units import Concentration, Diffusivity


@dataclass(frozen=True)
class SteadyStateEquationSpec:
    """
    Value object describing a steady-state diffusion equation.
    Pure data - no behavior, no FiPy knowledge.
    """
    substance_name: str
    diffusion_coeff: Diffusivity
    initial_concentration: Concentration
    boundary_type: str  # "fixed", "no_flux", etc.
    boundary_value: Concentration
    source_field: np.ndarray  # mM/s, already mapped to mesh indices
    
    def __post_init__(self):
        """Validate the equation spec."""
        if self.source_field.ndim != 1:
            raise ValueError("source_field must be 1D array matching mesh size")
        if self.diffusion_coeff.value <= 0:
            raise ValueError("diffusion_coeff must be positive")


class DiffusionSolver(ABC):
    """
    Port (interface) for solving steady-state diffusion equations.
    
    Implementations handle the actual solver technology (FiPy, finite differences, etc.)
    but must satisfy this contract.
    """
    
    @abstractmethod
    def solve_steady_state(self, equation: SteadyStateEquationSpec) -> np.ndarray:
        """
        Solve steady-state diffusion equation.
        
        Args:
            equation: Complete specification of the equation to solve
            
        Returns:
            np.ndarray: Concentration field (mM) with same shape as source_field
            
        Raises:
            SolverError: If solution fails to converge or other solver issues
        """
        pass
    
    @abstractmethod
    def get_mesh_info(self) -> Dict[str, Any]:
        """
        Return mesh metadata for debugging/validation.
        
        Returns:
            Dict with keys like 'shape', 'spacing', 'total_cells', etc.
        """
        pass


class SolverError(Exception):
    """Raised when diffusion solver encounters problems."""
    pass


class BoundaryConditionProvider(ABC):
    """
    Port for applying boundary conditions to solver variables.
    
    Separates boundary logic from solver implementation.
    """
    
    @abstractmethod
    def apply_boundaries(self, equation: SteadyStateEquationSpec, solver_context: Any) -> None:
        """
        Apply boundary conditions to the solver's internal variables.
        
        Args:
            equation: The equation spec with boundary info
            solver_context: Solver-specific context (e.g., FiPy variable)
        """
        pass
