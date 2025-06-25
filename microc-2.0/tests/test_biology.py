import pytest
import sys
from pathlib import Path
from typing import Dict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biology.cell import Cell, CellState
from biology.gene_network import BooleanNetwork, NetworkNode
from biology.population import CellPopulation, PopulationState


class TestCellState:
    """Test CellState functionality"""
    
    def test_cell_state_creation(self):
        """Test creating a CellState"""
        state = CellState(
            id="test_cell",
            position=(5, 10),
            phenotype="normal",
            age=12.5,
            division_count=2
        )
        
        assert state.id == "test_cell"
        assert state.position == (5, 10)
        assert state.phenotype == "normal"
        assert state.age == 12.5
        assert state.division_count == 2
        
    def test_cell_state_immutability(self):
        """Test that CellState is immutable"""
        state = CellState(
            id="test_cell",
            position=(5, 10),
            phenotype="normal",
            age=12.5,
            division_count=2
        )
        
        # Create updated state
        new_state = state.with_updates(age=15.0, phenotype="hypoxic")
        
        # Original state unchanged
        assert state.age == 12.5
        assert state.phenotype == "normal"
        
        # New state has updates
        assert new_state.age == 15.0
        assert new_state.phenotype == "hypoxic"
        assert new_state.id == "test_cell"  # Other fields preserved


class TestCell:
    """Test Cell functionality"""
    
    def test_cell_creation(self):
        """Test creating a Cell"""
        cell = Cell(position=(0, 0), phenotype="normal")
        
        assert cell.state.position == (0, 0)
        assert cell.state.phenotype == "normal"
        assert cell.state.age == 0.0
        assert cell.state.division_count == 0
        assert len(cell.state.id) > 0  # UUID generated
        
    def test_cell_with_custom_id(self):
        """Test creating cell with custom ID"""
        cell = Cell(position=(1, 1), cell_id="custom_id")
        assert cell.state.id == "custom_id"
        
    def test_default_phenotype_update(self):
        """Test default phenotype update logic"""
        cell = Cell(position=(0, 0))
        
        # Normal conditions
        env = {'lactate': 5.0, 'oxygen': 21.0}
        phenotype = cell.update_phenotype(env, {})
        assert phenotype == "normal"
        
        # Hypoxic conditions
        env = {'lactate': 5.0, 'oxygen': 3.0}
        phenotype = cell.update_phenotype(env, {})
        assert phenotype == "hypoxic"
        
        # High lactate
        env = {'lactate': 18.0, 'oxygen': 21.0}
        phenotype = cell.update_phenotype(env, {})
        assert phenotype == "acidic_resistant"
        
    def test_default_metabolism_calculation(self):
        """Test default metabolism calculation"""
        cell = Cell(position=(0, 0))
        
        env = {'oxygen': 21.0}
        rates = cell.calculate_metabolism(env)
        
        assert 'lactate' in rates
        assert 'glucose' in rates
        assert rates['lactate'] > 0  # Production
        assert rates['glucose'] < 0  # Consumption
        
        # Test hypoxic conditions increase lactate production
        env_hypoxic = {'oxygen': 3.0}
        rates_hypoxic = cell.calculate_metabolism(env_hypoxic)
        assert rates_hypoxic['lactate'] > rates['lactate']
        
    def test_default_division_logic(self):
        """Test default division logic"""
        cell = Cell(position=(0, 0))
        
        # Young cell shouldn't divide
        assert not cell.should_divide()

        # Age the cell
        cell.age(25.0)  # Above threshold
        assert cell.should_divide()

        # Quiescent cells don't divide
        cell.state = cell.state.with_updates(phenotype="quiescent")
        assert not cell.should_divide()
        
    def test_default_death_logic(self):
        """Test default death logic"""
        cell = Cell(position=(0, 0))
        
        # Normal conditions - no death
        env = {'lactate': 5.0, 'oxygen': 21.0}
        assert not cell.should_die(env)

        # High lactate toxicity
        env_toxic = {'lactate': 25.0, 'oxygen': 21.0}
        assert cell.should_die(env_toxic)

        # Severe hypoxia
        env_hypoxic = {'lactate': 5.0, 'oxygen': 0.5}
        assert cell.should_die(env_hypoxic)

        # Very old cell
        cell.age(250.0)
        assert cell.should_die({'lactate': 5.0, 'oxygen': 21.0})
        
    def test_cell_aging(self):
        """Test cell aging"""
        cell = Cell(position=(0, 0))
        
        initial_age = cell.state.age
        cell.age(5.0)
        assert cell.state.age == initial_age + 5.0
        
    def test_cell_division(self):
        """Test cell division"""
        parent = Cell(position=(5, 5), phenotype="proliferative")
        parent.age(10.0)
        parent.state = parent.state.with_updates(division_count=1)
        
        daughter = parent.divide()
        
        # Daughter cell properties
        assert daughter.state.position == (5, 5)  # Same initial position
        assert daughter.state.phenotype == "proliferative"
        assert daughter.state.age == 0.0  # New cell
        assert daughter.state.division_count == 0
        assert daughter.state.id != parent.state.id  # Different ID
        
        # Parent cell updated
        assert parent.state.division_count == 2
        assert parent.state.age == 0.0  # Reset after division
        
    def test_cell_movement(self):
        """Test cell movement"""
        cell = Cell(position=(0, 0))
        
        cell.move_to((3, 7))
        assert cell.state.position == (3, 7)
        
    def test_cell_state_access(self):
        """Test accessing cell state"""
        cell = Cell(position=(1, 2), phenotype="test")
        
        state = cell.get_state()
        assert isinstance(state, CellState)
        assert state.position == (1, 2)
        assert state.phenotype == "test"


