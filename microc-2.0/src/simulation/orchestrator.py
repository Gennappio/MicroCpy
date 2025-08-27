"""
Multi-timescale orchestration for MicroC 2.0

Coordinates different biological processes running at different timescales.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
import time
import sys
from pathlib import Path

# Add interfaces to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from interfaces.base import ITimescaleOrchestrator
import importlib.util

# Add config to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "config"))
from config.config import TimeConfig

@dataclass
class TimescaleState:
    """Immutable timescale state representation"""
    current_step: int = 0
    current_time: float = 0.0
    last_diffusion_step: int = 0
    last_intracellular_step: int = 0
    last_intercellular_step: int = 0
    total_diffusion_updates: int = 0
    total_intracellular_updates: int = 0
    total_intercellular_updates: int = 0
    
    def with_updates(self, **kwargs) -> 'TimescaleState':
        """Create new TimescaleState with updates (immutable pattern)"""
        updates = {
            'current_step': self.current_step,
            'current_time': self.current_time,
            'last_diffusion_step': self.last_diffusion_step,
            'last_intracellular_step': self.last_intracellular_step,
            'last_intercellular_step': self.last_intercellular_step,
            'total_diffusion_updates': self.total_diffusion_updates,
            'total_intracellular_updates': self.total_intracellular_updates,
            'total_intercellular_updates': self.total_intercellular_updates
        }
        updates.update(kwargs)
        return TimescaleState(**updates)

@dataclass
class ProcessTiming:
    """Timing information for a process"""
    name: str
    interval: int  # Steps between updates
    last_update: int = 0
    total_updates: int = 0
    total_time: float = 0.0
    average_time: float = 0.0
    
    def record_update(self, step: int, duration: float):
        """Record an update for this process"""
        self.last_update = step
        self.total_updates += 1
        self.total_time += duration
        self.average_time = self.total_time / self.total_updates

class TimescaleOrchestrator(ITimescaleOrchestrator):
    """
    Coordinates multi-timescale biological processes
    
    Manages when different processes should be updated based on their
    characteristic timescales and computational requirements.
    """
    
    def __init__(self, time_config: TimeConfig, custom_functions_module=None):

        self.time_config = time_config
        self.custom_functions = self._load_custom_functions(custom_functions_module)

        # Validate that all required timing functions are present
        self._validate_timing_functions()

        # Initialize state
        self.state = TimescaleState()

        # Process timing tracking
        self.process_timings = {
            'diffusion': ProcessTiming('diffusion', time_config.diffusion_step),
            'intracellular': ProcessTiming('intracellular', time_config.intracellular_step),
            'intercellular': ProcessTiming('intercellular', time_config.intercellular_step)
        }
        
        # Adaptive timing parameters
        self.adaptive_timing = True
        self.target_step_time = 0.1  # Target 0.1 seconds per step
        self.timing_history = []
        self.max_history = 100
        
        # Process dependencies
        self.dependencies = {
            'intracellular': [],  # No dependencies
            'diffusion': ['intracellular'],  # Depends on cell reactions
            'intercellular': ['diffusion']  # Depends on substance fields
        }

    def _load_custom_functions(self, custom_functions_module):
        """Load custom functions from module"""
        if custom_functions_module is None:
            return None

        try:
            if isinstance(custom_functions_module, str):
                # Load from file path
                spec = importlib.util.spec_from_file_location("custom_functions", custom_functions_module)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    return module
            else:
                # Already a module
                return custom_functions_module
        except Exception as e:
            print(f"Warning: Could not load custom functions: {e}")
            return None

    def _validate_timing_functions(self):
        """Validate that all required timing functions are present"""
        required_functions = [
            'should_update_diffusion',
            'should_update_intracellular',
            'should_update_intercellular'
        ]

        if not self.custom_functions:
            raise RuntimeError(
                f"[!] Custom functions module is required but not provided!\n"
                f"   The orchestrator requires custom timing functions: {required_functions}\n"
                f"   Please provide a custom functions module with these functions."
            )

        missing_functions = []
        for func_name in required_functions:
            if not hasattr(self.custom_functions, func_name):
                missing_functions.append(func_name)

        if missing_functions:
            raise RuntimeError(
                f"[!] Required timing functions are missing from custom functions module!\n"
                f"   Missing functions: {missing_functions}\n"
                f"   Custom functions module: {self.custom_functions}\n"
                f"   Please ensure your custom functions module defines all required timing functions."
            )

    def should_update_diffusion(self, current_step: int) -> bool:
        """Check if diffusion should be updated this step"""
        if self.custom_functions and hasattr(self.custom_functions, 'should_update_diffusion'):
            # Call custom timing logic
            return self.custom_functions.should_update_diffusion(
                current_step=current_step,
                last_update=self.process_timings['diffusion'].last_update,
                interval=self.process_timings['diffusion'].interval,
                state=self.state.__dict__
            )
        else:
            # Fail explicitly if custom function is not provided
            raise RuntimeError(
                f"[!] Custom timing function 'should_update_diffusion' is required but not found!\n"
                f"   Please ensure your custom functions module defines this function.\n"
                f"   Custom functions module: {self.custom_functions}"
            )
    

    
    def should_update_intracellular(self, current_step: int) -> bool:
        """Check if intracellular processes should be updated"""
        if self.custom_functions and hasattr(self.custom_functions, 'should_update_intracellular'):
            # Call custom timing logic
            return self.custom_functions.should_update_intracellular(
                current_step=current_step,
                last_update=self.process_timings['intracellular'].last_update,
                interval=self.process_timings['intracellular'].interval,
                state=self.state.__dict__
            )
        else:
            # Fail explicitly if custom function is not provided
            raise RuntimeError(
                f"[!] Custom timing function 'should_update_intracellular' is required but not found!\n"
                f"   Please ensure your custom functions module defines this function.\n"
                f"   Custom functions module: {self.custom_functions}"
            )
    

    
    def should_update_intercellular(self, current_step: int) -> bool:
        """Check if intercellular processes should be updated"""
        if self.custom_functions and hasattr(self.custom_functions, 'should_update_intercellular'):
            # Call custom timing logic
            return self.custom_functions.should_update_intercellular(
                current_step=current_step,
                last_update=self.process_timings['intercellular'].last_update,
                interval=self.process_timings['intercellular'].interval,
                state=self.state.__dict__
            )
        else:
            # Fail explicitly if custom function is not provided
            raise RuntimeError(
                f"[!] Custom timing function 'should_update_intercellular' is required but not found!\n"
                f"   Please ensure your custom functions module defines this function.\n"
                f"   Custom functions module: {self.custom_functions}"
            )
    

    
    def step(self, current_step: int) -> Dict[str, bool]:
        """Determine which processes should be updated this step"""
        updates = {}
        
        # Check each process
        updates['intracellular'] = self.should_update_intracellular(current_step)
        updates['diffusion'] = self.should_update_diffusion(current_step)
        updates['intercellular'] = self.should_update_intercellular(current_step)
        
        # Apply dependencies
        if updates['diffusion'] and not updates['intracellular']:
            # If diffusion needs update but intracellular doesn't, force intracellular
            updates['intracellular'] = True
        
        if updates['intercellular'] and not updates['diffusion']:
            # If intercellular needs update but diffusion doesn't, force diffusion
            updates['diffusion'] = True
            if not updates['intracellular']:
                updates['intracellular'] = True
        
        # Update state
        new_time = current_step * self.time_config.dt
        self.state = self.state.with_updates(
            current_step=current_step,
            current_time=new_time
        )
        
        return updates
    
    def record_process_timing(self, process_name: str, duration: float, current_step: int):
        """Record timing for a process"""
        if process_name in self.process_timings:
            self.process_timings[process_name].record_update(current_step, duration)
            
            # Update state counters
            if process_name == 'diffusion':
                self.state = self.state.with_updates(
                    last_diffusion_step=current_step,
                    total_diffusion_updates=self.state.total_diffusion_updates + 1
                )
            elif process_name == 'intracellular':
                self.state = self.state.with_updates(
                    last_intracellular_step=current_step,
                    total_intracellular_updates=self.state.total_intracellular_updates + 1
                )
            elif process_name == 'intercellular':
                self.state = self.state.with_updates(
                    last_intercellular_step=current_step,
                    total_intercellular_updates=self.state.total_intercellular_updates + 1
                )
    
    def adapt_timing(self, total_step_time: float):
        """Adapt timing intervals based on performance"""
        if not self.adaptive_timing:
            return
        
        # Add to history
        self.timing_history.append(total_step_time)
        if len(self.timing_history) > self.max_history:
            self.timing_history.pop(0)
        
        # Calculate average step time
        if len(self.timing_history) >= 10:
            avg_time = sum(self.timing_history[-10:]) / 10
            
            # Adjust intervals if needed
            if avg_time > self.target_step_time * 1.5:
                # Too slow - increase intervals
                for process in self.process_timings.values():
                    process.interval = min(process.interval + 1, 20)
            elif avg_time < self.target_step_time * 0.5:
                # Too fast - decrease intervals
                for process in self.process_timings.values():
                    process.interval = max(process.interval - 1, 1)

    def get_timing_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of process timing information"""
        summary = {}
        for name, timing in self.process_timings.items():
            summary[name] = {
                'interval': timing.interval,
                'total_updates': timing.total_updates,
                'total_time': timing.total_time,
                'average_time': timing.average_time
            }
        return summary
    
    def get_timing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive timing statistics"""
        stats = {
            'current_step': self.state.current_step,
            'current_time': self.state.current_time,
            'processes': {}
        }
        
        for name, timing in self.process_timings.items():
            stats['processes'][name] = {
                'interval': timing.interval,
                'last_update': timing.last_update,
                'total_updates': timing.total_updates,
                'total_time': timing.total_time,
                'average_time': timing.average_time,
                'updates_per_step': timing.total_updates / max(self.state.current_step, 1)
            }
        
        # Overall statistics
        if self.timing_history:
            stats['step_timing'] = {
                'recent_average': sum(self.timing_history[-10:]) / min(len(self.timing_history), 10),
                'overall_average': sum(self.timing_history) / len(self.timing_history),
                'target_time': self.target_step_time,
                'adaptive_timing': self.adaptive_timing
            }
        
        return stats
    
    def reset(self):
        """Reset orchestrator state"""
        self.state = TimescaleState()
        for timing in self.process_timings.values():
            timing.last_update = 0
            timing.total_updates = 0
            timing.total_time = 0.0
            timing.average_time = 0.0
        self.timing_history.clear()
    
    def set_adaptive_timing(self, enabled: bool, target_time: Optional[float] = None):
        """Enable/disable adaptive timing"""
        self.adaptive_timing = enabled
        if target_time is not None:
            self.target_step_time = target_time
    
    def get_state(self) -> TimescaleState:
        """Get current orchestrator state (immutable)"""
        return self.state
    
    def __repr__(self) -> str:
        stats = self.get_timing_statistics()
        return (f"TimescaleOrchestrator(step={stats['current_step']}, "
                f"time={stats['current_time']:.2f}, "
                f"adaptive={self.adaptive_timing})")
