"""
Multi-Substance Simulator

Handles simulation of all substances from the parameter files:
- Growth factors (FGF, TGFA, HGF)
- Receptor drugs (EGFRD, FGFRD, cMETD, MCT1D, GLUT1D)
- Essential metabolites (Oxygen, Glucose, Lactate, H, pH)
- Growth inhibitor (GI)

Implements associations and thresholds from parameter files.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path

# Import FiPy for diffusion simulation
try:
    from fipy import Grid2D, CellVariable, DiffusionTerm, ImplicitSourceTerm
    FIPY_AVAILABLE = True
except ImportError:
    FIPY_AVAILABLE = False
    print("Warning: FiPy not available. Using simplified diffusion model.")

# TODO: These config imports should be removed and passed as arguments instead
from config.config import MicroCConfig, SubstanceConfig, ThresholdConfig
from core.domain import MeshManager
# Hook system removed - using direct function calls

@dataclass
class SubstanceState:
    """State of a single substance"""
    name: str
    concentrations: np.ndarray  # 2D array of concentrations
    config: SubstanceConfig
    
    def get_concentration_at(self, position: Tuple[int, int]) -> float:
        """Get concentration at specific grid position"""
        x, y = position
        if 0 <= x < self.concentrations.shape[1] and 0 <= y < self.concentrations.shape[0]:
            return float(self.concentrations[y, x])
        return 0.0

@dataclass
class MultiSubstanceState:
    """State of all substances in the simulation"""
    substances: Dict[str, SubstanceState] = field(default_factory=dict)
    time: float = 0.0
    
    def get_local_environment(self, position: Tuple[int, int]) -> Dict[str, float]:
        """Get all substance concentrations at a position"""
        environment = {}
        for name, substance in self.substances.items():
            environment[f"{name.lower()}_concentration"] = substance.get_concentration_at(position)
        return environment
    
    def get_gene_network_inputs(self, position: Tuple[int, int], 
                               associations: Dict[str, str], 
                               thresholds: Dict[str, ThresholdConfig]) -> Dict[str, float]:
        """Convert substance concentrations to gene network inputs using associations and thresholds"""
        inputs = {}
        
        for substance_name, gene_input in associations.items():
            if gene_input == "NA":
                continue
                
            # Get substance concentration
            if substance_name in self.substances:
                concentration = self.substances[substance_name].get_concentration_at(position)
                
                # Apply threshold if available
                if gene_input in thresholds:
                    threshold_config = thresholds[gene_input]
                    # Convert concentration to boolean input based on threshold
                    threshold_value = float(threshold_config.threshold)
                    inputs[gene_input] = concentration > threshold_value
                else:
                    # This should never happen - all gene inputs must have thresholds
                    raise KeyError(f"Gene input '{gene_input}' has no threshold defined in config. All gene inputs must have thresholds.")
        
        return inputs

class MultiSubstanceSimulator:
    """Simulates multiple substances with their interactions"""
    
    def __init__(self, config: MicroCConfig, mesh_manager: MeshManager):
        self.config = config
        self.mesh_manager = mesh_manager
        
        # Initialize substance states
        self.state = MultiSubstanceState()
        self._initialize_substances()
        
        # FiPy variables if available
        self.fipy_variables = {}
        self.fipy_mesh = None
        if FIPY_AVAILABLE:
            self._setup_fipy()
    
    def _initialize_substances(self):
        """Initialize all substances from configuration"""
        nx, ny = self.config.domain.nx, self.config.domain.ny
        
        for name, substance_config in self.config.substances.items():
            # Initialize concentration field
            initial_conc = substance_config.initial_value.value
            concentrations = np.full((ny, nx), initial_conc, dtype=float)
            
            # Create substance state
            self.state.substances[name] = SubstanceState(
                name=name,
                concentrations=concentrations,
                config=substance_config
            )
            
            print(f"✅ Initialized {name}: {initial_conc} {substance_config.initial_value.unit}")
    
    def _setup_fipy(self):
        """Setup FiPy variables for diffusion simulation"""
        if not FIPY_AVAILABLE:
            return
        
        # Create FiPy mesh
        dx = self.config.domain.size_x.meters / self.config.domain.nx
        dy = self.config.domain.size_y.meters / self.config.domain.ny
        
        self.fipy_mesh = Grid2D(dx=dx, dy=dy, 
                               nx=self.config.domain.nx, 
                               ny=self.config.domain.ny)
        
        # Create FiPy variables for each substance
        for name, substance_state in self.state.substances.items():
            initial_value = substance_state.config.initial_value.value
            boundary_value = substance_state.config.boundary_value.value
            
            # Create variable
            var = CellVariable(name=name, mesh=self.fipy_mesh, value=initial_value)
            
            # Set boundary conditions
            if substance_state.config.boundary_type == "fixed":
                # Original fixed boundary behavior - constant value on all boundaries
                var.constrain(boundary_value, self.fipy_mesh.facesTop | 
                             self.fipy_mesh.facesBottom | self.fipy_mesh.facesLeft | 
                             self.fipy_mesh.facesRight)
            elif substance_state.config.boundary_type == "gradient":
                # New gradient boundary type - custom gradient setup
                self._apply_custom_gradient_boundary_conditions(var, name)
            elif substance_state.config.boundary_type == "linear_gradient":
                # Default linear gradient: 0 left, 1 right, gradients top/bottom
                self._apply_gradient_boundary_conditions(var, name, boundary_value)
            
            self.fipy_variables[name] = var
    
    def _apply_gradient_boundary_conditions(self, var, substance_name, default_boundary_value):
        """Apply gradient boundary conditions: 0 on left, 1 on right, gradients on top/bottom"""
        
        # Left side: 0
        var.constrain(0.0, self.fipy_mesh.facesLeft)
        
        # Right side: 1  
        var.constrain(1.0, self.fipy_mesh.facesRight)
        
        # Top and bottom: create linear gradients based on x-position
        domain_width = self.config.domain.size_x.meters
        face_centers_x = self.fipy_mesh.faceCenters[0]
        face_centers_y = self.fipy_mesh.faceCenters[1]
        
        # Apply gradients to top and bottom faces
        for face_id in range(self.fipy_mesh.numberOfFaces):
            face_center_x = face_centers_x[face_id]
            face_center_y = face_centers_y[face_id]
            
            # Check if this is a top or bottom face (not left or right)
            is_top_face = self.fipy_mesh.facesTop[face_id]
            is_bottom_face = self.fipy_mesh.facesBottom[face_id]
            
            if is_top_face or is_bottom_face:
                # Create linear gradient based on x position (0 at left, 1 at right)
                normalized_x = face_center_x / domain_width
                gradient_value = max(0.0, min(1.0, normalized_x))  # Clamp to [0,1]
                
                # Create a mask for this specific face
                face_mask = ((self.fipy_mesh.exteriorFaces == 1) & 
                           (self.fipy_mesh.faceCenters[0] == face_center_x) & 
                           (self.fipy_mesh.faceCenters[1] == face_center_y))
                if face_mask.any():
                    var.constrain(gradient_value, where=face_mask)
    
    def _apply_custom_gradient_boundary_conditions(self, var, substance_name):
        """Apply fully custom gradient boundary conditions"""
        
        try:
            # Apply custom boundary conditions face by face
            face_centers_x = self.fipy_mesh.faceCenters[0]
            face_centers_y = self.fipy_mesh.faceCenters[1]
            
            for face_id in range(self.fipy_mesh.numberOfFaces):
                if self.fipy_mesh.exteriorFaces[face_id]:
                    face_center_x = float(face_centers_x[face_id])
                    face_center_y = float(face_centers_y[face_id])
                    face_center = (face_center_x, face_center_y)
                    
                    try:
                        boundary_value = self.hook_manager.call_hook(
                            "custom_calculate_boundary_conditions",
                            substance_name=substance_name,
                            position=face_center,
                            time=0.0  # For steady state, time doesn't matter
                        )
                        
                        # Apply boundary condition to this specific face
                        face_mask = ((self.fipy_mesh.exteriorFaces == 1) & 
                                   (self.fipy_mesh.faceCenters[0] == face_center_x) & 
                                   (self.fipy_mesh.faceCenters[1] == face_center_y))
                        if face_mask.any():
                            var.constrain(boundary_value, where=face_mask)
                            
                    except NotImplementedError:
                        # If no custom function, fall back to default gradient for this face
                        self._apply_default_gradient_for_face(var, face_center_x, face_center_y)
                        
        except Exception as e:
            print(f"Warning: Custom boundary conditions failed for {substance_name}: {e}")
            # Fall back to simple gradient
            self._apply_gradient_boundary_conditions(var, substance_name, 0.5)
    
    def _apply_default_gradient_for_face(self, var, face_center_x, face_center_y):
        """Apply default gradient boundary condition for a single face"""
        domain_width = self.config.domain.size_x.meters
        
        # Create linear gradient based on x-position (0 at left, 1 at right)
        normalized_x = face_center_x / domain_width
        gradient_value = max(0.0, min(1.0, normalized_x))  # Clamp to [0,1]
        
        # Apply constraint to this specific face
        face_mask = ((self.fipy_mesh.exteriorFaces == 1) & 
                   (self.fipy_mesh.faceCenters[0] == face_center_x) & 
                   (self.fipy_mesh.faceCenters[1] == face_center_y))
        if face_mask.any():
            var.constrain(gradient_value, where=face_mask)

    def update(self, substance_reactions: Dict[Tuple[float, float], Dict[str, float]]):
        """Update using FiPy diffusion solver - steady state solution"""

        for name, substance_state in self.state.substances.items():
            if name not in self.fipy_variables:
                continue

            var = self.fipy_variables[name]
            config = substance_state.config

            # Create source/sink terms from cell reactions
            source_field = self._create_source_field_from_reactions(name, substance_reactions)

            # DEBUG: Show source field before and after negation for lactate
            # if name == 'Lactate':
            #     non_zero_indices = np.where(source_field != 0)[0]
            #     if len(non_zero_indices) > 0:
            #         print(f"🔍 LACTATE SOURCE FIELD BEFORE NEGATION:")
            #         for idx in non_zero_indices[:5]:  # Show first 5 non-zero values
            #             print(f"   idx {idx}: {source_field[idx]:.2e} mM/s")

            # CRITICAL FIX: Negate source field for correct FiPy behavior
            # In our convention: negative = consumption, positive = production
            # In FiPy ImplicitSourceTerm: positive coeff = consumption, negative coeff = production
            # So we need to negate our values: consumption (-) becomes (+) for FiPy
            source_field = -source_field

            # DEBUG: Show source field after negation for lactate
            # if name == 'Lactate':
            #     non_zero_indices = np.where(source_field != 0)[0]
            #     if len(non_zero_indices) > 0:
            #         print(f"🔍 LACTATE SOURCE FIELD AFTER NEGATION (to FiPy):")
            #         for idx in non_zero_indices[:5]:  # Show first 5 non-zero values
            #             print(f"   idx {idx}: {source_field[idx]:.2e} mM/s")

            # Create FiPy source variable
            source_var = CellVariable(mesh=self.fipy_mesh, value=source_field)

            # Steady state diffusion equation (no TransientTerm)
            # 0 = ∇·(D∇C) - R*C where R > 0 for consumption
            # Fixed: Use minus sign for ImplicitSourceTerm to get consumption behavior
            equation = (DiffusionTerm(coeff=config.diffusion_coeff) -
                       ImplicitSourceTerm(coeff=source_var))

            # Solve for steady state
            # Use iterative solver with convergence criteria
            max_iterations = int(getattr(self.config.diffusion, 'max_iterations', 1000))
            tolerance = float(getattr(self.config.diffusion, 'tolerance', 1e-6))

            # Solve iteratively until convergence
            residual = 1.0
            iteration = 0

            while residual > tolerance and iteration < max_iterations:
                old_values = var.value.copy()
                equation.solve(var=var)

                # Calculate residual (relative change)
                residual = np.max(np.abs(var.value - old_values)) / (np.max(np.abs(var.value)) + 1e-12)
                iteration += 1

            if iteration >= max_iterations:
                print(f"Warning: {name} diffusion did not converge after {max_iterations} iterations (residual: {residual:.2e})")
            # else:
            #     print(f"✅ {name} converged in {iteration} iterations (residual: {residual:.2e})")

            # Update our state
            substance_state.concentrations = np.array(var.value).reshape(
                (self.config.domain.ny, self.config.domain.nx), order='F'
            )

            # Ensure non-negative concentrations
            substance_state.concentrations = np.maximum(substance_state.concentrations, 0.0)
    
    def _create_source_field_from_reactions(self, substance_name: str,
                                          substance_reactions: Dict[Tuple[float, float], Dict[str, float]]) -> np.ndarray:
        """Create source/sink field from cell reactions (no config access!)"""

        nx, ny = self.config.domain.nx, self.config.domain.ny
        source_field = np.zeros(nx * ny)

        # Calculate mesh cell volume (grid spacing × grid spacing × configurable height)
        dx = self.config.domain.size_x.meters / self.config.domain.nx
        dy = self.config.domain.size_y.meters / self.config.domain.ny
        cell_height = self.config.domain.cell_height.meters  # Get configurable cell height
        mesh_cell_volume = dx * dy  # m³ (area × height)

        # Optional debug output for cell height effect (uncomment for debugging)
        # print(f"🔍 CELL HEIGHT DEBUG:")
        # print(f"   Cell height: {self.config.domain.cell_height}")
        # print(f"   Mesh cell volume: {mesh_cell_volume:.2e} m³")
        # print(f"   Expected volume (μm³): {mesh_cell_volume * 1e18:.1f}")
        # print(f"   Grid spacing: {dx*1e6:.1f} × {dy*1e6:.1f} μm")

        for (x_pos, y_pos), reactions in substance_reactions.items():
            # Convert to grid coordinates
            x, y = int(x_pos), int(y_pos)

            if 0 <= x < nx and 0 <= y < ny:
                # Convert to FiPy index (Fortran/column-major order to match reshape)
                fipy_idx = x * ny + y

                # Get reaction rate for this substance (from custom metabolism function)
                # Some substances may not have reactions defined (e.g., EGF, TGFA)
                if substance_name not in reactions:
                    continue  # Skip substances with no reactions
                reaction_rate = reactions[substance_name]  # mol/s/cell

                # Convert mol/s/cell to mol/(m³⋅s) by dividing by mesh cell volume
                # Apply 2D adjustment coefficient (1/thickness) to account for 2D simulation of 3D system
                volumetric_rate = reaction_rate / mesh_cell_volume * self.config.diffusion.twodimensional_adjustment_coefficient

                # Convert to mM/s for FiPy (1 mol/m³ = 1000 mM)
                final_rate = volumetric_rate * 1000.0
                source_field[fipy_idx] = final_rate

                # DEBUG: Print reaction terms being passed to FiPy for lactate
                # if substance_name == 'Lactate' and reaction_rate != 0.0:
                #     print(f"🔍 FIPY SOURCE TERM {substance_name} at ({x},{y}):")
                #     print(f"   reaction_rate: {reaction_rate:.2e} mol/s/cell")
                #     print(f"   mesh_cell_volume: {mesh_cell_volume:.2e} m³")
                #     print(f"   2D_adjustment_coeff: {self.config.diffusion.twodimensional_adjustment_coefficient}")
                #     print(f"   volumetric_rate: {volumetric_rate:.2e} mol/(m³⋅s)")
                #     print(f"   final_rate (to FiPy): {final_rate:.2e} mM/s")
                #     print(f"   fipy_idx: {fipy_idx}")

                # Optional debug output for cell height effect on reaction rates (uncomment for debugging)
                # if len([r for r in source_field if r != 0]) <= 3:
                #     print(f"🔍 REACTION RATE DEBUG {substance_name} at ({x},{y}):")
                #     print(f"   reaction_rate: {reaction_rate:.2e} mol/s/cell")
                #     print(f"   mesh_cell_volume: {mesh_cell_volume:.2e} m³")
                #     print(f"   volumetric_rate: {volumetric_rate:.2e} mol/(m³⋅s)")
                #     print(f"   final_rate: {final_rate:.2e} mM/s")
                #     print(f"   Cell height effect: larger volume → lower volumetric rate")

        return source_field

    def _create_source_field(self, substance_name: str, cell_positions: List[Tuple[int, int]],
                           cell_states: Dict[str, Any]) -> np.ndarray:
        """DEPRECATED: Create source/sink field for FiPy simulation using config values"""
        raise NotImplementedError("This method is deprecated. Use _create_source_field_from_reactions instead.")
    
    def get_substance_concentrations(self) -> Dict[str, Dict[Tuple[int, int], float]]:
        """Get all substance concentrations for cell updates"""
        concentrations = {}
        
        for name, substance_state in self.state.substances.items():
            substance_concentrations = {}
            ny, nx = substance_state.concentrations.shape
            
            for y in range(ny):
                for x in range(nx):
                    substance_concentrations[(x, y)] = substance_state.concentrations[y, x]
            
            concentrations[name.lower()] = substance_concentrations
        
        return concentrations
    
    def get_gene_network_inputs_for_position(self, position: Tuple[int, int]) -> Dict[str, float]:
        """Get gene network inputs for a specific position"""
        return self.state.get_gene_network_inputs(
            position, 
            self.config.associations, 
            self.config.thresholds
        )
    
    def get_summary_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get summary statistics for all substances"""
        stats = {}
        
        for name, substance_state in self.state.substances.items():
            conc = substance_state.concentrations
            stats[name] = {
                'min': float(np.min(conc)),
                'max': float(np.max(conc)),
                'mean': float(np.mean(conc)),
                'std': float(np.std(conc))
            }
        
        return stats

    def get_substance_concentrations(self) -> Dict[str, Dict[Tuple[int, int], float]]:
        """Get substance concentrations at all grid positions"""
        concentrations = {}

        for name, substance_state in self.state.substances.items():
            conc_field = {}
            ny, nx = substance_state.concentrations.shape

            for i in range(ny):
                for j in range(nx):
                    conc_field[(i, j)] = float(substance_state.concentrations[i, j])

            concentrations[name] = conc_field

        return concentrations
