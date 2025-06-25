from dataclasses import dataclass
from typing import Union, Type
import numpy as np

class UnitError(Exception):
    """Raised when unit operations are invalid"""
    pass

@dataclass(frozen=True)
class Length:
    """Length with automatic unit conversion"""
    value: float
    unit: str = "m"  # Base unit: meters
    
    def __post_init__(self):
        if self.unit not in ["m", "mm", "μm", "um", "micrometer"]:
            raise UnitError(f"Invalid length unit: {self.unit}")
    
    @property
    def meters(self) -> float:
        conversions = {"m": 1.0, "mm": 1e-3, "μm": 1e-6, "um": 1e-6, "micrometer": 1e-6}
        return self.value * conversions[self.unit]
    
    @property 
    def micrometers(self) -> float:
        return self.meters * 1e6
    
    def __truediv__(self, other: 'Length') -> float:
        """Length / Length = dimensionless ratio"""
        return self.meters / other.meters
    
    def __repr__(self) -> str:
        return f"Length({self.value} {self.unit} = {self.meters:.2e} m = {self.micrometers:.1f} μm)"

@dataclass(frozen=True) 
class Concentration:
    value: float
    unit: str = "mM"  # Base unit: millimolar
    
    @property
    def millimolar(self) -> float:
        conversions = {"mM": 1.0, "M": 1000.0, "mol/L": 1000.0}
        return self.value * conversions[self.unit]

class UnitValidator:
    """Validates unit consistency across calculations"""
    
    @staticmethod
    def validate_grid_spacing(domain_size: Length, num_cells: int, expected_spacing: Length) -> bool:
        calculated_spacing = Length(domain_size.meters / num_cells, "m")
        ratio = calculated_spacing.meters / expected_spacing.meters
        if not (0.95 < ratio < 1.05):  # 5% tolerance
            raise UnitError(f"Grid spacing mismatch: calculated {calculated_spacing}, expected {expected_spacing}")
        return True
    
    @staticmethod
    def validate_volume_calculation(length: Length, width: Length, height: Length, expected_volume: float) -> bool:
        calculated = length.meters * width.meters * height.meters
        if not (0.95 * expected_volume < calculated < 1.05 * expected_volume):
            raise UnitError(f"Volume mismatch: calculated {calculated:.2e} m³, expected {expected_volume:.2e} m³")
        return True
