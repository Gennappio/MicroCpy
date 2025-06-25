"""
Substance simulation for MicroC 2.0

Provides FiPy-based diffusion-reaction simulation with bulletproof unit handling.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Any
import numpy as np
from fipy import CellVariable, DiffusionTerm, ImplicitSourceTerm, Viewer
from fipy.solvers import LinearLUSolver
from interfaces.base import ISubstanceSimulator, CustomizableComponent
from interfaces.hooks import get_hook_manager
from core.domain import MeshManager
from config.config import SubstanceConfig

@dataclass
class SimulationState:
    """Immutable simulation state representation"""
    concentration_field: np.ndarray
    time: float
    converged: bool
    iterations: int
    residual: float
    
    def with_updates(self, **kwargs) -> 'SimulationState':
        """Create new SimulationState with updates (immutable pattern)"""
        updates = {
            'concentration_field': self.concentration_field.copy(),
            'time': self.time,
            'converged': self.converged,
            'iterations': self.iterations,
            'residual': self.residual
        }
        updates.update(kwargs)
        return SimulationState(**updates)

class SubstanceSimulator(ISubstanceSimulator, CustomizableComponent):
    """
    FiPy-based substance diffusion-reaction simulator
    
    Handles steady-state and transient diffusion with cell reactions.
    All boundary conditions can be customized via the hook system.
    """
    
    def __init__(self, mesh_manager: MeshManager, substance_config: SubstanceConfig,
                 custom_functions_module=None):
        super().__init__(custom_functions_module)
        
        self.mesh_manager = mesh_manager
        self.substance_config = substance_config
        self.hook_manager = get_hook_manager()
        
        # Create FiPy variable
        self.concentration = CellVariable(
            name=substance_config.name,
            mesh=mesh_manager.mesh,
            value=substance_config.initial_value.millimolar
        )
        
        # Create equation terms
        self.diffusion_term = DiffusionTerm(coeff=substance_config.diffusion_coeff)
        # Create source term variable for cell reactions
        self.source_field = CellVariable(mesh=mesh_manager.mesh, value=0.0)
        self.source_term = ImplicitSourceTerm(coeff=self.source_field)
        
        # Simulation parameters
        self.solver = LinearLUSolver()
        self.tolerance = 1e-4  # Relaxed tolerance for better convergence
        self.max_iterations = 100  # Reduced iterations to avoid long runs
        
        # Current state
        self.state = SimulationState(
            concentration_field=np.array(self.concentration.value),
            time=0.0,
            converged=False,
            iterations=0,
            residual=float('inf')
        )
        
        # Set boundary conditions
        self._apply_boundary_conditions()
    
    def _apply_boundary_conditions(self):
        """Apply boundary conditions to the concentration field"""
        try:
            # Try custom boundary condition function
            for face_id in range(len(self.mesh_manager.mesh.faceCenters[0])):
                face_center = (
                    float(self.mesh_manager.mesh.faceCenters[0][face_id]),
                    float(self.mesh_manager.mesh.faceCenters[1][face_id])
                )
                
                boundary_value = self.hook_manager.call_hook(
                    "custom_calculate_boundary_conditions",
                    substance_name=self.substance_config.name,
                    position=face_center,
                    time=self.state.time
                )
                
                # Apply custom boundary value
                if self.mesh_manager.mesh.exteriorFaces[face_id]:
                    self.concentration.constrain(boundary_value, 
                                               where=self.mesh_manager.mesh.exteriorFaces[face_id])
                    
        except NotImplementedError:
            # Fall back to default boundary conditions
            self._default_apply_boundary_conditions()
    
    def _default_apply_boundary_conditions(self):
        """Default boundary condition application"""
        if self.substance_config.boundary_type == "fixed":
            # Fixed concentration on all boundaries
            self.concentration.constrain(
                self.substance_config.boundary_value.millimolar,
                where=self.mesh_manager.mesh.exteriorFaces
            )
        elif self.substance_config.boundary_type == "no_flux":
            # No flux (natural boundary condition - no explicit constraint needed)
            pass
        else:
            raise ValueError(f"Unknown boundary type: {self.substance_config.boundary_type}")
    
    def solve_steady_state(self, cell_reactions: Dict[Tuple[float, float], float]) -> bool:
        """Solve diffusion-reaction to steady state"""
        # Update source term with cell reactions
        self._update_source_term(cell_reactions)
        
        # Create equation
        equation = self.diffusion_term + self.source_term == 0
        
        # Solve iteratively
        converged = False
        iteration = 0
        residual = float('inf')
        
        for iteration in range(self.max_iterations):
            # Store previous values for convergence check
            old_concentration = self.concentration.value.copy()
            
            # Solve one iteration
            residual = equation.sweep(var=self.concentration, solver=self.solver)
            
            # Check convergence
            max_change = np.max(np.abs(self.concentration.value - old_concentration))
            if max_change < self.tolerance:
                converged = True
                break
        
        # Update state
        self.state = self.state.with_updates(
            concentration_field=np.array(self.concentration.value),
            converged=converged,
            iterations=iteration + 1,
            residual=float(residual)
        )
        
        return converged
    
    def _update_source_term(self, cell_reactions: Dict[Tuple[float, float], float]):
        """Update source term with cell reactions"""
        # Reset source field
        self.source_field.setValue(0.0)

        # Create source array
        source_array = np.zeros(self.mesh_manager.mesh.numberOfCells)

        # Add cell reactions
        for (x_pos, y_pos), reaction_rate in cell_reactions.items():
            # Find closest mesh cell
            cell_id = self._find_closest_cell(x_pos, y_pos)
            if cell_id is not None:
                # Convert reaction rate to source term
                # reaction_rate is in mol/s/cell, need to convert to mol/s/m³
                cell_volume_m3 = self.mesh_manager.cell_volume_m3
                source_density = reaction_rate / cell_volume_m3  # mol/s/m³

                # Convert to mM/s (FiPy units)
                # 1 mol/m³ = 1000 mM, so mol/s/m³ = 1000 mM/s
                source_array[cell_id] = source_density * 1000.0

        # Update source field with array
        self.source_field.setValue(source_array)
    
    def _find_closest_cell(self, x_pos: float, y_pos: float) -> Optional[int]:
        """Find mesh cell closest to given position"""
        # Get cell centers as numpy arrays
        cell_centers_x = np.array(self.mesh_manager.mesh.cellCenters[0])
        cell_centers_y = np.array(self.mesh_manager.mesh.cellCenters[1])

        # Calculate distances
        distances = np.sqrt((cell_centers_x - x_pos)**2 + (cell_centers_y - y_pos)**2)

        # Find closest cell
        closest_cell = np.argmin(distances)

        # Check if position is within mesh bounds
        mesh_bounds = self._get_mesh_bounds()
        if (mesh_bounds['x_min'] <= x_pos <= mesh_bounds['x_max'] and
            mesh_bounds['y_min'] <= y_pos <= mesh_bounds['y_max']):
            return int(closest_cell)
        else:
            return None
    
    def _get_mesh_bounds(self) -> Dict[str, float]:
        """Get mesh boundary coordinates"""
        # Convert FiPy mesh variables to numpy arrays
        cell_centers_x = np.array(self.mesh_manager.mesh.cellCenters[0])
        cell_centers_y = np.array(self.mesh_manager.mesh.cellCenters[1])

        return {
            'x_min': float(np.min(cell_centers_x)),
            'x_max': float(np.max(cell_centers_x)),
            'y_min': float(np.min(cell_centers_y)),
            'y_max': float(np.max(cell_centers_y))
        }
    
    def evaluate_at_point(self, position: Tuple[float, float]) -> float:
        """Get concentration at specific position"""
        x_pos, y_pos = position
        
        # Find closest cell
        cell_id = self._find_closest_cell(x_pos, y_pos)
        
        if cell_id is not None:
            return float(self.concentration.value[cell_id])
        else:
            # Outside mesh - return boundary value
            return self.substance_config.boundary_value.millimolar
    
    def get_field_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get X, Y, Z arrays for visualization"""
        # Get mesh coordinates
        x_coords = np.array(self.mesh_manager.mesh.cellCenters[0])
        y_coords = np.array(self.mesh_manager.mesh.cellCenters[1])
        z_values = np.array(self.concentration.value)
        
        # Reshape for visualization (assuming rectangular grid)
        nx, ny = self.mesh_manager.config.nx, self.mesh_manager.config.ny
        
        X = x_coords.reshape((ny, nx))
        Y = y_coords.reshape((ny, nx))
        Z = z_values.reshape((ny, nx))
        
        return X, Y, Z
    
    def get_concentration_at_positions(self, positions: Dict[Tuple[int, int], Any]) -> Dict[Tuple[int, int], float]:
        """Get concentrations at grid positions"""
        concentrations = {}
        
        for grid_pos in positions.keys():
            # Convert grid position to physical coordinates
            x_phys = (grid_pos[0] + 0.5) * self.mesh_manager.mesh.dx
            y_phys = (grid_pos[1] + 0.5) * self.mesh_manager.mesh.dy
            
            concentration = self.evaluate_at_point((float(x_phys), float(y_phys)))
            concentrations[grid_pos] = concentration
        
        return concentrations
    
    def get_simulation_info(self) -> Dict[str, Any]:
        """Get simulation information"""
        return {
            'substance_name': self.substance_config.name,
            'diffusion_coefficient': self.substance_config.diffusion_coeff,
            'boundary_type': self.substance_config.boundary_type,
            'boundary_value': self.substance_config.boundary_value.millimolar,
            'initial_value': self.substance_config.initial_value.millimolar,
            'mesh_cells': self.mesh_manager.mesh.numberOfCells,
            'converged': self.state.converged,
            'iterations': self.state.iterations,
            'residual': self.state.residual,
            'min_concentration': float(np.min(self.concentration.value)),
            'max_concentration': float(np.max(self.concentration.value)),
            'mean_concentration': float(np.mean(self.concentration.value))
        }
    
    def reset(self):
        """Reset simulation to initial conditions"""
        self.concentration.setValue(self.substance_config.initial_value.millimolar)
        self._apply_boundary_conditions()
        
        self.state = SimulationState(
            concentration_field=np.array(self.concentration.value),
            time=0.0,
            converged=False,
            iterations=0,
            residual=float('inf')
        )
    
    def get_state(self) -> SimulationState:
        """Get current simulation state (immutable)"""
        return self.state
    
    def __repr__(self) -> str:
        info = self.get_simulation_info()
        return (f"SubstanceSimulator({info['substance_name']}, "
                f"converged={info['converged']}, "
                f"mean_conc={info['mean_concentration']:.2f} mM)")
