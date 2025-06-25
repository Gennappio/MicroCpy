"""
Tests for visualization module

Tests the plotting, analysis, and export functionality.
"""

import pytest
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import tempfile
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))

from visualization.plotter import SimulationPlotter, PlotConfig
from visualization.analysis import DataAnalyzer, TimeSeriesAnalyzer, AnalysisResult
from visualization.export import PlotExporter, AnimationExporter

# Import test fixtures
from core.domain import MeshManager
from core.units import Length, Concentration
from biology.population import CellPopulation
from simulation.substance_simulator import SubstanceSimulator
from simulation.performance import PerformanceMonitor
from config import DomainConfig, SubstanceConfig

class TestPlotConfig:
    """Test PlotConfig functionality"""
    
    def test_plot_config_creation(self):
        """Test creating a PlotConfig"""
        config = PlotConfig()
        
        assert config.figsize == (12, 8)
        assert config.dpi == 300
        assert config.font_size == 12
        assert config.save_format == 'png'
        
    def test_plot_config_custom(self):
        """Test custom PlotConfig"""
        config = PlotConfig(
            figsize=(10, 6),
            dpi=150,
            font_size=14,
            save_format='pdf'
        )
        
        assert config.figsize == (10, 6)
        assert config.dpi == 150
        assert config.font_size == 14
        assert config.save_format == 'pdf'

class TestSimulationPlotter:
    """Test SimulationPlotter functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create test simulation components
        domain_config = DomainConfig(
            size_x=Length(200.0, "μm"),
            size_y=Length(200.0, "μm"),
            nx=10,
            ny=10
        )
        self.mesh_manager = MeshManager(domain_config)
        
        substance_config = SubstanceConfig(
            name="test_substance",
            diffusion_coeff=1e-9,
            production_rate=1e-15,
            uptake_rate=0.0,
            initial_value=Concentration(5.0, "mM"),
            boundary_value=Concentration(2.0, "mM")
        )
        self.simulator = SubstanceSimulator(self.mesh_manager, substance_config)
        
        self.population = CellPopulation(grid_size=(10, 10))
        self.population.add_cell((5, 5), "normal")
        self.population.add_cell((3, 3), "hypoxic")
        
        self.monitor = PerformanceMonitor()
        
        # Create plotter
        config = PlotConfig(dpi=100)  # Lower DPI for tests
        self.plotter = SimulationPlotter(config)
    
    def test_plotter_creation(self):
        """Test creating a SimulationPlotter"""
        assert self.plotter.config.dpi == 100
        assert 'normal' in self.plotter.phenotype_colors
        assert 'hypoxic' in self.plotter.phenotype_colors
    
    def test_plot_concentration_field(self):
        """Test plotting concentration field"""
        fig = self.plotter.plot_concentration_field(
            self.simulator, 
            title="Test Concentration"
        )
        
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) >= 1  # At least one axis
        
        plt.close(fig)
    
    def test_plot_cell_population(self):
        """Test plotting cell population"""
        fig = self.plotter.plot_cell_population(
            self.population,
            title="Test Population"
        )
        
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) >= 1
        
        plt.close(fig)
    
    def test_plot_population_statistics(self):
        """Test plotting population statistics"""
        # Create mock history
        stats_history = [
            {'total_cells': 10, 'average_age': 0.0, 'generation_count': 0, 'grid_occupancy': 0.1},
            {'total_cells': 12, 'average_age': 0.1, 'generation_count': 1, 'grid_occupancy': 0.12},
            {'total_cells': 15, 'average_age': 0.2, 'generation_count': 2, 'grid_occupancy': 0.15}
        ]
        
        fig = self.plotter.plot_population_statistics(
            stats_history,
            title="Test Statistics"
        )
        
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 4  # Four subplots
        
        plt.close(fig)
    
    def test_plot_performance_metrics(self):
        """Test plotting performance metrics"""
        # Add some mock data to monitor
        self.monitor.start_profile("test_process")
        self.monitor.end_profile("test_process")
        
        fig = self.plotter.plot_performance_metrics(
            self.monitor,
            title="Test Performance"
        )
        
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) == 4  # Four subplots
        
        plt.close(fig)
    
    def test_plot_combined_overview(self):
        """Test plotting combined overview"""
        fig = self.plotter.plot_combined_overview(
            self.simulator, self.population, self.monitor,
            title="Test Overview"
        )
        
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) >= 6  # Multiple subplots
        
        plt.close(fig)
    
    def teardown_method(self):
        """Clean up after tests"""
        self.plotter.close_all()

class TestDataAnalyzer:
    """Test DataAnalyzer functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        domain_config = DomainConfig(
            size_x=Length(200.0, "μm"),
            size_y=Length(200.0, "μm"),
            nx=10,
            ny=10
        )
        mesh_manager = MeshManager(domain_config)
        
        substance_config = SubstanceConfig(
            name="test_substance",
            diffusion_coeff=1e-9,
            production_rate=1e-15,
            uptake_rate=0.0,
            initial_value=Concentration(5.0, "mM"),
            boundary_value=Concentration(2.0, "mM")
        )
        self.simulator = SubstanceSimulator(mesh_manager, substance_config)
        
        self.population = CellPopulation(grid_size=(10, 10))
        self.population.add_cell((5, 5), "normal")
        
        self.monitor = PerformanceMonitor()
        self.analyzer = DataAnalyzer()
    
    def test_analyzer_creation(self):
        """Test creating a DataAnalyzer"""
        assert isinstance(self.analyzer, DataAnalyzer)
    
    def test_analyze_concentration_field(self):
        """Test concentration field analysis"""
        result = self.analyzer.analyze_concentration_field(self.simulator)
        
        assert isinstance(result, AnalysisResult)
        assert result.name == "concentration_field_analysis"
        assert 'mean' in result.statistics
        assert 'std' in result.statistics
        assert 'min' in result.statistics
        assert 'max' in result.statistics
        assert result.statistics['mean'] > 0
    
    def test_analyze_population_dynamics(self):
        """Test population dynamics analysis"""
        result = self.analyzer.analyze_population_dynamics(self.population)
        
        assert isinstance(result, AnalysisResult)
        assert result.name == "population_dynamics_analysis"
        assert 'total_cells' in result.statistics
        assert 'age_mean' in result.statistics
        assert result.statistics['total_cells'] == 1
    
    def test_analyze_performance_metrics(self):
        """Test performance metrics analysis"""
        # Add some data to monitor
        self.monitor.start_profile("test")
        self.monitor.end_profile("test")
        
        result = self.analyzer.analyze_performance_metrics(self.monitor)
        
        assert isinstance(result, AnalysisResult)
        assert result.name == "performance_analysis"
        assert isinstance(result.statistics, dict)
    
    def test_compare_simulations(self):
        """Test simulation comparison"""
        # Create multiple analysis results
        result1 = self.analyzer.analyze_concentration_field(self.simulator)
        result2 = self.analyzer.analyze_population_dynamics(self.population)
        
        comparison = self.analyzer.compare_simulations([result1, result2])
        
        assert isinstance(comparison, AnalysisResult)
        assert comparison.name == "simulation_comparison"
        assert 'num_simulations' in comparison.metadata
        assert comparison.metadata['num_simulations'] == 2

