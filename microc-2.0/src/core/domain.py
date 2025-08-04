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
        self.mesh = self._create_mesh()
        self._validate_mesh()
    
    def _validate_config(self):
        """Validate domain configuration - flexible grid spacing"""
        # Check grid spacing is reasonable (1-50 μm)
        actual_spacing_um = self.config.size_x.micrometers / self.config.nx

        if actual_spacing_um < 1.0 or actual_spacing_um > 50.0:
            raise DomainError(
                f"GRID SPACING ERROR!\n"
                f"Domain: {self.config.size_x} ÷ {self.config.nx} = {actual_spacing_um:.1f} μm per cell\n"
                f"Reasonable range: 1-50 μm per cell\n"
                f"Current spacing is {'too fine' if actual_spacing_um < 1.0 else 'too coarse'}"
            )

        # Check that grid spacing is consistent
        spacing_x = self.config.size_x.micrometers / self.config.nx
        spacing_y = self.config.size_y.micrometers / self.config.ny

        if abs(spacing_x - spacing_y) > 0.1:
            raise DomainError(
                f"GRID MUST HAVE CONSISTENT SPACING!\n"
                f"X spacing: {spacing_x:.1f} μm\n"
                f"Y spacing: {spacing_y:.1f} μm"
            )

        # For 3D, also check Z spacing
        if self.config.dimensions == 3:
            if self.config.size_z is None or self.config.nz is None:
                raise DomainError("3D simulation requires size_z and nz parameters")

            spacing_z = self.config.size_z.micrometers / self.config.nz
            if abs(spacing_x - spacing_z) > 0.1:
                raise DomainError(
                    f"GRID MUST HAVE CONSISTENT SPACING!\n"
                    f"X spacing: {spacing_x:.1f} μm\n"
                    f"Z spacing: {spacing_z:.1f} μm"
                )
    
    def _create_mesh(self) -> Union[Grid2D, Grid3D]:
        """Create FiPy mesh with correct units"""
        # Calculate grid spacing in meters (FiPy's base unit)
        dx = self.config.size_x.meters / self.config.nx
        dy = self.config.size_y.meters / self.config.ny

        if self.config.dimensions == 3:
            dz = self.config.size_z.meters / self.config.nz
            print(f"Creating 3D mesh:")
            print(f"  Domain: {self.config.size_x} × {self.config.size_y} × {self.config.size_z}")
            print(f"  Grid: {self.config.nx} × {self.config.ny} × {self.config.nz}")
            print(f"  Spacing: {dx*1e6:.1f} × {dy*1e6:.1f} × {dz*1e6:.1f} μm")

            mesh = Grid3D(dx=dx, dy=dy, dz=dz, nx=self.config.nx, ny=self.config.ny, nz=self.config.nz)
        else:
            print(f"Creating 2D mesh:")
            print(f"  Domain: {self.config.size_x} × {self.config.size_y}")
            print(f"  Grid: {self.config.nx} × {self.config.ny}")
            print(f"  Spacing: {dx*1e6:.1f} × {dy*1e6:.1f} μm")

            mesh = Grid2D(dx=dx, dy=dy, nx=self.config.nx, ny=self.config.ny)

        return mesh
    
    def _validate_mesh(self):
        """Ensure mesh properties match configuration"""
        # Check mesh spacing matches config
        expected_dx = self.config.size_x.meters / self.config.nx
        actual_dx = float(self.mesh.dx)
        
        if abs(actual_dx - expected_dx) > 1e-9:
            raise DomainError(f"Mesh dx mismatch: expected {expected_dx:.2e}, got {actual_dx:.2e}")
        
        # Check grid size
        if self.config.dimensions == 3:
            expected_shape = (self.config.nx, self.config.ny, self.config.nz)
            if self.mesh.shape != expected_shape:
                raise DomainError(f"Mesh shape mismatch: expected {expected_shape}, got {self.mesh.shape}")
        else:
            expected_shape = (self.config.nx, self.config.ny)
            if self.mesh.shape != expected_shape:
                raise DomainError(f"Mesh shape mismatch: expected {expected_shape}, got {self.mesh.shape}")

        print(f"✅ Mesh validation passed:")
        print(f"  Shape: {self.mesh.shape}")
        if self.config.dimensions == 3:
            print(f"  Spacing: {self.mesh.dx*1e6:.1f} × {self.mesh.dy*1e6:.1f} × {self.mesh.dz*1e6:.1f} μm")
        else:
            print(f"  Spacing: {self.mesh.dx*1e6:.1f} × {self.mesh.dy*1e6:.1f} μm")
        print(f"  Total cells: {self.mesh.numberOfCells}")
    
    @property
    def cell_volume_m3(self) -> float:
        """Cell volume in m³ - handles both 2D and 3D"""
        if self.config.dimensions == 3:
            # For 3D, use FiPy's cellVolumes directly
            volume_m3 = float(self.mesh.cellVolumes[0])
        else:
            # For 2D, area from FiPy cellVolumes (m²) × configurable height
            area_m2 = float(self.mesh.cellVolumes[0])
            height_m = self.config.cell_height.meters  # Configurable cell height
            volume_m3 = area_m2 * height_m

        # Validate against expected volume (based on config)
        expected_volume_m3 = self.config.cell_volume_um3 * 1e-18  # Convert μm³ to m³
        if abs(volume_m3 - expected_volume_m3) > 1e-18:
            raise DomainError(f"Volume calculation error: got {volume_m3:.2e} m³, expected {expected_volume_m3:.2e} m³")

        return volume_m3
    
    @property 
    def cell_volume_um3(self) -> float:
        """Cell volume in μm³ for easier reading"""
        return self.cell_volume_m3 * 1e18
    
    def get_metadata(self) -> dict:
        """Return mesh metadata - single source of truth"""
        metadata = {
            'dimensions': self.config.dimensions,
            'nx': self.config.nx,
            'ny': self.config.ny,
            'dx_um': float(self.mesh.dx * 1e6),
            'dy_um': float(self.mesh.dy * 1e6),
            'domain_x_um': self.config.size_x.micrometers,
            'domain_y_um': self.config.size_y.micrometers,
            'cell_volume_um3': self.cell_volume_um3,
            'total_cells': self.mesh.numberOfCells
        }

        # Add 3D-specific metadata if applicable
        if self.config.dimensions == 3:
            metadata.update({
                'nz': self.config.nz,
                'dz_um': float(self.mesh.dz * 1e6),
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
            raise DomainError(f"Spacing validation failed: {metadata['dx_um']:.1f} μm vs expected {expected_spacing_um} μm")

        # Check volume
        if abs(metadata['cell_volume_um3'] - expected_volume_um3) > 100:
            raise DomainError(f"Volume validation failed: {metadata['cell_volume_um3']:.0f} μm³ vs expected {expected_volume_um3} μm³")
        
        print(f"✅ Mesh validation successful:")
        print(f"  Grid spacing: {metadata['dx_um']:.1f} μm ✓")
        print(f"  Cell volume: {metadata['cell_volume_um3']:.0f} μm³ ✓")
        print(f"  Domain size: {metadata['domain_x_um']:.0f} × {metadata['domain_y_um']:.0f} μm ✓")
