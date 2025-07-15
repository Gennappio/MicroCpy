"""
Hook system for MicroC 2.0 - Enables customization without code modification

This module provides a flexible hook system that allows users to customize
behavior by providing custom functions without modifying the core codebase.
"""

from typing import Dict, Callable, Any, Optional, List
from dataclasses import dataclass
import importlib.util
from pathlib import Path

@dataclass
class HookDefinition:
    """Definition of a customization hook"""
    name: str
    description: str
    parameters: Dict[str, type]
    return_type: type
    default_implementation: Optional[Callable] = None

class HookRegistry:
    """Registry for all available hooks in the system"""
    
    def __init__(self):
        self.hooks: Dict[str, HookDefinition] = {}
        self._register_core_hooks()
    
    def register_hook(self, hook: HookDefinition):
        """Register a new hook"""
        self.hooks[hook.name] = hook
    
    def get_hook(self, name: str) -> Optional[HookDefinition]:
        """Get hook definition by name"""
        return self.hooks.get(name)
    
    def list_hooks(self) -> List[str]:
        """List all available hook names"""
        return list(self.hooks.keys())
    
    def _register_core_hooks(self):
        """Register core hooks used throughout the system"""
        
        # Cell behavior hooks
        self.register_hook(HookDefinition(
            name="custom_calculate_cell_metabolism",
            description="Calculate metabolic rates for a cell",
            parameters={"local_environment": dict, "cell_state": dict},
            return_type=dict
        ))

        self.register_hook(HookDefinition(
            name="custom_update_cell_phenotype",
            description="Update cell phenotype based on environment and genes",
            parameters={"local_environment": dict, "gene_states": dict, "current_phenotype": str},
            return_type=str
        ))

        self.register_hook(HookDefinition(
            name="custom_check_cell_death",
            description="Determine if cell should die",
            parameters={"cell_state": dict, "local_environment": dict},
            return_type=bool
        ))

        self.register_hook(HookDefinition(
            name="custom_should_divide",
            description="Determine if cell should divide (alternative interface)",
            parameters={"cell": object, "config": dict},
            return_type=bool
        ))
        
        # Gene network hooks
        self.register_hook(HookDefinition(
            name="custom_update_gene_network",
            description="Custom gene network update logic",
            parameters={"current_states": dict, "inputs": dict, "network_params": dict},
            return_type=dict
        ))

        # Substance simulation hooks
        self.register_hook(HookDefinition(
            name="custom_calculate_boundary_conditions",
            description="Calculate custom boundary conditions",
            parameters={"substance_name": str, "position": tuple, "time": float},
            return_type=float
        ))
        
        # Population dynamics hooks
        self.register_hook(HookDefinition(
            name="custom_initialize_cell_placement",
            description="Define initial cell placement pattern",
            parameters={"grid_size": tuple, "simulation_params": dict},
            return_type=list
        ))

        self.register_hook(HookDefinition(
            name="custom_select_division_direction",
            description="Select direction for cell division",
            parameters={"parent_position": tuple, "available_positions": list},
            return_type=tuple
        ))

        self.register_hook(HookDefinition(
            name="custom_calculate_migration_probability",
            description="Calculate probability of cell migration",
            parameters={"cell_state": dict, "local_environment": dict, "target_position": tuple},
            return_type=float
        ))

        # Additional hooks for Jayatilake experiment
        self.register_hook(HookDefinition(
            name="custom_get_substance_reactions",
            description="Calculate substance consumption/production rates for a cell",
            parameters={"cell": object, "local_env": dict, "gene_states": dict, "config": object},
            return_type=dict
        ))

        self.register_hook(HookDefinition(
            name="custom_get_cell_color",
            description="Get cell color for visualization",
            parameters={"cell": object, "gene_states": dict, "config": object},
            return_type=str
        ))

        self.register_hook(HookDefinition(
            name="custom_get_population_substance_reactions",
            description="Get substance reactions for entire population",
            parameters={"population": object, "config": object},
            return_type=dict
        ))

        # Timing orchestration hooks
        self.register_hook(HookDefinition(
            name="custom_should_update_diffusion",
            description="Determine if diffusion should be updated this step",
            parameters={"current_step": int, "last_update": int, "interval": int, "state": dict},
            return_type=bool
        ))

        self.register_hook(HookDefinition(
            name="custom_should_update_intracellular",
            description="Determine if intracellular processes should be updated this step",
            parameters={"current_step": int, "last_update": int, "interval": int, "state": dict},
            return_type=bool
        ))

        self.register_hook(HookDefinition(
            name="custom_should_update_intercellular",
            description="Determine if intercellular processes should be updated this step",
            parameters={"current_step": int, "last_update": int, "interval": int, "state": dict},
            return_type=bool
        ))

        # Performance monitoring hooks
        self.register_hook(HookDefinition(
            name="custom_capture_custom_metrics",
            description="Capture custom performance metrics",
            parameters={"monitor": object, "timestamp": float},
            return_type=dict
        ))

        self.register_hook(HookDefinition(
            name="custom_handle_performance_alert",
            description="Handle performance alerts",
            parameters={"alert": dict},
            return_type=None
        ))

