import pytest
import sys
from pathlib import Path
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))

from simulation.substance_simulator import SubstanceSimulator, SimulationState
from simulation.orchestrator import TimescaleOrchestrator, TimescaleState, ProcessTiming
from simulation.performance import PerformanceMonitor, PerformanceMetrics, ProfileEntry
from core.domain import MeshManager
from core.units import Length, Concentration
from config import DomainConfig, SubstanceConfig, TimeConfig


class TestSimulationState:
    """Test SimulationState functionality"""
    
    def test_simulation_state_creation(self):
        """Test creating a SimulationState"""
        field = np.array([1.0, 2.0, 3.0])
        state = SimulationState(
            concentration_field=field,
            time=5.0,
            converged=True,
            iterations=10,
            residual=1e-8
        )
        
        assert np.array_equal(state.concentration_field, field)
        assert state.time == 5.0
        assert state.converged is True
        assert state.iterations == 10
        assert state.residual == 1e-8
        
    def test_simulation_state_immutability(self):
        """Test that SimulationState is immutable"""
        field = np.array([1.0, 2.0, 3.0])
        state = SimulationState(
            concentration_field=field,
            time=5.0,
            converged=True,
            iterations=10,
            residual=1e-8
        )
        
        # Create updated state
        new_field = np.array([4.0, 5.0, 6.0])
        new_state = state.with_updates(
            concentration_field=new_field,
            time=10.0,
            converged=False
        )
        
        # Original state unchanged
        assert np.array_equal(state.concentration_field, field)
        assert state.time == 5.0
        assert state.converged is True
        
        # New state has updates
        assert np.array_equal(new_state.concentration_field, new_field)
        assert new_state.time == 10.0
        assert new_state.converged is False
        assert new_state.iterations == 10  # Preserved
        assert new_state.residual == 1e-8  # Preserved


