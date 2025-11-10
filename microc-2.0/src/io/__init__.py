"""
Input/Output module for MicroC simulations.

Handles saving and loading of simulation data, including:
- Initial cell states
- Periodic cell state snapshots
- Simulation results
"""

from .initial_state import InitialStateManager

__all__ = ['InitialStateManager']
