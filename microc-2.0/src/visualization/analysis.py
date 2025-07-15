"""
Data analysis tools for MicroC 2.0

Provides statistical analysis and data processing capabilities for simulation results.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any

# Optional scipy import
try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available. Some statistical functions will be limited.")
from dataclasses import dataclass
import sys
from pathlib import Path

# Add interfaces to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from interfaces.base import CustomizableComponent

@dataclass
class AnalysisResult:
    """Container for analysis results"""
    name: str
    data: Any
    statistics: Dict[str, float]
    metadata: Dict[str, Any]

class DataAnalyzer(CustomizableComponent):
    """
    Statistical analysis tools for simulation data
    """
    
    def __init__(self, custom_functions_module=None):
        super().__init__(custom_functions_module)
    
    def analyze_concentration_field(self, simulator) -> AnalysisResult:
        """Analyze concentration field statistics"""
        
        concentration = np.array(simulator.concentration.value)
        
        statistics = {
            'mean': float(np.mean(concentration)),
            'std': float(np.std(concentration)),
            'min': float(np.min(concentration)),
            'max': float(np.max(concentration)),
            'median': float(np.median(concentration)),
            'q25': float(np.percentile(concentration, 25)),
            'q75': float(np.percentile(concentration, 75))
        }

        # Add scipy-dependent statistics if available
        if SCIPY_AVAILABLE:
            statistics.update({
                'skewness': float(stats.skew(concentration)),
                'kurtosis': float(stats.kurtosis(concentration))
            })
        else:
            statistics.update({
                'skewness': 0.0,  # Fallback value
                'kurtosis': 0.0   # Fallback value
            })
        
        metadata = {
            'substance_name': simulator.substance_config.name,
            'mesh_size': concentration.shape,
            'total_cells': len(concentration),
            'converged': simulator.state.converged
        }
        
        return AnalysisResult(
            name="concentration_field_analysis",
            data=concentration,
            statistics=statistics,
            metadata=metadata
        )
    
    def analyze_population_dynamics(self, population) -> AnalysisResult:
        """Analyze cell population characteristics"""
        
        stats_dict = population.get_population_statistics()
        
        # Calculate additional statistics
        cell_ages = [cell.state.age for cell in population.state.cells.values()]
        
        if cell_ages:
            age_stats = {
                'age_mean': float(np.mean(cell_ages)),
                'age_std': float(np.std(cell_ages)),
                'age_min': float(np.min(cell_ages)),
                'age_max': float(np.max(cell_ages))
            }
        else:
            age_stats = {'age_mean': 0, 'age_std': 0, 'age_min': 0, 'age_max': 0}
        
        # Combine with population statistics
        statistics = {**stats_dict, **age_stats}
        
        metadata = {
            'grid_size': population.grid_size,
            'total_positions': population.grid_size[0] * population.grid_size[1],
            'cell_positions': population.get_cell_positions()
        }
        
        return AnalysisResult(
            name="population_dynamics_analysis",
            data=cell_ages,
            statistics=statistics,
            metadata=metadata
        )
    
    def analyze_performance_metrics(self, monitor) -> AnalysisResult:
        """Analyze performance monitoring data"""
        
        perf_stats = monitor.get_statistics()
        metrics_history = monitor.get_metrics_history()
        
        statistics = {}
        
        # Analyze timing data
        if 'profile_statistics' in perf_stats:
            for process, proc_stats in perf_stats['profile_statistics'].items():
                statistics[f'{process}_avg_time'] = proc_stats['avg_duration']
                statistics[f'{process}_total_time'] = proc_stats['total_duration']
                statistics[f'{process}_count'] = proc_stats['count']
        
        # Analyze resource usage
        if metrics_history:
            cpu_values = [m['cpu_percent'] for m in metrics_history]
            memory_values = [m['memory_mb'] for m in metrics_history]
            
            statistics.update({
                'cpu_mean': float(np.mean(cpu_values)),
                'cpu_max': float(np.max(cpu_values)),
                'memory_mean': float(np.mean(memory_values)),
                'memory_max': float(np.max(memory_values))
            })
        
        metadata = {
            'total_profiles': perf_stats['total_profiles'],
            'total_alerts': perf_stats['total_alerts'],
            'monitoring_enabled': perf_stats['monitoring_enabled'],
            'history_length': len(metrics_history)
        }
        
        return AnalysisResult(
            name="performance_analysis",
            data=metrics_history,
            statistics=statistics,
            metadata=metadata
        )
    
    def compare_simulations(self, results_list: List[AnalysisResult]) -> AnalysisResult:
        """Compare multiple simulation results"""
        
        if not results_list:
            raise ValueError("No results provided for comparison")
        
        # Extract key metrics for comparison
        comparison_data = {}
        for i, result in enumerate(results_list):
            comparison_data[f'simulation_{i}'] = result.statistics
        
        # Calculate comparative statistics
        statistics = {}
        if len(results_list) > 1:
            # Compare means across simulations
            for key in results_list[0].statistics.keys():
                values = [r.statistics[key] for r in results_list]
                statistics[f'{key}_comparison_mean'] = float(np.mean(values))
                statistics[f'{key}_comparison_std'] = float(np.std(values))
                statistics[f'{key}_comparison_range'] = float(np.max(values) - np.min(values))
        
        metadata = {
            'num_simulations': len(results_list),
            'simulation_names': [r.name for r in results_list]
        }
        
        return AnalysisResult(
            name="simulation_comparison",
            data=comparison_data,
            statistics=statistics,
            metadata=metadata
        )

class TimeSeriesAnalyzer(CustomizableComponent):
    """
    Time series analysis for simulation data
    """
    
    def __init__(self, custom_functions_module=None):
        super().__init__(custom_functions_module)
    
    def analyze_population_growth(self, population_history: List[Dict]) -> AnalysisResult:
        """Analyze population growth patterns"""
        
        if not population_history:
            raise ValueError("No population history provided")
        
        # Extract time series data
        times = list(range(len(population_history)))
        total_cells = [stats['total_cells'] for stats in population_history]
        
        # Calculate growth statistics
        if len(total_cells) > 1:
            growth_rates = np.diff(total_cells)
            statistics = {
                'initial_population': float(total_cells[0]),
                'final_population': float(total_cells[-1]),
                'total_growth': float(total_cells[-1] - total_cells[0]),
                'mean_growth_rate': float(np.mean(growth_rates)),
                'max_growth_rate': float(np.max(growth_rates)),
                'min_growth_rate': float(np.min(growth_rates)),
                'growth_variability': float(np.std(growth_rates))
            }
        else:
            statistics = {
                'initial_population': float(total_cells[0]),
                'final_population': float(total_cells[0]),
                'total_growth': 0.0,
                'mean_growth_rate': 0.0,
                'max_growth_rate': 0.0,
                'min_growth_rate': 0.0,
                'growth_variability': 0.0
            }
        
        metadata = {
            'time_points': len(times),
            'duration': len(times) - 1,
            'phenotype_evolution': [stats['phenotype_counts'] for stats in population_history]
        }
        
        return AnalysisResult(
            name="population_growth_analysis",
            data={'times': times, 'populations': total_cells},
            statistics=statistics,
            metadata=metadata
        )
    
    def analyze_concentration_evolution(self, concentration_history: List[np.ndarray]) -> AnalysisResult:
        """Analyze how concentration fields evolve over time"""
        
        if not concentration_history:
            raise ValueError("No concentration history provided")
        
        # Calculate statistics over time
        mean_concentrations = [float(np.mean(conc)) for conc in concentration_history]
        std_concentrations = [float(np.std(conc)) for conc in concentration_history]
        
        # Analyze temporal changes
        if len(mean_concentrations) > 1:
            mean_changes = np.diff(mean_concentrations)
            statistics = {
                'initial_mean_concentration': mean_concentrations[0],
                'final_mean_concentration': mean_concentrations[-1],
                'total_concentration_change': mean_concentrations[-1] - mean_concentrations[0],
                'mean_change_rate': float(np.mean(mean_changes)),
                'max_change_rate': float(np.max(mean_changes)),
                'concentration_stability': float(np.std(mean_concentrations)),
                'spatial_heterogeneity_mean': float(np.mean(std_concentrations))
            }
        else:
            statistics = {
                'initial_mean_concentration': mean_concentrations[0],
                'final_mean_concentration': mean_concentrations[0],
                'total_concentration_change': 0.0,
                'mean_change_rate': 0.0,
                'max_change_rate': 0.0,
                'concentration_stability': 0.0,
                'spatial_heterogeneity_mean': std_concentrations[0]
            }
        
        metadata = {
            'time_points': len(concentration_history),
            'field_shape': concentration_history[0].shape,
            'total_cells': concentration_history[0].size
        }
        
        return AnalysisResult(
            name="concentration_evolution_analysis",
            data={'mean_concentrations': mean_concentrations, 'std_concentrations': std_concentrations},
            statistics=statistics,
            metadata=metadata
        )
    
    def detect_steady_state(self, time_series: List[float], 
                          window_size: int = 10, 
                          tolerance: float = 0.01) -> Dict[str, Any]:
        """Detect when a time series reaches steady state"""
        
        if len(time_series) < window_size:
            return {'steady_state_reached': False, 'steady_state_time': None}
        
        # Calculate rolling statistics
        for i in range(window_size, len(time_series)):
            window = time_series[i-window_size:i]
            window_std = np.std(window)
            window_mean = np.mean(window)
            
            # Check if variation is within tolerance
            if window_std / (window_mean + 1e-10) < tolerance:
                return {
                    'steady_state_reached': True,
                    'steady_state_time': i,
                    'steady_state_value': window_mean,
                    'steady_state_std': window_std
                }
        
        return {'steady_state_reached': False, 'steady_state_time': None}
    
    def calculate_autocorrelation(self, time_series: List[float], max_lag: int = 20) -> Dict[str, Any]:
        """Calculate autocorrelation function for time series"""
        
        if len(time_series) < max_lag:
            max_lag = len(time_series) - 1
        
        # Calculate autocorrelation
        autocorr = []
        for lag in range(max_lag + 1):
            if lag == 0:
                autocorr.append(1.0)
            else:
                corr = np.corrcoef(time_series[:-lag], time_series[lag:])[0, 1]
                autocorr.append(corr if not np.isnan(corr) else 0.0)
        
        return {
            'lags': list(range(max_lag + 1)),
            'autocorrelation': autocorr,
            'decorrelation_time': self._find_decorrelation_time(autocorr)
        }
    
    def _find_decorrelation_time(self, autocorr: List[float], threshold: float = 0.1) -> Optional[int]:
        """Find decorrelation time (when autocorrelation drops below threshold)"""
        for i, corr in enumerate(autocorr):
            if abs(corr) < threshold:
                return i
        return None