class TestTimeSeriesAnalyzer:
    """Test TimeSeriesAnalyzer functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = TimeSeriesAnalyzer()
    
    def test_analyzer_creation(self):
        """Test creating a TimeSeriesAnalyzer"""
        assert isinstance(self.analyzer, TimeSeriesAnalyzer)
    
    def test_analyze_population_growth(self):
        """Test population growth analysis"""
        # Create mock population history
        history = [
            {'total_cells': 10, 'phenotype_counts': {'normal': 10}},
            {'total_cells': 12, 'phenotype_counts': {'normal': 12}},
            {'total_cells': 15, 'phenotype_counts': {'normal': 15}}
        ]
        
        result = self.analyzer.analyze_population_growth(history)
        
        assert isinstance(result, AnalysisResult)
        assert result.name == "population_growth_analysis"
        assert 'initial_population' in result.statistics
        assert 'final_population' in result.statistics
        assert 'total_growth' in result.statistics
        assert result.statistics['initial_population'] == 10
        assert result.statistics['final_population'] == 15
        assert result.statistics['total_growth'] == 5
    
    def test_analyze_concentration_evolution(self):
        """Test concentration evolution analysis"""
        # Create mock concentration history
        history = [
            np.full((10, 10), 5.0),
            np.full((10, 10), 5.2),
            np.full((10, 10), 5.5)
        ]
        
        result = self.analyzer.analyze_concentration_evolution(history)
        
        assert isinstance(result, AnalysisResult)
        assert result.name == "concentration_evolution_analysis"
        assert 'initial_mean_concentration' in result.statistics
        assert 'final_mean_concentration' in result.statistics
        assert result.statistics['initial_mean_concentration'] == 5.0
        assert result.statistics['final_mean_concentration'] == 5.5
    
    def test_detect_steady_state(self):
        """Test steady state detection"""
        # Create time series that reaches steady state
        time_series = [1.0, 1.1, 1.05, 1.02, 1.01, 1.005, 1.002, 1.001, 1.0005, 1.0002]
        
        result = self.analyzer.detect_steady_state(time_series, window_size=5, tolerance=0.01)
        
        assert 'steady_state_reached' in result
        assert isinstance(result['steady_state_reached'], bool)
    
    def test_calculate_autocorrelation(self):
        """Test autocorrelation calculation"""
        # Create simple time series
        time_series = [1, 2, 3, 4, 5, 4, 3, 2, 1]
        
        result = self.analyzer.calculate_autocorrelation(time_series, max_lag=5)
        
        assert 'lags' in result
        assert 'autocorrelation' in result
        assert len(result['lags']) == 6  # 0 to 5
        assert len(result['autocorrelation']) == 6
        assert result['autocorrelation'][0] == 1.0  # Perfect correlation at lag 0

class TestPlotExporter:
    """Test PlotExporter functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.exporter = PlotExporter(self.temp_dir)
        
        # Create test simulation components
        domain_config = DomainConfig(
            size_x=Length(200.0, "μm"),
            size_y=Length(200.0, "μm"),
            nx=10,
            ny=10
        )
        mesh_manager = MeshManager(domain_config)
        
        substance_config = SubstanceConfig(
            name="test_substance",
            diffusion_coeff=1e-9,
            production_rate=1e-15,
            uptake_rate=0.0,
            initial_value=Concentration(5.0, "mM"),
            boundary_value=Concentration(2.0, "mM")
        )
        self.simulator = SubstanceSimulator(mesh_manager, substance_config)
        
        self.population = CellPopulation(grid_size=(10, 10))
        self.population.add_cell((5, 5), "normal")
        
        self.monitor = PerformanceMonitor()
    
    def test_exporter_creation(self):
        """Test creating a PlotExporter"""
        assert self.exporter.output_dir == Path(self.temp_dir)
        assert self.exporter.output_dir.exists()
    
    def test_export_concentration_data(self):
        """Test exporting concentration data"""
        filepath = self.exporter.export_concentration_data(self.simulator)
        
        assert Path(filepath).exists()
        assert Path(filepath).suffix == '.csv'
        
        # Check file has content
        assert Path(filepath).stat().st_size > 0
    
    def test_export_population_data(self):
        """Test exporting population data"""
        filepath = self.exporter.export_population_data(self.population)
        
        assert Path(filepath).exists()
        assert Path(filepath).suffix == '.csv'
        assert Path(filepath).stat().st_size > 0
    
    def test_export_performance_data(self):
        """Test exporting performance data"""
        # Add some data to monitor
        self.monitor.start_profile("test")
        self.monitor.end_profile("test")
        
        filepath = self.exporter.export_performance_data(self.monitor)
        
        assert Path(filepath).exists()
        assert Path(filepath).suffix == '.json'
        assert Path(filepath).stat().st_size > 0
    
    def test_export_simulation_summary(self):
        """Test exporting simulation summary"""
        filepath = self.exporter.export_simulation_summary(
            self.simulator, self.population, self.monitor
        )
        
        assert Path(filepath).exists()
        assert Path(filepath).suffix == '.json'
        assert Path(filepath).stat().st_size > 0

