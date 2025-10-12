"""
Custom gradient boundary conditions for testing
Demonstrates various gradient patterns
"""

import numpy as np
from typing import Tuple

def custom_calculate_boundary_conditions(substance_name: str, position: Tuple[float, float], time: float) -> float:
    """
    Custom gradient boundary conditions
    
    Parameters:
    - substance_name: Name of the substance
    - position: (x, y) position in meters of the boundary face
    - time: Current time in hours
    
    Returns:
    - Boundary concentration value
    """
    x, y = position
    
    if substance_name == "CustomGradientSubstance":
        # Example 1: Simple linear gradient (0 at left, 1 at right)
        # Assuming domain is 400 um = 400e-6 m wide
        domain_width = 400e-6  # meters
        normalized_x = x / domain_width
        return normalized_x
        
    elif substance_name == "RadialGradient":
        # Example 2: Radial gradient from center
        domain_width = 400e-6
        domain_height = 400e-6
        center_x = domain_width / 2
        center_y = domain_height / 2
        
        # Distance from center
        distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        max_distance = np.sqrt(center_x**2 + center_y**2)
        
        # Normalize to [0,1]
        normalized_distance = min(distance / max_distance, 1.0)
        return normalized_distance
        
    elif substance_name == "SinusoidalGradient":
        # Example 3: Sinusoidal gradient
        domain_width = 400e-6
        normalized_x = x / domain_width
        
        # Sinusoidal pattern
        gradient_value = 0.5 + 0.5 * np.sin(2 * np.pi * normalized_x)
        return gradient_value
        
    elif substance_name == "ParabolicGradient":
        # Example 4: Parabolic gradient (high at edges, low in center)
        domain_width = 400e-6
        normalized_x = x / domain_width
        
        # Parabolic: ax^2 + bx + c where minimum is at x=0.5
        # f(0) = 1, f(0.5) = 0, f(1) = 1
        gradient_value = 4 * (normalized_x - 0.5)**2
        return gradient_value
        
    elif substance_name == "StepGradient":
        # Example 5: Step function gradient
        domain_width = 400e-6
        normalized_x = x / domain_width
        
        if normalized_x < 0.33:
            return 0.0
        elif normalized_x < 0.67:
            return 0.5
        else:
            return 1.0
            
    elif substance_name == "TimeVaryingGradient":
        # Example 6: Time-varying gradient
        domain_width = 400e-6
        normalized_x = x / domain_width
        
        # Base gradient with time modulation
        base_gradient = normalized_x
        time_modulation = 0.1 * np.sin(2 * np.pi * time / 12.0)  # 12-hour cycle
        return base_gradient + time_modulation
        
    else:
        # Default: simple linear gradient for any other substance
        domain_width = 400e-6
        normalized_x = x / domain_width
        return normalized_x


def apply_boundary_conditions(mesh, substance_config):
    """
    Override boundary condition type for specific substances
    """
    if substance_config.name in ["RadialGradient", "SinusoidalGradient", 
                               "ParabolicGradient", "StepGradient", "TimeVaryingGradient"]:
        return "gradient"  # Use custom gradient
    else:
        return None  # Use default from config 