class TestBooleanNetwork:
    """Test BooleanNetwork functionality"""
    
    def test_network_creation_default(self):
        """Test creating default network"""
        network = BooleanNetwork()
        
        assert len(network.nodes) > 0
        assert 'oxygen' in network.input_nodes
        assert 'lactate' in network.input_nodes
        assert 'VEGF' in network.output_nodes
        assert 'apoptosis' in network.output_nodes
        
    def test_network_info(self):
        """Test getting network information"""
        network = BooleanNetwork()
        info = network.get_network_info()
        
        assert 'total_nodes' in info
        assert 'input_nodes' in info
        assert 'output_nodes' in info
        assert 'internal_nodes' in info
        assert 'connections' in info
        
        assert info['total_nodes'] > 0
        assert len(info['input_nodes']) > 0
        assert len(info['output_nodes']) > 0
        
    def test_set_input_states(self):
        """Test setting input states"""
        network = BooleanNetwork()
        
        network.set_input_states({'oxygen': False, 'lactate': True})
        
        assert network.nodes['oxygen'].current_state is False
        assert network.nodes['lactate'].current_state is True
        
    def test_network_step(self):
        """Test network stepping"""
        network = BooleanNetwork()
        
        # Set inputs
        network.set_input_states({'oxygen': False, 'lactate': True})
        
        # Step the network (need 2 steps for signal propagation)
        outputs = network.step(2)

        assert isinstance(outputs, dict)
        assert 'VEGF' in outputs
        assert 'apoptosis' in outputs

        # Low oxygen should activate HIF1 -> VEGF
        assert outputs['VEGF'] is True
        # High lactate should activate p53 -> apoptosis
        assert outputs['apoptosis'] is True
        
    def test_get_all_states(self):
        """Test getting all node states"""
        network = BooleanNetwork()
        
        network.set_input_states({'oxygen': True, 'lactate': False})
        network.step(1)
        
        all_states = network.get_all_states()
        
        assert isinstance(all_states, dict)
        assert 'oxygen' in all_states
        assert 'lactate' in all_states
        assert 'HIF1' in all_states
        assert 'p53' in all_states
        
    def test_network_reset(self):
        """Test network reset"""
        network = BooleanNetwork()
        
        # Set some states
        network.set_input_states({'oxygen': True, 'lactate': True})
        network.step(1)
        
        # Reset
        network.reset()
        
        # All states should be False
        all_states = network.get_all_states()
        for state in all_states.values():
            assert state is False
            
    def test_network_with_nonexistent_file(self):
        """Test network creation with non-existent file falls back to default"""
        fake_file = Path("nonexistent.bnd")
        network = BooleanNetwork(network_file=fake_file)
        
        # Should fall back to default network
        assert len(network.nodes) > 0
        assert 'oxygen' in network.input_nodes


