import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))

from core.domain import MeshManager, DomainError
from core.units import Length
from config import DomainConfig


class TestMeshManager:
    """Test MeshManager functionality"""
    
    def test_valid_domain_config(self):
        """Test creating MeshManager with valid configuration"""
        config = DomainConfig(
            size_x=Length(800.0, "μm"),
            size_y=Length(800.0, "μm"),
            nx=40,
            ny=40
        )
        
        mesh_manager = MeshManager(config)
        assert mesh_manager.config == config
        assert mesh_manager.mesh is not None
        
    def test_grid_spacing_validation(self):
        """Test that grid spacing validation works"""
        # This should work (800 μm / 40 = 20 μm spacing)
        config_good = DomainConfig(
            size_x=Length(800.0, "μm"),
            size_y=Length(800.0, "μm"),
            nx=40,
            ny=40
        )
        mesh_manager = MeshManager(config_good)
        assert mesh_manager is not None
        
        # This should fail (800 μm / 20 = 40 μm spacing, not 20 μm)
        with pytest.raises(ValueError) as exc_info:
            DomainConfig(
                size_x=Length(800.0, "μm"),
                size_y=Length(800.0, "μm"),
                nx=20,  # Wrong number of cells
                ny=20
            )

        assert "Grid spacing mismatch" in str(exc_info.value)
        
    def test_mesh_properties(self):
        """Test mesh properties are correct"""
        config = DomainConfig(
            size_x=Length(800.0, "μm"),
            size_y=Length(800.0, "μm"),
            nx=40,
            ny=40
        )
        
        mesh_manager = MeshManager(config)
        
        # Check mesh shape
        assert mesh_manager.mesh.shape == (40, 40)
        
        # Check spacing (should be 20 μm = 20e-6 m)
        expected_dx = 800e-6 / 40  # 20e-6 m
        assert abs(float(mesh_manager.mesh.dx) - expected_dx) < 1e-9
        
    def test_cell_volume_calculation(self):
        """Test cell volume calculation"""
        config = DomainConfig(
            size_x=Length(800.0, "μm"),
            size_y=Length(800.0, "μm"),
            nx=40,
            ny=40
        )
        
        mesh_manager = MeshManager(config)
        
        # Check volume in μm³ (should be 20×20×20 = 8000 μm³)
        volume_um3 = mesh_manager.cell_volume_um3
        assert abs(volume_um3 - 8000.0) < 100  # Allow some tolerance
        
        # Check volume in m³
        volume_m3 = mesh_manager.cell_volume_m3
        expected_m3 = 8000e-18  # 8000 μm³ in m³
        assert abs(volume_m3 - expected_m3) < 1e-18
        
    def test_metadata_generation(self):
        """Test metadata generation"""
        config = DomainConfig(
            size_x=Length(800.0, "μm"),
            size_y=Length(800.0, "μm"),
            nx=40,
            ny=40
        )
        
        mesh_manager = MeshManager(config)
        metadata = mesh_manager.get_metadata()
        
        # Check all expected keys are present
        expected_keys = ['nx', 'ny', 'dx_um', 'dy_um', 'domain_x_um', 'domain_y_um', 'cell_volume_um3', 'total_cells']
        for key in expected_keys:
            assert key in metadata
            
        # Check values
        assert metadata['nx'] == 40
        assert metadata['ny'] == 40
        assert abs(metadata['dx_um'] - 20.0) < 0.1
        assert abs(metadata['dy_um'] - 20.0) < 0.1
        assert abs(metadata['domain_x_um'] - 800.0) < 0.1
        assert abs(metadata['domain_y_um'] - 800.0) < 0.1
        assert abs(metadata['cell_volume_um3'] - 8000.0) < 100
        assert metadata['total_cells'] == 1600  # 40×40
        
    def test_validation_against_expected(self):
        """Test validation against expected values"""
        config = DomainConfig(
            size_x=Length(800.0, "μm"),
            size_y=Length(800.0, "μm"),
            nx=40,
            ny=40
        )
        
        mesh_manager = MeshManager(config)
        
        # This should pass
        mesh_manager.validate_against_expected(expected_spacing_um=20.0, expected_volume_um3=8000.0)
        
        # This should fail
        with pytest.raises(DomainError):
            mesh_manager.validate_against_expected(expected_spacing_um=10.0, expected_volume_um3=8000.0)
            
        with pytest.raises(DomainError):
            mesh_manager.validate_against_expected(expected_spacing_um=20.0, expected_volume_um3=4000.0)


class TestIntegration:
    """Integration tests for domain system"""
    
    def test_problematic_configuration_caught(self):
        """Test that the problematic configuration from the original issue is caught"""
        # This was the problematic config: 800 μm domain with 20 cells
        # Should give 40 μm spacing, not the expected 20 μm
        with pytest.raises(ValueError) as exc_info:
            DomainConfig(
                size_x=Length(800.0, "μm"),
                size_y=Length(800.0, "μm"),
                nx=20,  # This is wrong - should be 40
                ny=20
            )

        error_msg = str(exc_info.value)
        assert "Grid spacing mismatch" in error_msg
        assert "40.0 μm" in error_msg
        assert "20.0 μm" in error_msg
        
    def test_correct_configuration_works(self):
        """Test that the correct configuration works"""
        # This should work: 800 μm domain with 40 cells = 20 μm spacing
        config = DomainConfig(
            size_x=Length(800.0, "μm"),
            size_y=Length(800.0, "μm"),
            nx=40,
            ny=40
        )
        
        mesh_manager = MeshManager(config)
        mesh_manager.validate_against_expected()
        
        # Check that we get the expected values
        metadata = mesh_manager.get_metadata()
        assert abs(metadata['dx_um'] - 20.0) < 0.1
        assert abs(metadata['cell_volume_um3'] - 8000.0) < 100
