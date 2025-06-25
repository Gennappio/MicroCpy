import pytest
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from interfaces.base import (
    CustomizableComponent, ISubstanceSimulator, ICell, ICellPopulation,
    IGeneNetwork, IVisualization, IDataExporter, ITimescaleOrchestrator,
    IPerformanceProfiler
)
from interfaces.hooks import HookRegistry, CustomFunctionLoader, HookManager


class TestCustomizableComponent:
    """Test CustomizableComponent base class"""
    
    def test_customizable_component_creation(self):
        """Test creating a CustomizableComponent"""
        
        class TestComponent(CustomizableComponent):
            def _default_test_method(self, x: int) -> int:
                return x * 2
        
        component = TestComponent()
        assert component.custom_functions is None
        
        # Test calling default method
        result = component.call_custom_or_default("test_method", 5)
        assert result == 10


class TestHookRegistry:
    """Test HookRegistry functionality"""
    
    def test_hook_registry_creation(self):
        """Test creating a HookRegistry"""
        registry = HookRegistry()
        assert len(registry.hooks) > 0  # Should have core hooks
        
    def test_list_hooks(self):
        """Test listing available hooks"""
        registry = HookRegistry()
        hooks = registry.list_hooks()
        
        # Check that core hooks are present
        expected_hooks = [
            "calculate_cell_metabolism",
            "update_cell_phenotype", 
            "check_cell_division",
            "check_cell_death",
            "update_gene_network"
        ]
        
        for hook in expected_hooks:
            assert hook in hooks
            
    def test_get_hook(self):
        """Test getting hook definitions"""
        registry = HookRegistry()
        
        hook = registry.get_hook("calculate_cell_metabolism")
        assert hook is not None
        assert hook.name == "calculate_cell_metabolism"
        assert "local_environment" in hook.parameters
        assert hook.return_type == dict


class TestCustomFunctionLoader:
    """Test CustomFunctionLoader functionality"""
    
    def test_loader_creation_without_file(self):
        """Test creating loader without custom functions file"""
        loader = CustomFunctionLoader()
        assert len(loader.custom_functions) == 0
        assert not loader.has_custom_function("test_function")
        
    def test_loader_creation_with_nonexistent_file(self):
        """Test creating loader with non-existent file"""
        fake_path = Path("nonexistent_file.py")
        loader = CustomFunctionLoader(fake_path)
        assert len(loader.custom_functions) == 0


class TestHookManager:
    """Test HookManager functionality"""
    
    def test_hook_manager_creation(self):
        """Test creating a HookManager"""
        manager = HookManager()
        assert manager.loader is not None
        assert manager.hook_registry is not None
        
    def test_list_available_hooks(self):
        """Test listing available hooks"""
        manager = HookManager()
        hooks = manager.list_available_hooks()
        
        assert isinstance(hooks, dict)
        assert "calculate_cell_metabolism" in hooks
        assert isinstance(hooks["calculate_cell_metabolism"], str)
        
    def test_get_hook_signature(self):
        """Test getting hook signature"""
        manager = HookManager()
        
        signature = manager.get_hook_signature("calculate_cell_metabolism")
        assert signature is not None
        assert "parameters" in signature
        assert "return_type" in signature
        assert "description" in signature
        
        # Test non-existent hook
        signature = manager.get_hook_signature("nonexistent_hook")
        assert signature is None
        
    def test_call_unknown_hook(self):
        """Test calling unknown hook raises error"""
        manager = HookManager()
        
        with pytest.raises(ValueError) as exc_info:
            manager.call_hook("unknown_hook")
        
        assert "Unknown hook" in str(exc_info.value)


class TestInterfaceContracts:
    """Test that interface contracts are properly defined"""
    
    def test_isubstance_simulator_interface(self):
        """Test ISubstanceSimulator interface"""
        
        class MockSubstanceSimulator(ISubstanceSimulator):
            def solve_steady_state(self, cell_reactions: Dict[Tuple[float, float], float]) -> bool:
                return True
                
            def evaluate_at_point(self, position: Tuple[float, float]) -> float:
                return 1.0
                
            def get_field_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
                x = np.array([[0, 1], [0, 1]])
                y = np.array([[0, 0], [1, 1]])
                z = np.array([[1, 1], [1, 1]])
                return x, y, z
        
        simulator = MockSubstanceSimulator()
        assert simulator.solve_steady_state({}) is True
        assert simulator.evaluate_at_point((0.0, 0.0)) == 1.0
        
        x, y, z = simulator.get_field_data()
        assert isinstance(x, np.ndarray)
        assert isinstance(y, np.ndarray)
        assert isinstance(z, np.ndarray)
        
    def test_icell_interface(self):
        """Test ICell interface"""
        
        class MockCell(ICell):
            def update_phenotype(self, local_environment: Dict[str, float], 
                                gene_states: Dict[str, bool]) -> str:
                return "normal"
                
            def calculate_metabolism(self, local_environment: Dict[str, float]) -> Dict[str, float]:
                return {"lactate": 1.0}
                
            def should_divide(self) -> bool:
                return False
                
            def should_die(self, local_environment: Dict[str, float]) -> bool:
                return False
        
        cell = MockCell()
        assert cell.update_phenotype({}, {}) == "normal"
        assert cell.calculate_metabolism({}) == {"lactate": 1.0}
        assert cell.should_divide() is False
        assert cell.should_die({}) is False
        
    def test_icell_population_interface(self):
        """Test ICellPopulation interface"""
        
        class MockCellPopulation(ICellPopulation):
            def add_cell(self, position: Tuple[int, int], phenotype: str = "normal") -> bool:
                return True
                
            def attempt_division(self, parent_id: str) -> bool:
                return False
                
            def remove_dead_cells(self) -> List[str]:
                return []
                
            def get_substance_reactions(self) -> Dict[Tuple[float, float], Dict[str, float]]:
                return {}
        
        population = MockCellPopulation()
        assert population.add_cell((0, 0)) is True
        assert population.attempt_division("cell_1") is False
        assert population.remove_dead_cells() == []
        assert population.get_substance_reactions() == {}
        
    def test_igene_network_interface(self):
        """Test IGeneNetwork interface"""
        
        class MockGeneNetwork(IGeneNetwork):
            def set_input_states(self, inputs: Dict[str, bool]):
                pass
                
            def step(self, num_steps: int = 1) -> Dict[str, bool]:
                return {"gene1": True}
                
            def get_output_states(self) -> Dict[str, bool]:
                return {"gene1": True}
        
        network = MockGeneNetwork()
        network.set_input_states({"input1": True})
        assert network.step() == {"gene1": True}
        assert network.get_output_states() == {"gene1": True}


class TestIntegration:
    """Integration tests for interface system"""
    
    def test_interfaces_work_together(self):
        """Test that interfaces can work together"""
        
        # This test verifies that the interface system supports
        # the modular architecture we're building
        
        class MockSystem:
            def __init__(self):
                self.hook_manager = HookManager()
                
            def process_cell(self, cell_data: dict) -> dict:
                # This would use hooks to customize behavior
                hooks = self.hook_manager.list_available_hooks()
                assert "calculate_cell_metabolism" in hooks
                return {"processed": True}
        
        system = MockSystem()
        result = system.process_cell({"id": "cell_1"})
        assert result["processed"] is True