class CustomFunctionLoader:
    """Loads and manages custom functions from user-provided modules"""
    
    def __init__(self, custom_functions_path: Optional[Path] = None):
        self.custom_functions_path = custom_functions_path
        self.custom_functions: Dict[str, Callable] = {}
        self.hook_registry = HookRegistry()
        self._auto_load_attempted = False

        if custom_functions_path and custom_functions_path.exists():
            self._load_custom_functions()
        elif custom_functions_path is None:
            # Try auto-loading from config folder
            self._try_auto_load()

    def _try_auto_load(self):
        """Try to automatically load custom_functions.py from config folder"""
        if self._auto_load_attempted:
            return

        self._auto_load_attempted = True

        # Try to find config/custom_functions.py
        possible_paths = [
            Path("config/custom_functions.py"),
            Path("../config/custom_functions.py"),
            Path("microc-2.0/config/custom_functions.py"),
            Path("./config/custom_functions.py")
        ]

        for path in possible_paths:
            if path.exists():
                try:
                    self.custom_functions_path = path
                    self._load_custom_functions()
                    print(f"✅ Auto-loaded custom functions from {path}")
                    return
                except Exception as e:
                    print(f"⚠️  Failed to auto-load from {path}: {e}")

        # If no custom functions found, that's okay
        print("ℹ️  No custom_functions.py found in config folder (using defaults)")

    def _load_custom_functions(self):
        """Load custom functions from the specified module"""
        try:
            spec = importlib.util.spec_from_file_location(
                "custom_functions", 
                self.custom_functions_path
            )
            if spec and spec.loader:
                custom_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(custom_module)
                
                # Extract functions that match hook names exactly
                for hook_name in self.hook_registry.list_hooks():
                    if hasattr(custom_module, hook_name):
                        self.custom_functions[hook_name] = getattr(custom_module, hook_name)
                        print(f"✅ Loaded custom function: {hook_name}")
                        
        except Exception as e:
            print(f"Warning: Could not load custom functions: {e}")
    
    def get_function(self, hook_name: str) -> Optional[Callable]:
        """Get custom function for a hook, if available"""
        # Try auto-loading if not done yet
        if not self._auto_load_attempted and self.custom_functions_path is None:
            self._try_auto_load()

        return self.custom_functions.get(hook_name)
    
    def has_custom_function(self, hook_name: str) -> bool:
        """Check if custom function is available for hook"""
        return hook_name in self.custom_functions

class HookManager:
    """Manages hook execution with fallback to defaults"""
    
    def __init__(self, custom_functions_loader: Optional[CustomFunctionLoader] = None):
        self.loader = custom_functions_loader or CustomFunctionLoader()
        self.hook_registry = HookRegistry()
    
    def call_hook(self, hook_name: str, *args, **kwargs) -> Any:
        """Call a hook with custom function if available, otherwise use default"""
        
        # Check if hook is registered
        hook_def = self.hook_registry.get_hook(hook_name)
        if not hook_def:
            raise ValueError(f"Unknown hook: {hook_name}")
        
        # Try custom function first
        custom_func = self.loader.get_function(hook_name)
        if custom_func:
            try:
                return custom_func(*args, **kwargs)
            except Exception as e:
                print(f"Warning: Custom function {hook_name} failed: {e}")
                print("Falling back to default implementation")
        
        # Fall back to default implementation
        if hook_def.default_implementation:
            return hook_def.default_implementation(*args, **kwargs)
        else:
            raise NotImplementedError(f"No implementation available for hook: {hook_name}")
    
    def list_available_hooks(self) -> Dict[str, str]:
        """List all available hooks with descriptions"""
        return {name: hook.description for name, hook in self.hook_registry.hooks.items()}
    
    def get_hook_signature(self, hook_name: str) -> Optional[Dict[str, Any]]:
        """Get the signature information for a hook"""
        hook_def = self.hook_registry.get_hook(hook_name)
        if hook_def:
            return {
                "parameters": hook_def.parameters,
                "return_type": hook_def.return_type,
                "description": hook_def.description
            }
        return None

# Global hook manager instance
_global_hook_manager: Optional[HookManager] = None

def get_hook_manager() -> HookManager:
    """Get the global hook manager instance"""
    global _global_hook_manager
    if _global_hook_manager is None:
        _global_hook_manager = HookManager()
    return _global_hook_manager

def set_custom_functions_path(path):
    """Set the path to custom functions module"""
    global _global_hook_manager
    from pathlib import Path

    # Convert string to Path if needed
    if isinstance(path, str):
        path = Path(path)

    loader = CustomFunctionLoader(path)
    _global_hook_manager = HookManager(loader)

def call_hook(hook_name: str, *args, **kwargs) -> Any:
    """Convenience function to call a hook"""
    return get_hook_manager().call_hook(hook_name, *args, **kwargs)