class TestIntegration:
    """Integration tests for biology components"""
    
    def test_cell_with_gene_network(self):
        """Test cell working with gene network"""
        cell = Cell(position=(0, 0))
        network = BooleanNetwork()
        
        # Simulate environment
        env = {'lactate': 18.0, 'oxygen': 3.0}
        
        # Set network inputs based on environment
        network.set_input_states({
            'oxygen': env['oxygen'] > 10.0,  # Boolean conversion
            'lactate': env['lactate'] > 10.0
        })
        
        # Step network
        gene_states = network.step(1)
        
        # Update cell phenotype based on environment and genes
        phenotype = cell.update_phenotype(env, gene_states)
        
        # Calculate metabolism
        metabolism = cell.calculate_metabolism(env)
        
        assert isinstance(phenotype, str)
        assert isinstance(metabolism, dict)
        assert 'lactate' in metabolism
        
    def test_cell_lifecycle(self):
        """Test complete cell lifecycle"""
        cell = Cell(position=(5, 5), phenotype="normal")
        
        # Age the cell
        cell.age(10.0)
        assert cell.state.age == 10.0
        
        # Update phenotype
        env = {'lactate': 5.0, 'oxygen': 21.0}
        phenotype = cell.update_phenotype(env, {})
        assert phenotype == "normal"
        
        # Calculate metabolism
        metabolism = cell.calculate_metabolism(env)
        assert metabolism['lactate'] > 0
        
        # Check division (shouldn't divide yet)
        assert not cell.should_divide()

        # Age more
        cell.age(20.0)  # Total 30 hours
        assert cell.should_divide()
        
        # Divide
        daughter = cell.divide()
        assert daughter.state.age == 0.0
        assert cell.state.division_count == 1
        
        # Check death (shouldn't die in normal conditions)
        assert not cell.should_die(env)


class TestPopulationState:
    """Test PopulationState functionality"""

    def test_population_state_creation(self):
        """Test creating a PopulationState"""
        state = PopulationState()

        assert len(state.cells) == 0
        assert len(state.spatial_grid) == 0
        assert state.total_cells == 0
        assert state.generation_count == 0

    def test_population_state_immutability(self):
        """Test that PopulationState is immutable"""
        state = PopulationState(total_cells=5, generation_count=2)

        # Create updated state
        new_state = state.with_updates(total_cells=10, generation_count=3)

        # Original state unchanged
        assert state.total_cells == 5
        assert state.generation_count == 2

        # New state has updates
        assert new_state.total_cells == 10
        assert new_state.generation_count == 3


