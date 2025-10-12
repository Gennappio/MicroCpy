from dataclasses import dataclass
from typing import Tuple, Union
import numpy as np
from fipy import Grid2D, Grid3D

from config.config import DomainConfig
from core.units import Length, UnitValidator

class DomainError(Exception):
    """Raised when domain configuration is invalid"""
    pass

class MeshManager:
    """Manages FiPy mesh with bulletproof unit handling"""
    
    def __init__(self, config: DomainConfig):
        self.config = config
        self._validate_config()
        # Use explicit solver terminology for FiPy mesh
        self.solver_mesh = self._create_solver_mesh()
        self._validate_solver_mesh()

    def _validate_config(self):
        """Validate domain configuration - flexible grid spacing"""
        # Check grid spacing is reasonable (1-50 um)
        actual_spacing_um = self.config.size_x.micrometers / self.config.nx

        if actual_spacing_um < 1.0 or actual_spacing_um > 100.0:
            raise DomainError(
                f"GRID SPACING ERROR!\n"
                f"Domain: {self.config.size_x} / {self.config.nx} = {actual_spacing_um:.1f} um per cell\n"
                f"Reasonable range: 1-100 um per cell\n"
                f"Current spacing is {'too fine' if actual_spacing_um < 1.0 else 'too coarse'}"
            )

        # Check that grid spacing is consistent
        spacing_x = self.config.size_x.micrometers / self.config.nx
        spacing_y = self.config.size_y.micrometers / self.config.ny

        if abs(spacing_x - spacing_y) > 0.1:
            raise DomainError(
                f"GRID MUST HAVE CONSISTENT SPACING!\n"
                f"X spacing: {spacing_x:.1f} um\n"
                f"Y spacing: {spacing_y:.1f} um"
            )

        # For 3D, also check Z spacing
        if self.config.dimensions == 3:
            if self.config.size_z is None or self.config.nz is None:
                raise DomainError("3D simulation requires size_z and nz parameters")

            spacing_z = self.config.size_z.micrometers / self.config.nz
            if abs(spacing_x - spacing_z) > 0.1:
                raise DomainError(
                    f"GRID MUST HAVE CONSISTENT SPACING!\n"
                    f"X spacing: {spacing_x:.1f} um\n"
                    f"Z spacing: {spacing_z:.1f} um"
                )
    
    def _create_solver_mesh(self) -> Union[Grid2D, Grid3D]:
        """Create FiPy solver mesh with correct units"""
        # Calculate grid spacing in meters (FiPy's base unit)
        dx = self.config.size_x.meters / self.config.nx
        dy = self.config.size_y.meters / self.config.ny

        if self.config.dimensions == 3:
            dz = self.config.size_z.meters / self.config.nz
            print(f"Creating 3D mesh:")
            print(f"  Domain: {self.config.size_x} x {self.config.size_y} x {self.config.size_z}")
            print(f"  Grid: {self.config.nx} x {self.config.ny} x {self.config.nz}")
            print(f"  Spacing: {dx*1e6:.1f} x {dy*1e6:.1f} x {dz*1e6:.1f} um")

            solver_mesh = Grid3D(dx=dx, dy=dy, dz=dz, nx=self.config.nx, ny=self.config.ny, nz=self.config.nz)
            print(f"  Initial domain bounds: 0 to {self.config.size_x.micrometers:.0f} um")
        else:
            print(f"Creating 2D mesh:")
            print(f"  Domain: {self.config.size_x} x {self.config.size_y}")
            print(f"  Grid: {self.config.nx} x {self.config.ny}")
            print(f"  Spacing: {dx*1e6:.1f} x {dy*1e6:.1f} um")

            solver_mesh = Grid2D(dx=dx, dy=dy, nx=self.config.nx, ny=self.config.ny)
            print(f"  Initial domain bounds: 0 to {self.config.size_x.micrometers:.0f} um")

        return solver_mesh

    # Backward-compatible alias for solver mesh
    @property
    def mesh(self):
        return getattr(self, 'solver_mesh', None)

    @mesh.setter
    def mesh(self, value):
        self.solver_mesh = value

    def center_solver_mesh_at_origin(self):
        """
        Center the solver mesh at origin after FiPy variables are created.
        This should be called after all FiPy setup is complete.
        """
        if self.config.dimensions == 3:
            offset_x = -self.config.size_x.meters / 2
            offset_y = -self.config.size_y.meters / 2
            offset_z = -self.config.size_z.meters / 2
            self.solver_mesh = self.solver_mesh + ((offset_x, offset_y, offset_z))
            print(f"[MESH] Centered 3D solver domain: {offset_x*1e6:.0f} to {-offset_x*1e6:.0f} um")
        else:
            offset_x = -self.config.size_x.meters / 2
            offset_y = -self.config.size_y.meters / 2
            self.solver_mesh = self.solver_mesh + ((offset_x, offset_y))
            print(f"[MESH] Centered 2D solver domain: {offset_x*1e6:.0f} to {-offset_x*1e6:.0f} um")

    # Backward-compatible name
    def center_mesh_at_origin(self):
        self.center_solver_mesh_at_origin()

    def _validate_solver_mesh(self):
        """Ensure solver mesh properties match configuration"""
        # Check mesh spacing matches config
        expected_dx = self.config.size_x.meters / self.config.nx
        actual_dx = float(self.solver_mesh.dx)

        if abs(actual_dx - expected_dx) > 1e-9:
            raise DomainError(f"Mesh dx mismatch: expected {expected_dx:.2e}, got {actual_dx:.2e}")

        # Check grid size
        if self.config.dimensions == 3:
            expected_shape = (self.config.nx, self.config.ny, self.config.nz)
            if self.solver_mesh.shape != expected_shape:
                raise DomainError(f"Mesh shape mismatch: expected {expected_shape}, got {self.solver_mesh.shape}")
        else:
            expected_shape = (self.config.nx, self.config.ny)
            if self.solver_mesh.shape != expected_shape:
                raise DomainError(f"Mesh shape mismatch: expected {expected_shape}, got {self.solver_mesh.shape}")

        print(f"[OK] Mesh validation passed:")
        print(f"  Shape: {self.solver_mesh.shape}")
        if self.config.dimensions == 3:
            print(f"  Spacing: {self.solver_mesh.dx*1e6:.1f} x {self.solver_mesh.dy*1e6:.1f} x {self.solver_mesh.dz*1e6:.1f} um")
        else:
            print(f"  Spacing: {self.solver_mesh.dx*1e6:.1f} x {self.solver_mesh.dy*1e6:.1f} um")
        print(f"  Total cells: {self.solver_mesh.numberOfCells}")

    # Backward-compatible name
    def _validate_mesh(self):
        self._validate_solver_mesh()

    @property
    def cell_volume_m3(self) -> float:
        """Cell volume in m³ - handles both 2D and 3D"""
        if self.config.dimensions == 3:
            # For 3D, use FiPy's cellVolumes directly
            volume_m3 = float(self.solver_mesh.cellVolumes[0])
        else:
            # For 2D, area from FiPy cellVolumes (m²) × configurable height
            area_m2 = float(self.solver_mesh.cellVolumes[0])
            height_m = self.config.cell_height.meters  # Configurable cell height
            volume_m3 = area_m2 * height_m

        # Validate against expected volume (based on config)
        expected_volume_m3 = self.config.cell_volume_um3 * 1e-18  # Convert um³ to m³
        if abs(volume_m3 - expected_volume_m3) > 1e-18:
            raise DomainError(f"Volume calculation error: got {volume_m3:.2e} m³, expected {expected_volume_m3:.2e} m³")

        return volume_m3

    @property
    def cell_volume_um3(self) -> float:
        """Cell volume in um³ for easier reading"""
        return self.cell_volume_m3 * 1e18

    def get_metadata(self) -> dict:
        """Return mesh metadata - single source of truth"""
        metadata = {
            'dimensions': self.config.dimensions,
            'nx': self.config.nx,
            'ny': self.config.ny,
            'dx_um': float(self.solver_mesh.dx * 1e6),
            'dy_um': float(self.solver_mesh.dy * 1e6),
            'domain_x_um': self.config.size_x.micrometers,
            'domain_y_um': self.config.size_y.micrometers,
            'cell_volume_um3': self.cell_volume_um3,
            'total_cells': self.solver_mesh.numberOfCells
        }

        # Add 3D-specific metadata if applicable
        if self.config.dimensions == 3:
            metadata.update({
                'nz': self.config.nz,
                'dz_um': float(self.solver_mesh.dz * 1e6),
                'domain_z_um': self.config.size_z.micrometers,
            })

        return metadata

    def validate_against_expected(self, expected_spacing_um: float = None,
                                expected_volume_um3: float = None):
        """Validate mesh against expected values (uses config if not specified)"""
        metadata = self.get_metadata()

        # Use config values if not specified
        if expected_spacing_um is None:
            expected_spacing_um = self.config.size_x.micrometers / self.config.nx
        if expected_volume_um3 is None:
            expected_volume_um3 = self.config.cell_volume_um3

        # Check spacing
        if abs(metadata['dx_um'] - expected_spacing_um) > 0.1:
            raise DomainError(f"Spacing validation failed: {metadata['dx_um']:.1f} um vs expected {expected_spacing_um} um")

        # Check volume
        if abs(metadata['cell_volume_um3'] - expected_volume_um3) > 100:
            raise DomainError(f"Volume validation failed: {metadata['cell_volume_um3']:.0f} um³ vs expected {expected_volume_um3} um³")

        print(f"[OK] Mesh validation successful:")
        print(f"  Grid spacing: {metadata['dx_um']:.1f} um [OK]")
        print(f"  Cell volume: {metadata['cell_volume_um3']:.0f} um³ [OK]")
        print(f"  Domain size: {metadata['domain_x_um']:.0f} x {metadata['domain_y_um']:.0f} um [OK]")
