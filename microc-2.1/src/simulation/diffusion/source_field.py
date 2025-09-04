"""
Source field builder – centralize unit/sign/index logic for mapping reactions to mesh.
No solver dependency. Easy to unit test.
"""
from dataclasses import dataclass
import numpy as np
from typing import Dict, Iterable, Tuple

from ..core.domain.geometry import GridSpec


@dataclass(frozen=True)
class SourceFieldBuilder:
    grid: GridSpec
    cell_height_um: float
    twod_coeff: float
    
    def reactions_to_source_field(self, reactions_per_index: Dict[int, Dict[str, float]], substance_name: str) -> np.ndarray:
        """
        Convert mol/s/cell reactions aggregated per grid index into a 1D mM/s source field.
        
        Args:
            reactions_per_index: {fipy_index: {substance: mol_per_sec}}
            substance_name: which substance to extract
        Returns:
            1D array of length grid.total_cells with mM/s values (positive production, negative consumption)
        """
        n = self.grid.total_cells
        field = np.zeros(n, dtype=float)
        # Volume um^3 for each voxel (assume uniform grid)
        voxel_um3 = self.grid.spacing_x * self.grid.spacing_y * self.grid.spacing_z
        # Convert um^3 to liters (1 um^3 = 1e-15 L)
        voxel_L = voxel_um3 * 1e-15
        # Convert mol/s to mM/s: (mol/s) / L * 1e3
        # Apply 2D coefficient and/or cell height if sim is quasi-2D
        scale = 1e3 / voxel_L
        if self.twod_coeff != 1.0:
            scale *= self.twod_coeff
        if self.cell_height_um and self.cell_height_um > 0:
            scale /= (self.cell_height_um * 1e-6)  # um → m, then to volume scaling if needed
        
        for idx, per_sub in reactions_per_index.items():
            rate_mol_s = per_sub.get(substance_name, 0.0)
            if rate_mol_s == 0.0:
                continue
            field[idx] += rate_mol_s * scale
        return field