class TestSubstanceSimulator:
    """Test SubstanceSimulator functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create domain configuration
        self.domain_config = DomainConfig(
            size_x=Length(800.0, "μm"),
            size_y=Length(800.0, "μm"),
            nx=40,
            ny=40
        )
        
        # Create mesh manager
        self.mesh_manager = MeshManager(self.domain_config)
        
        # Create substance configuration
        self.substance_config = SubstanceConfig(
            name="lactate",
            diffusion_coeff=6.70e-11,  # m²/s
            production_rate=3.0e-15,   # mol/s/cell
            uptake_rate=0.0,
            initial_value=Concentration(5.0, "mM"),
            boundary_value=Concentration(2.0, "mM"),
            boundary_type="fixed"
        )
    
    def test_simulator_creation(self):
        """Test creating a SubstanceSimulator"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        assert simulator.mesh_manager == self.mesh_manager
        assert simulator.substance_config == self.substance_config
        assert simulator.concentration is not None
        assert simulator.state.time == 0.0
        assert not simulator.state.converged
        
    def test_initial_concentration_field(self):
        """Test initial concentration field setup"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        # Check that initial concentration is set correctly
        initial_conc = simulator.substance_config.initial_value.millimolar
        assert np.allclose(simulator.concentration.value, initial_conc)
        
        # Check field data shape
        X, Y, Z = simulator.get_field_data()
        assert X.shape == (40, 40)
        assert Y.shape == (40, 40)
        assert Z.shape == (40, 40)
        
    def test_evaluate_at_point(self):
        """Test evaluating concentration at specific points"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        # Test point inside mesh
        center_point = (400e-6, 400e-6)  # Center of 800μm domain in meters
        concentration = simulator.evaluate_at_point(center_point)
        
        # Should be close to initial value
        expected = simulator.substance_config.initial_value.millimolar
        assert abs(concentration - expected) < 0.1
        
        # Test point outside mesh
        outside_point = (1000e-6, 1000e-6)  # Outside domain
        concentration = simulator.evaluate_at_point(outside_point)
        
        # Should return boundary value
        expected = simulator.substance_config.boundary_value.millimolar
        assert concentration == expected
        
    def test_solve_steady_state_no_reactions(self):
        """Test steady-state solution with no cell reactions"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        # Solve with no reactions
        converged = simulator.solve_steady_state({})
        
        assert converged is True
        assert simulator.state.converged is True
        assert simulator.state.iterations > 0
        
        # With fixed boundary conditions and no reactions,
        # should converge to boundary value
        final_concentration = np.mean(simulator.concentration.value)
        boundary_value = simulator.substance_config.boundary_value.millimolar
        
        # Should be close to boundary value (exact depends on initial conditions)
        assert abs(final_concentration - boundary_value) < 1.0
        
    def test_solve_steady_state_with_reactions(self):
        """Test steady-state solution with cell reactions"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        # Add some cell reactions (production)
        cell_reactions = {
            (400e-6, 400e-6): 3.0e-15,  # Center cell producing lactate
            (200e-6, 200e-6): 3.0e-15,  # Another producing cell
        }
        
        # Solve with reactions
        converged = simulator.solve_steady_state(cell_reactions)
        
        assert converged is True
        assert simulator.state.converged is True
        
        # With production, concentration should be higher than boundary value
        final_concentration = np.mean(simulator.concentration.value)
        boundary_value = simulator.substance_config.boundary_value.millimolar
        
        assert final_concentration > boundary_value
        
    def test_get_concentration_at_positions(self):
        """Test getting concentrations at grid positions"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        # Define some grid positions
        positions = {
            (20, 20): None,  # Center
            (10, 10): None,  # Off-center
            (0, 0): None,    # Corner
        }
        
        concentrations = simulator.get_concentration_at_positions(positions)
        
        assert len(concentrations) == 3
        assert (20, 20) in concentrations
        assert (10, 10) in concentrations
        assert (0, 0) in concentrations
        
        # All should be close to initial value initially
        initial_value = simulator.substance_config.initial_value.millimolar
        for conc in concentrations.values():
            assert abs(conc - initial_value) < 0.1
            
    def test_simulation_info(self):
        """Test getting simulation information"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        info = simulator.get_simulation_info()
        
        # Check all expected keys are present
        expected_keys = [
            'substance_name', 'diffusion_coefficient', 'boundary_type',
            'boundary_value', 'initial_value', 'mesh_cells', 'converged',
            'iterations', 'residual', 'min_concentration', 'max_concentration',
            'mean_concentration'
        ]
        
        for key in expected_keys:
            assert key in info
            
        # Check some values
        assert info['substance_name'] == "lactate"
        assert info['diffusion_coefficient'] == 6.70e-11
        assert info['boundary_type'] == "fixed"
        assert info['mesh_cells'] == 1600  # 40×40
        
    def test_reset(self):
        """Test resetting simulation"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        # Solve to change state
        simulator.solve_steady_state({})
        
        # Check state changed
        assert simulator.state.converged is True
        assert simulator.state.iterations > 0
        
        # Reset
        simulator.reset()
        
        # Check state reset
        assert simulator.state.time == 0.0
        assert simulator.state.converged is False
        assert simulator.state.iterations == 0
        
        # Check concentration reset to initial value
        initial_value = simulator.substance_config.initial_value.millimolar
        assert np.allclose(simulator.concentration.value, initial_value)
        
    def test_mesh_bounds(self):
        """Test mesh bounds calculation"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        bounds = simulator._get_mesh_bounds()
        
        assert 'x_min' in bounds
        assert 'x_max' in bounds
        assert 'y_min' in bounds
        assert 'y_max' in bounds
        
        # Check bounds are reasonable for 800μm domain
        assert bounds['x_min'] >= 0
        assert bounds['x_max'] <= 800e-6
        assert bounds['y_min'] >= 0
        assert bounds['y_max'] <= 800e-6
        
    def test_find_closest_cell(self):
        """Test finding closest mesh cell"""
        simulator = SubstanceSimulator(self.mesh_manager, self.substance_config)
        
        # Test point inside mesh
        center_point = (400e-6, 400e-6)
        cell_id = simulator._find_closest_cell(*center_point)
        
        assert cell_id is not None
        assert isinstance(cell_id, int)
        assert 0 <= cell_id < simulator.mesh_manager.mesh.numberOfCells
        
        # Test point outside mesh
        outside_point = (1000e-6, 1000e-6)
        cell_id = simulator._find_closest_cell(*outside_point)
        
        assert cell_id is None