class TestIntegration:
    """Integration tests for visualization system"""
    
    def test_complete_visualization_workflow(self):
        """Test complete visualization workflow"""
        # Create simulation components
        domain_config = DomainConfig(
            size_x=Length(100.0, "μm"),
            size_y=Length(100.0, "μm"),
            nx=5,
            ny=5
        )
        mesh_manager = MeshManager(domain_config)
        
        substance_config = SubstanceConfig(
            name="test_substance",
            diffusion_coeff=1e-9,
            production_rate=1e-15,
            uptake_rate=0.0,
            initial_value=Concentration(5.0, "mM"),
            boundary_value=Concentration(2.0, "mM")
        )
        simulator = SubstanceSimulator(mesh_manager, substance_config)
        
        population = CellPopulation(grid_size=(5, 5))
        population.add_cell((2, 2), "normal")
        
        monitor = PerformanceMonitor()
        
        # Create visualization components
        plotter = SimulationPlotter(PlotConfig(dpi=50))  # Low DPI for tests
        analyzer = DataAnalyzer()
        
        # Test analysis workflow
        conc_analysis = analyzer.analyze_concentration_field(simulator)
        pop_analysis = analyzer.analyze_population_dynamics(population)
        
        assert conc_analysis.statistics['mean'] > 0
        assert pop_analysis.statistics['total_cells'] == 1
        
        # Test plotting workflow
        conc_fig = plotter.plot_concentration_field(simulator)
        pop_fig = plotter.plot_cell_population(population)
        
        assert isinstance(conc_fig, plt.Figure)
        assert isinstance(pop_fig, plt.Figure)
        
        # Clean up
        plt.close(conc_fig)
        plt.close(pop_fig)
        plotter.close_all()