class TestCellPopulation:
    """Test CellPopulation functionality"""

    def test_population_creation(self):
        """Test creating a CellPopulation"""
        population = CellPopulation(grid_size=(10, 10))

        assert population.grid_size == (10, 10)
        assert population.state.total_cells == 0
        assert len(population.state.cells) == 0
        assert len(population.state.spatial_grid) == 0

    def test_add_cell(self):
        """Test adding cells to population"""
        population = CellPopulation(grid_size=(10, 10))

        # Add first cell
        success = population.add_cell((5, 5), "normal")
        assert success is True
        assert population.state.total_cells == 1
        assert (5, 5) in population.state.spatial_grid

        # Try to add cell at same position (should fail)
        success = population.add_cell((5, 5), "normal")
        assert success is False
        assert population.state.total_cells == 1

        # Add cell at different position
        success = population.add_cell((3, 7), "hypoxic")
        assert success is True
        assert population.state.total_cells == 2

    def test_add_cell_invalid_position(self):
        """Test adding cell at invalid position"""
        population = CellPopulation(grid_size=(10, 10))

        # Out of bounds positions
        assert population.add_cell((-1, 5), "normal") is False
        assert population.add_cell((10, 5), "normal") is False
        assert population.add_cell((5, -1), "normal") is False
        assert population.add_cell((5, 10), "normal") is False

    def test_cell_division(self):
        """Test cell division"""
        import numpy as np
        np.random.seed(42)  # Set seed for reproducible test

        population = CellPopulation(grid_size=(10, 10))

        # Add a cell
        population.add_cell((5, 5), "normal")
        cell_id = list(population.state.cells.keys())[0]

        # Age the cell so it wants to divide
        cell = population.state.cells[cell_id]
        cell.age(25.0)  # Above division threshold

        # Attempt division multiple times if needed (due to random success rate)
        success = False
        for _ in range(10):  # Try up to 10 times
            success = population.attempt_division(cell_id)
            if success:
                break

        assert success is True
        assert population.state.total_cells == 2
        assert population.state.generation_count == 1

        # Check that daughter cell is in a neighboring position
        positions = [cell.state.position for cell in population.state.cells.values()]
        assert len(positions) == 2
        assert (5, 5) in positions  # Parent position

        # Find daughter position
        daughter_pos = [pos for pos in positions if pos != (5, 5)][0]
        # Should be a neighbor of (5, 5)
        dx = abs(daughter_pos[0] - 5)
        dy = abs(daughter_pos[1] - 5)
        assert dx <= 1 and dy <= 1 and (dx + dy) > 0

    def test_cell_division_no_space(self):
        """Test cell division when no space available"""
        population = CellPopulation(grid_size=(3, 3))

        # Fill all positions around center
        center = (1, 1)
        population.add_cell(center, "normal")

        # Fill all neighbors
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue  # Skip center
                population.add_cell((center[0] + dx, center[1] + dy), "normal")

        # Try to divide center cell (should fail - no space)
        center_cell_id = population.state.spatial_grid[center]
        cell = population.state.cells[center_cell_id]
        cell.age(25.0)  # Make it want to divide

        success = population.attempt_division(center_cell_id)
        assert success is False
        assert population.state.total_cells == 9  # No new cells

    def test_remove_dead_cells(self):
        """Test removing dead cells"""
        population = CellPopulation(grid_size=(10, 10))

        # Add some cells
        population.add_cell((5, 5), "normal")
        population.add_cell((3, 3), "normal")

        # Age one cell to death
        cell_id = list(population.state.cells.keys())[0]
        cell = population.state.cells[cell_id]
        cell.age(250.0)  # Very old - should die

        # Remove dead cells
        dead_ids = population.remove_dead_cells()

        assert len(dead_ids) == 1
        assert dead_ids[0] == cell_id
        assert population.state.total_cells == 1
        assert cell_id not in population.state.cells

    def test_get_substance_reactions(self):
        """Test getting substance reactions"""
        population = CellPopulation(grid_size=(10, 10))

        # Add some cells
        population.add_cell((5, 5), "normal")
        population.add_cell((3, 3), "hypoxic")

        # Get reactions
        reactions = population.get_substance_reactions()

        assert len(reactions) == 2
        assert (5.0, 5.0) in reactions
        assert (3.0, 3.0) in reactions

        # Check reaction format
        for pos, reaction in reactions.items():
            assert isinstance(reaction, dict)
            assert 'lactate' in reaction
            assert 'glucose' in reaction

    def test_population_statistics(self):
        """Test population statistics"""
        population = CellPopulation(grid_size=(10, 10))

        # Empty population
        stats = population.get_population_statistics()
        assert stats['total_cells'] == 0
        assert stats['phenotype_counts'] == {}
        assert stats['average_age'] == 0.0

        # Add some cells
        population.add_cell((5, 5), "normal")
        population.add_cell((3, 3), "hypoxic")
        population.add_cell((7, 7), "normal")

        # Age cells differently
        cells = list(population.state.cells.values())
        cells[0].age(10.0)
        cells[1].age(20.0)
        cells[2].age(30.0)

        stats = population.get_population_statistics()
        assert stats['total_cells'] == 3
        assert stats['phenotype_counts']['normal'] == 2
        assert stats['phenotype_counts']['hypoxic'] == 1
        assert stats['average_age'] == 20.0  # (10 + 20 + 30) / 3
        assert 0 < stats['grid_occupancy'] < 1

    def test_cell_positions(self):
        """Test getting cell positions"""
        population = CellPopulation(grid_size=(10, 10))

        # Add some cells
        population.add_cell((5, 5), "normal")
        population.add_cell((3, 3), "hypoxic")

        positions = population.get_cell_positions()

        assert len(positions) == 2
        assert ((5, 5), "normal") in positions
        assert ((3, 3), "hypoxic") in positions
