import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.units import Length, Concentration, UnitValidator, UnitError


class TestLength:
    """Test Length class functionality"""
    
    def test_length_creation(self):
        """Test creating Length objects"""
        l1 = Length(800.0, "μm")
        assert l1.value == 800.0
        assert l1.unit == "μm"
        
    def test_length_conversions(self):
        """Test length unit conversions are exact"""
        l1 = Length(800.0, "μm")
        assert abs(l1.meters - 800e-6) < 1e-9
        assert abs(l1.micrometers - 800.0) < 1e-6

        l2 = Length(0.8, "mm")
        assert abs(l2.meters - 0.8e-3) < 1e-9
        assert abs(l2.micrometers - 800.0) < 1e-6

        l3 = Length(0.0008, "m")
        assert abs(l3.meters - 0.0008) < 1e-9
        assert abs(l3.micrometers - 800.0) < 1e-6
        
    def test_length_division(self):
        """Test Length / Length = ratio"""
        l1 = Length(800.0, "μm")
        l2 = Length(400.0, "μm")
        ratio = l1 / l2
        assert abs(ratio - 2.0) < 1e-9

        # Test with different units
        l3 = Length(0.4, "mm")
        ratio2 = l1 / l3
        assert abs(ratio2 - 2.0) < 1e-9
        
    def test_invalid_unit(self):
        """Test invalid units raise errors"""
        with pytest.raises(UnitError):
            Length(100.0, "invalid_unit")
            
    def test_length_repr(self):
        """Test string representation"""
        l1 = Length(800.0, "μm")
        repr_str = repr(l1)
        assert "800.0 μm" in repr_str
        assert "8.00e-04 m" in repr_str


class TestConcentration:
    """Test Concentration class functionality"""
    
    def test_concentration_creation(self):
        """Test creating Concentration objects"""
        c1 = Concentration(5.0, "mM")
        assert c1.value == 5.0
        assert c1.unit == "mM"
        
    def test_concentration_conversions(self):
        """Test concentration unit conversions"""
        c1 = Concentration(5.0, "mM")
        assert c1.millimolar == 5.0
        
        c2 = Concentration(0.005, "M")
        assert c2.millimolar == 5.0
        
        c3 = Concentration(0.005, "mol/L")
        assert c3.millimolar == 5.0


class TestUnitValidator:
    """Test UnitValidator functionality"""
    
    def test_grid_spacing_validation_success(self):
        """Test successful grid spacing validation"""
        domain_size = Length(800.0, "μm")
        num_cells = 40
        expected_spacing = Length(20.0, "μm")
        
        result = UnitValidator.validate_grid_spacing(domain_size, num_cells, expected_spacing)
        assert result is True
        
    def test_grid_spacing_validation_failure(self):
        """Test grid spacing validation catches errors"""
        domain_size = Length(500.0, "μm")  # Wrong domain size
        num_cells = 40
        expected_spacing = Length(20.0, "μm")
        
        with pytest.raises(UnitError) as exc_info:
            UnitValidator.validate_grid_spacing(domain_size, num_cells, expected_spacing)
        
        assert "Grid spacing mismatch" in str(exc_info.value)
        
    def test_volume_calculation_validation_success(self):
        """Test successful volume validation"""
        length = Length(20.0, "μm")
        width = Length(20.0, "μm")
        height = Length(20.0, "μm")
        expected_volume = 8000e-18  # 8000 μm³ in m³
        
        result = UnitValidator.validate_volume_calculation(length, width, height, expected_volume)
        assert result is True
        
    def test_volume_calculation_validation_failure(self):
        """Test volume validation catches errors"""
        length = Length(10.0, "μm")  # Wrong dimensions
        width = Length(10.0, "μm")
        height = Length(10.0, "μm")
        expected_volume = 8000e-18  # 8000 μm³ in m³
        
        with pytest.raises(UnitError) as exc_info:
            UnitValidator.validate_volume_calculation(length, width, height, expected_volume)
        
        assert "Volume mismatch" in str(exc_info.value)


class TestIntegration:
    """Integration tests for unit system"""
    
    def test_microc_domain_configuration(self):
        """Test typical MicroC domain configuration"""
        # Test the configuration that should work
        domain_x = Length(800.0, "μm")
        domain_y = Length(800.0, "μm")
        nx, ny = 40, 40
        
        # Calculate expected spacing
        expected_spacing = Length(20.0, "μm")
        
        # Validate grid spacing
        UnitValidator.validate_grid_spacing(domain_x, nx, expected_spacing)
        UnitValidator.validate_grid_spacing(domain_y, ny, expected_spacing)
        
        # Calculate cell volume
        dx = Length(domain_x.meters / nx, "m")
        dy = Length(domain_y.meters / ny, "m")
        height = Length(20.0, "μm")
        
        expected_volume = 8000e-18  # 8000 μm³ in m³
        UnitValidator.validate_volume_calculation(dx, dy, height, expected_volume)
        
    def test_problematic_configuration_caught(self):
        """Test that our problematic configuration is caught"""
        # This was the problematic config that caused issues
        domain_x = Length(800.0, "μm")  # Config said 800 μm
        nx = 20  # But used 20 cells instead of 40
        expected_spacing = Length(20.0, "μm")  # Expected 20 μm spacing
        
        # This should fail because 800/20 = 40 μm spacing, not 20 μm
        with pytest.raises(UnitError):
            UnitValidator.validate_grid_spacing(domain_x, nx, expected_spacing)