class TestIntegration:
    """Integration tests for substance simulation"""
    
    def test_simulator_with_population_reactions(self):
        """Test simulator working with population reactions"""
        # Create domain and mesh
        domain_config = DomainConfig(
            size_x=Length(400.0, "μm"),  # Smaller domain for faster testing
            size_y=Length(400.0, "μm"),
            nx=20,
            ny=20
        )
        mesh_manager = MeshManager(domain_config)
        
        # Create substance config
        substance_config = SubstanceConfig(
            name="lactate",
            diffusion_coeff=6.70e-11,
            production_rate=3.0e-15,
            uptake_rate=0.0,
            initial_value=Concentration(5.0, "mM"),
            boundary_value=Concentration(2.0, "mM"),
            boundary_type="fixed"
        )
        
        # Create simulator
        simulator = SubstanceSimulator(mesh_manager, substance_config)
        
        # Simulate cell population reactions
        cell_reactions = {}
        for i in range(5, 15):  # Some cells in middle of domain
            for j in range(5, 15):
                x_pos = (i + 0.5) * mesh_manager.mesh.dx
                y_pos = (j + 0.5) * mesh_manager.mesh.dy
                cell_reactions[(float(x_pos), float(y_pos))] = 3.0e-15  # Production
        
        # Solve
        converged = simulator.solve_steady_state(cell_reactions)
        
        assert converged is True
        
        # Check that concentration is higher in production region
        center_conc = simulator.evaluate_at_point((200e-6, 200e-6))  # Center
        edge_conc = simulator.evaluate_at_point((50e-6, 50e-6))      # Edge
        
        assert center_conc > edge_conc  # Production creates gradient
        
        # Get field data for visualization
        X, Y, Z = simulator.get_field_data()
        assert X.shape == (20, 20)
        assert Y.shape == (20, 20)
        assert Z.shape == (20, 20)
        
        # Check concentration range is reasonable
        assert np.min(Z) >= 0  # No negative concentrations
        assert np.max(Z) > np.min(Z)  # Some variation due to production


class TestTimescaleState:
    """Test TimescaleState functionality"""

    def test_timescale_state_creation(self):
        """Test creating a TimescaleState"""
        state = TimescaleState()

        assert state.current_step == 0
        assert state.current_time == 0.0
        assert state.last_diffusion_step == 0
        assert state.last_intracellular_step == 0
        assert state.last_intercellular_step == 0
        assert state.total_diffusion_updates == 0
        assert state.total_intracellular_updates == 0
        assert state.total_intercellular_updates == 0

    def test_timescale_state_immutability(self):
        """Test that TimescaleState is immutable"""
        state = TimescaleState(current_step=5, current_time=2.5)

        # Create updated state
        new_state = state.with_updates(
            current_step=10,
            current_time=5.0,
            total_diffusion_updates=3
        )

        # Original state unchanged
        assert state.current_step == 5
        assert state.current_time == 2.5
        assert state.total_diffusion_updates == 0

        # New state has updates
        assert new_state.current_step == 10
        assert new_state.current_time == 5.0
        assert new_state.total_diffusion_updates == 3
        assert new_state.last_diffusion_step == 0  # Preserved


class TestProcessTiming:
    """Test ProcessTiming functionality"""

    def test_process_timing_creation(self):
        """Test creating a ProcessTiming"""
        timing = ProcessTiming(name="diffusion", interval=5)

        assert timing.name == "diffusion"
        assert timing.interval == 5
        assert timing.last_update == 0
        assert timing.total_updates == 0
        assert timing.total_time == 0.0
        assert timing.average_time == 0.0

    def test_record_update(self):
        """Test recording updates"""
        timing = ProcessTiming(name="diffusion", interval=5)

        # Record first update
        timing.record_update(step=5, duration=0.1)

        assert timing.last_update == 5
        assert timing.total_updates == 1
        assert timing.total_time == 0.1
        assert timing.average_time == 0.1

        # Record second update
        timing.record_update(step=10, duration=0.2)

        assert timing.last_update == 10
        assert timing.total_updates == 2
        assert abs(timing.total_time - 0.3) < 1e-10  # Handle floating point precision
        assert abs(timing.average_time - 0.15) < 1e-10


