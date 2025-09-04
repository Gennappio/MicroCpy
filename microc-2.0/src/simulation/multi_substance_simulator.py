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
    from fipy import Grid2D, Grid3D, CellVariable, DiffusionTerm, ImplicitSourceTerm
    from fipy.solvers.scipy import LinearGMRESSolver as Solver
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
    concentrations: np.ndarray  # 2D or 3D array of concentrations
    config: SubstanceConfig
    
    def get_concentration_at(self, position: Tuple[int, int]) -> float:
        """Get concentration at specific grid position"""
        x, y = position

        # Handle both 2D and 3D concentration arrays
        if len(self.concentrations.shape) == 3:
            # 3D case: take middle slice in Z direction
            nz = self.concentrations.shape[0]
            middle_z = nz // 2
            if 0 <= x < self.concentrations.shape[2] and 0 <= y < self.concentrations.shape[1]:
                return float(self.concentrations[middle_z, y, x])
        else:
            # 2D case: use as-is
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
            
            print(f"[OK] Initialized {name}: {initial_conc} {substance_config.initial_value.unit}")
    
    def _setup_fipy(self):
        """Setup FiPy variables for diffusion simulation"""
        if not FIPY_AVAILABLE:
            return

        # Use the centered mesh from MeshManager instead of creating our own
        # This ensures consistent coordinate system across all components
        self.fipy_mesh = self.mesh_manager.mesh
        
        # Create FiPy variables for each substance
        for name, substance_state in self.state.substances.items():
            initial_value = substance_state.config.initial_value.value
            boundary_value = substance_state.config.boundary_value.value
            
            # Create variable
            var = CellVariable(name=name, mesh=self.fipy_mesh, value=initial_value)
            
            # Set boundary conditions
            if substance_state.config.boundary_type == "fixed":
                # Original fixed boundary behavior - constant value on all boundaries
                if self.config.domain.dimensions == 3:
                    var.constrain(boundary_value,
                                 self.fipy_mesh.facesTop | self.fipy_mesh.facesBottom |
                                 self.fipy_mesh.facesLeft | self.fipy_mesh.facesRight |
                                 self.fipy_mesh.facesFront | self.fipy_mesh.facesBack)
                else:
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

        # Center the mesh at origin after all FiPy variables and boundary conditions are set
        # This ensures proper coordinate system alignment
        self.mesh_manager.center_mesh_at_origin()
    
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

        # DEBUG: Show which substances are being processed
        # substance_names = list(self.state.substances.keys())
        # print(f"[DIFF] DIFFUSION UPDATE: Processing {len(substance_names)} substances: {substance_names}")

        for name, substance_state in self.state.substances.items():
            if name not in self.fipy_variables:
                continue

            var = self.fipy_variables[name]
            config = substance_state.config

            # CRITICAL FIX: Create completely fresh variable for each solve
            # This prevents any accumulated numerical errors or state corruption
            initial_value = substance_state.config.initial_value.value
            boundary_value = substance_state.config.boundary_value.value

            # Create brand new variable (don't reuse the old one)
            var = CellVariable(name=f"{name}_fresh", mesh=self.fipy_mesh, value=initial_value)

            # Apply boundary conditions to fresh variable
            if substance_state.config.boundary_type == "fixed":
                var.constrain(boundary_value, self.fipy_mesh.facesTop |
                             self.fipy_mesh.facesBottom | self.fipy_mesh.facesLeft |
                             self.fipy_mesh.facesRight)

            # DEBUG: Confirm fresh variable
            # if name == 'Lactate':
            #     fresh_min = float(np.min(var.value))
            #     fresh_max = float(np.max(var.value))
            #     print(f"   🆕 FRESH: Created new variable min={fresh_min:.6f}, max={fresh_max:.6f} mM")

            # Create source/sink terms from cell reactions
            source_field = self._create_source_field_from_reactions(name, substance_reactions)

            # DEBUG: Check if source field has any non-zero values
            non_zero_count = np.count_nonzero(source_field)
            if non_zero_count > 0:
                print(f"[DEBUG] {name}: {non_zero_count} non-zero source terms, range: {np.min(source_field):.2e} to {np.max(source_field):.2e} mM/s")
            else:
                print(f"[!] {name}: NO source terms! All zeros.")

            # DEBUG: Enable detailed debugging for Oxygen
            if name == 'Oxygen':
                print(f"\n[DEBUG] DEBUGGING OXYGEN DIFFUSION SOLVER:")
                print(f"   Substance: {name}")
                print(f"   Diffusion coeff: {config.diffusion_coeff:.2e} m²/s")

                # Check source field before negation
                non_zero_indices = np.where(source_field != 0)[0]
                print(f"   Source field: {len(non_zero_indices)} non-zero terms")
                if len(non_zero_indices) > 0:
                    print(f"   Range: {np.min(source_field):.2e} to {np.max(source_field):.2e} mM/s")
                    for i, idx in enumerate(non_zero_indices[:5]):
                        print(f"     idx {idx}: {source_field[idx]:.2e} mM/s")
                else:
                    print(f"   [!] NO SOURCE TERMS FOUND! This explains uniform concentrations!")

                # Check initial concentrations
                initial_min = float(np.min(var.value))
                initial_max = float(np.max(var.value))
                initial_mean = float(np.mean(var.value))
                print(f"   Initial concentrations: min={initial_min:.6f}, max={initial_max:.6f}, mean={initial_mean:.6f} mM")

            # DEBUG: Comprehensive debugging for lactate diffusion issue
            # if name == 'Lactate':
            #     print(f"\n[DEBUG] DEBUGGING LACTATE DIFFUSION SOLVER:")
            #     print(f"   Substance: {name}")
            #     print(f"   Diffusion coeff: {config.diffusion_coeff:.2e} m²/s")
            #
            #     # Check source field before negation
            #     non_zero_indices = np.where(source_field != 0)[0]
            #     print(f"   Source field BEFORE negation: {len(non_zero_indices)} non-zero terms")
            #     if len(non_zero_indices) > 0:
            #         print(f"   Range: {np.min(source_field):.2e} to {np.max(source_field):.2e} mM/s")
            #         for i, idx in enumerate(non_zero_indices[:5]):
            #             print(f"     idx {idx}: {source_field[idx]:.2e} mM/s")
            #     else:
            #         print(f"   [!] NO SOURCE TERMS FOUND! This explains uniform concentrations!")
            #
            #     # Check initial concentrations
            #     initial_min = float(np.min(var.value))
            #     initial_max = float(np.max(var.value))
            #     initial_mean = float(np.mean(var.value))
            #     print(f"   Initial concentrations: min={initial_min:.6f}, max={initial_max:.6f}, mean={initial_mean:.6f} mM")

            # FIXED: Do NOT negate source field - standalone equation handles the sign
            # Our convention: negative = consumption, positive = production
            # Standalone equation: DiffusionTerm(D) == -source_var handles the negation
            # So we keep our values as-is: positive = production, negative = consumption
            # source_field = -source_field  # REMOVED: This was causing double negation

            # DEBUG: Show source field after negation for lactate
            # if name == 'Lactate':
            #     non_zero_indices = np.where(source_field != 0)[0]
            #     print(f"   Source field AFTER negation: {len(non_zero_indices)} non-zero terms")
            #     if len(non_zero_indices) > 0:
            #         print(f"   Range: {np.min(source_field):.2e} to {np.max(source_field):.2e} mM/s")
            #         for i, idx in enumerate(non_zero_indices[:5]):
            #             print(f"     idx {idx}: {source_field[idx]:.2e} mM/s")

            # Create FiPy source variable
            source_var = CellVariable(mesh=self.fipy_mesh, value=source_field)

            # DEBUG: Print source field and key info for direct comparison - DISABLED
            # if name == 'Lactate':
            #     print(f"[DEBUG] Lactate source field (final): min={np.min(source_field):.3e}, max={np.max(source_field):.3e}, sum={np.sum(source_field):.3e}")
            #     nonzero = np.nonzero(source_field)[0]
            #     print(f"[DEBUG] Nonzero indices: {nonzero}")
            #     if len(nonzero) > 0:
            #         print(f"[DEBUG] Values at nonzero indices: {[source_field[i] for i in nonzero]}")
            #     # Print value at center cell
            #     nx, ny = self.config.domain.nx, self.config.domain.ny
            #     center_x, center_y = nx // 2, ny // 2
            #     center_idx = center_x * ny + center_y
            #     print(f"[DEBUG] Value at center cell index {center_idx}: {source_field[center_idx]:.3e}")
            #     print(f"[DEBUG] Boundary value: {boundary_value}")

            # Use the exact same equation as the standalone FiPy script
            # Standalone: DiffusionTerm(D) == -source_var
            equation = DiffusionTerm(coeff=config.diffusion_coeff) == -source_var

            # Solve for steady state using the exact same approach as standalone script
            solver = Solver(iterations=1000, tolerance=1e-6)

            try:
                res = equation.solve(var=var, solver=solver)
                # DEBUG: Show solver results for Oxygen
                if name == 'Oxygen':
                    if res is not None:
                        print(f"   [OK] {name} solver finished. Final residual: {res:.2e}")
                    else:
                        print(f"   [OK] {name} solver finished.")

                    # Check final concentrations
                    final_min = float(np.min(var.value))
                    final_max = float(np.max(var.value))
                    final_mean = float(np.mean(var.value))
                    final_range = final_max - final_min
                    print(f"   Final concentrations: min={final_min:.6f}, max={final_max:.6f}, mean={final_mean:.6f} mM")
                    print(f"   Concentration range: {final_range:.6f} mM ({final_range/final_mean*100:.4f}% variation)")

                    # Compare with expected behavior
                    if final_range < 0.0001:
                        print(f"   🎯 PROBLEM: Nearly uniform concentrations despite source terms!")
                    else:
                        print(f"   ✅ SUCCESS: Concentration gradients detected!")
            except Exception as e:
                print(f"[ERROR] Error during {name} solve: {e}")

            # DEBUG: Show solver results for lactate
            # if name == 'Lactate':
            #     print(f"   Solver converged in {iteration} iterations (residual: {residual:.2e})")
            #
            #     # Check final concentrations
            #     final_min = float(np.min(var.value))
            #     final_max = float(np.max(var.value))
            #     final_mean = float(np.mean(var.value))
            #     final_range = final_max - final_min
            #     print(f"   Final concentrations: min={final_min:.6f}, max={final_max:.6f}, mean={final_mean:.6f} mM")
            #     print(f"   Concentration range: {final_range:.6f} mM ({final_range/final_mean*100:.4f}% variation)")
            #
            #     # Compare with standalone test expectation
            #     if final_range < 0.0001:
            #         print(f"   🎯 MATCHES current MicroC behavior (nearly uniform)")
            #         print(f"   ❌ BUT standalone test shows this should be ~0.2 mM range!")
            #     elif final_range > 0.1:
            #         print(f"   [OK] SIGNIFICANT GRADIENTS like standalone test")
            #     else:
            #         print(f"   [INFO] SMALL GRADIENTS detected")

            # Update our state
            if self.config.domain.dimensions == 3:
                substance_state.concentrations = np.array(var.value).reshape(
                    (self.config.domain.nz, self.config.domain.ny, self.config.domain.nx), order='F'
                )
            else:
                substance_state.concentrations = np.array(var.value).reshape(
                    (self.config.domain.ny, self.config.domain.nx), order='F'
                )

            # Ensure non-negative concentrations
            substance_state.concentrations = np.maximum(substance_state.concentrations, 0.0)
    
    def _create_source_field_from_reactions(self, substance_name: str,
                                          substance_reactions: Dict[Tuple[float, float], Dict[str, float]]) -> np.ndarray:
        """Create source/sink field from cell reactions (no config access!)"""



        if self.config.domain.dimensions == 3:
            nx, ny, nz = self.config.domain.nx, self.config.domain.ny, self.config.domain.nz
            source_field = np.zeros(nx * ny * nz)
        else:
            nx, ny = self.config.domain.nx, self.config.domain.ny
            nz = 1  # For 2D case
            source_field = np.zeros(nx * ny)

        # Calculate mesh cell volume
        dx = self.config.domain.size_x.meters / self.config.domain.nx
        dy = self.config.domain.size_y.meters / self.config.domain.ny

        if self.config.domain.dimensions == 3:
            dz = self.config.domain.size_z.meters / self.config.domain.nz
            mesh_cell_volume = dx * dy * dz  # m³ (true 3D volume)
        else:
            cell_height = self.config.domain.cell_height.meters  # Get configurable cell height
            mesh_cell_volume = dx * dy * cell_height  # m³ (area × height)

        # Optional debug output for cell height effect (uncomment for debugging)
        # print(f"[DEBUG] CELL HEIGHT DEBUG:")
        # print(f"   Cell height: {self.config.domain.cell_height}")
        # print(f"   Mesh cell volume: {mesh_cell_volume:.2e} m³")
        # print(f"   Expected volume (μm³): {mesh_cell_volume * 1e18:.1f}")
        # print(f"   Grid spacing: {dx*1e6:.1f} × {dy*1e6:.1f} μm")

        for position, reactions in substance_reactions.items():
            # Handle both 2D and 3D positions
            if len(position) == 2:
                x_pos, y_pos = position

                # Convert physical coordinates (meters) to grid indices
                # Physical coordinates are in meters, need to convert to grid indices
                dx = self.config.domain.size_x.meters / nx
                dy = self.config.domain.size_y.meters / ny

                x = int(x_pos / dx)
                y = int(y_pos / dy)
                z = 0  # Default for 2D

                if 0 <= x < nx and 0 <= y < ny:
                    # Convert to FiPy index - use correct formula for 3D mesh even with 2D position
                    if self.config.domain.dimensions == 3:
                        # For 3D mesh: x * ny * nz + y * nz + z (z=0 for 2D positions)
                        fipy_idx = x * ny * nz + y * nz + z
                    else:
                        # For 2D mesh: x * ny + y
                        fipy_idx = x * ny + y
                else:
                    continue
            else:
                x_pos, y_pos, z_pos = position

                # Convert physical coordinates (meters) to grid indices
                dx = self.config.domain.size_x.meters / nx
                dy = self.config.domain.size_y.meters / ny
                dz = self.config.domain.size_z.meters / nz

                x = int(x_pos / dx)
                y = int(y_pos / dy)
                z = int(z_pos / dz)

                if 0 <= x < nx and 0 <= y < ny and 0 <= z < nz:
                    # Convert to FiPy index for 3D (Fortran/column-major order)
                    fipy_idx = x * ny * nz + y * nz + z
                else:
                    continue

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

            # DEBUG: Print reaction terms being passed to FiPy for key substances
            if substance_name in ['Lactate', 'Oxygen', 'Glucose'] and reaction_rate != 0.0:
                print(f"[DEBUG] FIPY SOURCE TERM {substance_name} at ({x},{y}):")
                print(f"   reaction_rate: {reaction_rate:.2e} mol/s/cell")
                print(f"   mesh_cell_volume: {mesh_cell_volume:.2e} m³")
                print(f"   2D_adjustment_coeff: {self.config.diffusion.twodimensional_adjustment_coefficient}")
                print(f"   volumetric_rate: {volumetric_rate:.2e} mol/(m³⋅s)")
                print(f"   final_rate (to FiPy): {final_rate:.2e} mM/s")
                print(f"   fipy_idx: {fipy_idx}")


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

            # Handle both 2D and 3D concentration arrays
            if len(substance_state.concentrations.shape) == 3:
                # 3D case: take middle slice in Z direction
                nz = substance_state.concentrations.shape[0]
                middle_z = nz // 2
                conc_slice = substance_state.concentrations[middle_z, :, :]
            else:
                # 2D case: use as-is
                conc_slice = substance_state.concentrations

            ny, nx = conc_slice.shape
            for y in range(ny):
                for x in range(nx):
                    substance_concentrations[(x, y)] = conc_slice[y, x]

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

            # Handle both 2D and 3D concentration arrays
            if len(substance_state.concentrations.shape) == 3:
                # 3D case: take middle slice in Z direction
                nz = substance_state.concentrations.shape[0]
                middle_z = nz // 2
                conc_slice = substance_state.concentrations[middle_z, :, :]
            else:
                # 2D case: use as-is
                conc_slice = substance_state.concentrations

            for i in range(conc_slice.shape[0]):
                for j in range(conc_slice.shape[1]):
                    conc_field[(i, j)] = float(conc_slice[i, j])

            concentrations[name] = conc_field

        return concentrations
