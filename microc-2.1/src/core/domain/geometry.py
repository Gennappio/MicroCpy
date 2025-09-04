from dataclasses import dataclass

@dataclass(frozen=True)
class GridSpec:
    shape: tuple[int, int, int]  # nx, ny, nz
    spacing_x: float
    spacing_y: float
    spacing_z: float

    @property
    def total_cells(self) -> int:
        nx, ny, nz = self.shape
        return nx * ny * nz

    def index_of(self, x: int, y: int, z: int = 0) -> int:
        """Column-major index mapping used uniformly across the codebase."""
        nx, ny, nz = self.shape
        return x * ny * max(1, nz) + y * max(1, nz) + z
