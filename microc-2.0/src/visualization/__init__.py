"""
Visualization module for MicroC 2.0

Provides comprehensive plotting and visualization capabilities for:
- Substance concentration fields
- Cell population distributions
- Performance metrics
- Time series analysis
- Multi-panel scientific figures
"""

from .plotter import SimulationPlotter, PlotConfig

# Try to import scipy-dependent modules, but make them optional
try:
    from .analysis import DataAnalyzer, TimeSeriesAnalyzer
    ANALYSIS_AVAILABLE = True
except ImportError:
    ANALYSIS_AVAILABLE = False
    DataAnalyzer = None
    TimeSeriesAnalyzer = None

try:
    from .export import PlotExporter, AnimationExporter
    EXPORT_AVAILABLE = True
except ImportError:
    EXPORT_AVAILABLE = False
    PlotExporter = None
    AnimationExporter = None

__all__ = [
    'SimulationPlotter',
    'PlotConfig'
]

if ANALYSIS_AVAILABLE:
    __all__.extend(['DataAnalyzer', 'TimeSeriesAnalyzer'])

if EXPORT_AVAILABLE:
    __all__.extend(['PlotExporter', 'AnimationExporter'])