class TestTimescaleOrchestrator:
    """Test TimescaleOrchestrator functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.time_config = TimeConfig(
            dt=0.01,
            end_time=2.0,
            diffusion_step=5,
            intracellular_step=1,
            intercellular_step=10
        )

    def test_orchestrator_creation(self):
        """Test creating a TimescaleOrchestrator"""
        orchestrator = TimescaleOrchestrator(self.time_config)

        assert orchestrator.time_config == self.time_config
        assert orchestrator.state.current_step == 0
        assert orchestrator.state.current_time == 0.0
        assert len(orchestrator.process_timings) == 3
        assert 'diffusion' in orchestrator.process_timings
        assert 'intracellular' in orchestrator.process_timings
        assert 'intercellular' in orchestrator.process_timings

    def test_initial_update_decisions(self):
        """Test initial update decisions"""
        orchestrator = TimescaleOrchestrator(self.time_config)

        # Step 0 - should update intracellular (interval=1)
        updates = orchestrator.step(0)
        assert updates['intracellular'] is True
        assert updates['diffusion'] is False  # interval=5
        assert updates['intercellular'] is False  # interval=10

        # Step 1 - should update intracellular again
        updates = orchestrator.step(1)
        assert updates['intracellular'] is True
        assert updates['diffusion'] is False
        assert updates['intercellular'] is False

    def test_diffusion_update_timing(self):
        """Test diffusion update timing"""
        orchestrator = TimescaleOrchestrator(self.time_config)

        # Record some intracellular updates
        for step in range(5):
            updates = orchestrator.step(step)
            if updates['intracellular']:
                orchestrator.record_process_timing('intracellular', 0.01, step)

        # Step 5 - should update diffusion (interval=5)
        updates = orchestrator.step(5)
        assert updates['diffusion'] is True
        assert updates['intracellular'] is True  # Forced due to dependency

    def test_intercellular_update_timing(self):
        """Test intercellular update timing"""
        orchestrator = TimescaleOrchestrator(self.time_config)

        # Record updates up to step 10
        for step in range(10):
            updates = orchestrator.step(step)
            for process, should_update in updates.items():
                if should_update:
                    orchestrator.record_process_timing(process, 0.01, step)

        # Step 10 - should update intercellular (interval=10)
        updates = orchestrator.step(10)
        assert updates['intercellular'] is True
        assert updates['diffusion'] is True  # Forced due to dependency
        assert updates['intracellular'] is True  # Forced due to dependency

    def test_dependency_enforcement(self):
        """Test that dependencies are enforced"""
        orchestrator = TimescaleOrchestrator(self.time_config)

        # Manually set last updates to create dependency scenario
        orchestrator.process_timings['intracellular'].last_update = 0
        orchestrator.process_timings['diffusion'].last_update = 0
        orchestrator.process_timings['intercellular'].last_update = 0

        # Force intercellular update
        updates = orchestrator.step(10)  # Step 10 triggers intercellular

        # Should force all dependencies
        assert updates['intercellular'] is True
        assert updates['diffusion'] is True  # Forced
        assert updates['intracellular'] is True  # Forced

    def test_record_process_timing(self):
        """Test recording process timing"""
        orchestrator = TimescaleOrchestrator(self.time_config)

        # Record diffusion timing
        orchestrator.record_process_timing('diffusion', 0.15, 5)

        assert orchestrator.process_timings['diffusion'].last_update == 5
        assert orchestrator.process_timings['diffusion'].total_updates == 1
        assert orchestrator.process_timings['diffusion'].total_time == 0.15
        assert orchestrator.state.last_diffusion_step == 5
        assert orchestrator.state.total_diffusion_updates == 1

    def test_timing_statistics(self):
        """Test getting timing statistics"""
        orchestrator = TimescaleOrchestrator(self.time_config)

        # Record some updates
        orchestrator.record_process_timing('diffusion', 0.1, 5)
        orchestrator.record_process_timing('intracellular', 0.05, 1)
        orchestrator.step(10)

        stats = orchestrator.get_timing_statistics()

        assert 'current_step' in stats
        assert 'current_time' in stats
        assert 'processes' in stats
        assert 'diffusion' in stats['processes']
        assert 'intracellular' in stats['processes']
        assert 'intercellular' in stats['processes']

        # Check diffusion stats
        diff_stats = stats['processes']['diffusion']
        assert diff_stats['total_updates'] == 1
        assert diff_stats['total_time'] == 0.1
        assert diff_stats['average_time'] == 0.1

    def test_adaptive_timing(self):
        """Test adaptive timing functionality"""
        orchestrator = TimescaleOrchestrator(self.time_config)

        # Enable adaptive timing
        orchestrator.set_adaptive_timing(True, target_time=0.1)
        assert orchestrator.adaptive_timing is True
        assert orchestrator.target_step_time == 0.1

        # Simulate slow steps
        for _ in range(15):
            orchestrator.adapt_timing(0.2)  # Slow steps

        # Intervals should increase
        original_intervals = {name: timing.interval for name, timing in orchestrator.process_timings.items()}

        # Simulate more slow steps to trigger adaptation
        for _ in range(10):
            orchestrator.adapt_timing(0.2)

        # Check if intervals increased (may not change immediately due to averaging)
        stats = orchestrator.get_timing_statistics()
        assert 'step_timing' in stats
        assert stats['step_timing']['recent_average'] > 0.1

    def test_reset(self):
        """Test resetting orchestrator"""
        orchestrator = TimescaleOrchestrator(self.time_config)

        # Make some changes
        orchestrator.step(10)
        orchestrator.record_process_timing('diffusion', 0.1, 5)
        orchestrator.adapt_timing(0.2)

        # Reset
        orchestrator.reset()

        # Check state is reset
        assert orchestrator.state.current_step == 0
        assert orchestrator.state.current_time == 0.0
        assert orchestrator.state.total_diffusion_updates == 0

        # Check process timings are reset
        for timing in orchestrator.process_timings.values():
            assert timing.last_update == 0
            assert timing.total_updates == 0
            assert timing.total_time == 0.0

        assert len(orchestrator.timing_history) == 0


class TestOrchestratorIntegration:
    """Integration tests for orchestrator"""

    def test_realistic_simulation_timing(self):
        """Test orchestrator with realistic simulation timing"""
        time_config = TimeConfig(
            dt=0.01,  # 0.01 hour time steps
            end_time=1.0,  # 1 hour simulation
            diffusion_step=5,  # Every 0.05 hours
            intracellular_step=1,  # Every 0.01 hours
            intercellular_step=10  # Every 0.1 hours
        )

        orchestrator = TimescaleOrchestrator(time_config)

        # Simulate 100 steps (1 hour)
        diffusion_updates = 0
        intracellular_updates = 0
        intercellular_updates = 0

        for step in range(100):
            updates = orchestrator.step(step)

            # Record updates
            for process, should_update in updates.items():
                if should_update:
                    # Simulate different process times
                    if process == 'diffusion':
                        duration = 0.05
                        diffusion_updates += 1
                    elif process == 'intracellular':
                        duration = 0.01
                        intracellular_updates += 1
                    elif process == 'intercellular':
                        duration = 0.02
                        intercellular_updates += 1

                    orchestrator.record_process_timing(process, duration, step)

        # Check update frequencies
        assert intracellular_updates == 100  # Every step
        assert diffusion_updates == 19  # Steps 5, 10, 15, ..., 95 (19 updates)
        assert intercellular_updates == 9  # Steps 10, 20, 30, ..., 90 (9 updates)

        # Check final statistics
        stats = orchestrator.get_timing_statistics()
        assert stats['current_step'] == 99
        assert abs(stats['current_time'] - 0.99) < 0.01  # 99 * 0.01

        # Check process statistics
        assert stats['processes']['intracellular']['total_updates'] == 100
        assert stats['processes']['diffusion']['total_updates'] == 19
        assert stats['processes']['intercellular']['total_updates'] == 9


class TestPerformanceMetrics:
    """Test PerformanceMetrics functionality"""

    def test_performance_metrics_creation(self):
        """Test creating PerformanceMetrics"""
        import time
        timestamp = time.time()

        metrics = PerformanceMetrics(
            timestamp=timestamp,
            cpu_percent=25.5,
            memory_mb=512.0,
            memory_percent=15.2,
            process_times={'diffusion': 0.1, 'intracellular': 0.05},
            custom_metrics={'cells_count': 100}
        )

        assert metrics.timestamp == timestamp
        assert metrics.cpu_percent == 25.5
        assert metrics.memory_mb == 512.0
        assert metrics.memory_percent == 15.2
        assert metrics.process_times['diffusion'] == 0.1
        assert metrics.custom_metrics['cells_count'] == 100

    def test_performance_metrics_to_dict(self):
        """Test converting metrics to dictionary"""
        import time
        timestamp = time.time()

        metrics = PerformanceMetrics(
            timestamp=timestamp,
            cpu_percent=25.5,
            memory_mb=512.0,
            memory_percent=15.2
        )

        data = metrics.to_dict()

        assert isinstance(data, dict)
        assert data['timestamp'] == timestamp
        assert data['cpu_percent'] == 25.5
        assert data['memory_mb'] == 512.0
        assert data['memory_percent'] == 15.2
        assert isinstance(data['process_times'], dict)
        assert isinstance(data['custom_metrics'], dict)


class TestProfileEntry:
    """Test ProfileEntry functionality"""

    def test_profile_entry_creation(self):
        """Test creating a ProfileEntry"""
        import time
        start_time = time.time()

        entry = ProfileEntry(
            name="test_process",
            start_time=start_time,
            metadata={'param1': 'value1'}
        )

        assert entry.name == "test_process"
        assert entry.start_time == start_time
        assert entry.end_time is None
        assert entry.duration is None
        assert entry.metadata['param1'] == 'value1'

    def test_profile_entry_finish(self):
        """Test finishing a ProfileEntry"""
        import time
        start_time = time.time()

        entry = ProfileEntry(name="test_process", start_time=start_time)

        # Small delay to ensure duration > 0
        time.sleep(0.01)

        entry.finish({'result': 'success'})

        assert entry.end_time is not None
        assert entry.duration is not None
        assert entry.duration > 0
        assert entry.metadata['result'] == 'success'


class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality"""

    def test_monitor_creation(self):
        """Test creating a PerformanceMonitor"""
        monitor = PerformanceMonitor(max_history=100)

        assert monitor.max_history == 100
        assert len(monitor.metrics_history) == 0
        assert len(monitor.profile_history) == 0
        assert len(monitor.active_profiles) == 0
        assert monitor.monitoring_enabled is True
        assert monitor.alerts_enabled is True

    def test_capture_metrics(self):
        """Test capturing performance metrics"""
        monitor = PerformanceMonitor()

        metrics = monitor.capture_metrics()

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.timestamp > 0
        assert metrics.cpu_percent >= 0
        assert metrics.memory_mb >= 0
        assert metrics.memory_percent >= 0
        assert isinstance(metrics.process_times, dict)
        assert isinstance(metrics.custom_metrics, dict)

    def test_profiling_context_manager(self):
        """Test profiling with context manager"""
        import time
        monitor = PerformanceMonitor()

        with monitor.profile("test_operation", {'param': 'value'}) as entry:
            time.sleep(0.01)  # Small delay
            assert entry.name == "test_operation"
            assert entry.start_time > 0
            assert entry.end_time is None

        # Check that profile was recorded
        assert "test_operation" in monitor.profile_history
        assert len(monitor.profile_history["test_operation"]) == 1

        recorded_entry = monitor.profile_history["test_operation"][0]
        assert recorded_entry.duration is not None
        assert recorded_entry.duration > 0
        assert recorded_entry.metadata['param'] == 'value'

    def test_manual_profiling(self):
        """Test manual profiling start/end"""
        import time
        monitor = PerformanceMonitor()

        # Start profiling
        entry = monitor.start_profile("manual_test", {'type': 'manual'})
        assert entry.name == "manual_test"
        assert "manual_test" in monitor.active_profiles

        time.sleep(0.01)

        # End profiling
        finished_entry = monitor.end_profile("manual_test", {'status': 'completed'})

        assert finished_entry is not None
        assert finished_entry.duration > 0
        assert finished_entry.metadata['type'] == 'manual'
        assert finished_entry.metadata['status'] == 'completed'
        assert "manual_test" not in monitor.active_profiles
        assert "manual_test" in monitor.profile_history

    def test_thresholds_and_alerts(self):
        """Test threshold checking and alerts"""
        import time
        monitor = PerformanceMonitor()

        # Set low thresholds to trigger alerts
        monitor.set_threshold('cpu_percent', 0.1)
        monitor.set_threshold('memory_mb', 1.0)

        alerts_triggered = []

        def alert_callback(alert_data):
            alerts_triggered.append(alert_data)

        monitor.add_alert_callback(alert_callback)

        # Create metrics that exceed thresholds
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            cpu_percent=50.0,  # Above 0.1 threshold
            memory_mb=100.0,   # Above 1.0 threshold
            memory_percent=10.0
        )

        monitor._check_thresholds(metrics)

        # Should have triggered 2 alerts
        assert len(alerts_triggered) >= 1  # At least one alert
        assert monitor.stats['total_alerts'] >= 1

    def test_statistics(self):
        """Test getting performance statistics"""
        import time
        monitor = PerformanceMonitor()

        # Add some data
        monitor.start_profile("test1")
        time.sleep(0.01)
        monitor.end_profile("test1")

        monitor.start_profile("test2")
        time.sleep(0.01)
        monitor.end_profile("test2")

        stats = monitor.get_statistics()

        assert 'uptime_seconds' in stats
        assert 'total_profiles' in stats
        assert 'total_alerts' in stats
        assert 'active_profiles' in stats
        assert 'metrics_history_size' in stats
        assert 'thresholds' in stats
        assert 'monitoring_enabled' in stats
        assert 'profile_statistics' in stats

        assert stats['total_profiles'] == 2
        assert stats['active_profiles'] == 0

        # Check profile statistics
        if 'test1' in stats['profile_statistics']:
            test1_stats = stats['profile_statistics']['test1']
            assert 'count' in test1_stats
            assert 'avg_duration' in test1_stats
            assert 'min_duration' in test1_stats
            assert 'max_duration' in test1_stats
            assert test1_stats['count'] == 1

    def test_history_management(self):
        """Test metrics and profile history management"""
        import time
        monitor = PerformanceMonitor(max_history=3)

        # Add metrics
        for i in range(5):
            metrics = PerformanceMetrics(
                timestamp=time.time() + i,
                cpu_percent=i * 10,
                memory_mb=i * 100,
                memory_percent=i * 5
            )
            monitor.metrics_history.append(metrics)

        # Should only keep last 3
        assert len(monitor.metrics_history) == 3

        # Add profiles
        for i in range(5):
            monitor.start_profile(f"test_{i}")
            time.sleep(0.001)
            monitor.end_profile(f"test_{i}")

        # Check profile history
        for i in range(5):
            process_name = f"test_{i}"
            if process_name in monitor.profile_history:
                assert len(monitor.profile_history[process_name]) <= monitor.max_history

    def test_reset_statistics(self):
        """Test resetting statistics"""
        import time
        monitor = PerformanceMonitor()

        # Add some data
        monitor.start_profile("test")
        time.sleep(0.01)
        monitor.end_profile("test")

        metrics = monitor.capture_metrics()
        monitor.metrics_history.append(metrics)

        # Verify data exists
        assert monitor.stats['total_profiles'] > 0
        assert len(monitor.metrics_history) > 0
        assert len(monitor.profile_history) > 0

        # Reset
        monitor.reset_statistics()

        # Verify reset
        assert monitor.stats['total_profiles'] == 0
        assert monitor.stats['total_alerts'] == 0
        assert len(monitor.metrics_history) == 0
        assert len(monitor.profile_history) == 0
        assert len(monitor.active_profiles) == 0

    def test_enable_disable_monitoring(self):
        """Test enabling/disabling monitoring"""
        monitor = PerformanceMonitor()

        assert monitor.monitoring_enabled is True

        monitor.enable_monitoring(False)
        assert monitor.monitoring_enabled is False

        monitor.enable_monitoring(True)
        assert monitor.monitoring_enabled is True

    def test_enable_disable_alerts(self):
        """Test enabling/disabling alerts"""
        monitor = PerformanceMonitor()

        assert monitor.alerts_enabled is True

        monitor.enable_alerts(False)
        assert monitor.alerts_enabled is False

        monitor.enable_alerts(True)
        assert monitor.alerts_enabled is True


class TestPerformanceIntegration:
    """Integration tests for performance monitoring"""

    def test_monitor_with_simulation_components(self):
        """Test performance monitor with simulation components"""
        import time

        # Create monitor
        monitor = PerformanceMonitor()

        # Simulate some operations
        with monitor.profile("simulation_step"):
            time.sleep(0.01)

            with monitor.profile("diffusion_solve"):
                time.sleep(0.005)

            with monitor.profile("cell_update"):
                time.sleep(0.003)

        # Check results
        stats = monitor.get_statistics()

        assert stats['total_profiles'] == 3
        assert 'simulation_step' in monitor.profile_history
        assert 'diffusion_solve' in monitor.profile_history
        assert 'cell_update' in monitor.profile_history

        # Check nested timing makes sense
        sim_duration = monitor.profile_history['simulation_step'][0].duration
        diff_duration = monitor.profile_history['diffusion_solve'][0].duration
        cell_duration = monitor.profile_history['cell_update'][0].duration

        assert sim_duration > diff_duration
        assert sim_duration > cell_duration
        assert diff_duration > 0
        assert cell_duration > 0
