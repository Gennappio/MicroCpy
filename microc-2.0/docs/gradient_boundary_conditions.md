# Gradient Boundary Conditions in FiPy

This document explains how to implement gradient boundary conditions in your FiPy simulations, moving beyond constant boundary values to create spatial gradients.

## Overview

Previously, the system applied the same boundary value to all faces of the domain:
```python
# Old approach: constant boundaries
var.constrain(boundary_value, mesh.facesTop | mesh.facesBottom | mesh.facesLeft | mesh.facesRight)
```

Now you can create gradients with different values on each face:
- **Left side**: 0
- **Right side**: 1  
- **Top and bottom**: Linear gradients from 0 to 1

## Usage Methods

### Method 1: Linear Gradient 

Set `boundary_type: "linear_gradient"` for the default gradient pattern (0 left, 1 right, gradients top/bottom).

```yaml
# config.yaml
substances:
  TestSubstance:
    diffusion_coeff: 1.0e-9
    boundary_type: "linear_gradient"  # Creates default gradient
    boundary_value: 0.5               # This value is overridden by gradient
```

**Result**: 
- Left boundary = 0
- Right boundary = 1
- Top/bottom boundaries = linear gradient from 0 (left edge) to 1 (right edge)

### Method 2: Custom Gradients

Set `boundary_type: "gradient"` and implement custom boundary functions.

### Method 3: Fixed Boundaries (Original)

Set `boundary_type: "fixed"` for constant values on all boundaries (original behavior).

```yaml
# config.yaml
substances:
  CustomSubstance:
    boundary_type: "gradient"  # Use custom gradient functions
    custom_functions_path: "config/my_custom_functions.py"
```

Then implement the boundary function:

```python
# my_custom_functions.py
def custom_calculate_boundary_conditions(substance_name: str, position: Tuple[float, float], time: float) -> float:
    """
    Parameters:
    - substance_name: Name of the substance
    - position: (x, y) position in meters of the boundary face
    - time: Current time in hours
    
    Returns:
    - Boundary concentration value
    """
    x, y = position
    domain_width = 400e-6  # Your domain width in meters
    
    if substance_name == "CustomSubstance":
        # Example: Sinusoidal gradient
        normalized_x = x / domain_width
        return 0.5 + 0.5 * np.sin(2 * np.pi * normalized_x)
    
    return 0.0  # Default
```

## Available Gradient Patterns

### 1. Linear Gradient (Default)
```python
# Simple linear: 0 at left, 1 at right
normalized_x = x / domain_width
return normalized_x
```

### 2. Sinusoidal Gradient
```python
# Oscillating pattern
normalized_x = x / domain_width
return 0.5 + 0.5 * np.sin(2 * np.pi * normalized_x)
```

### 3. Radial Gradient
```python
# Distance from center
center_x = domain_width / 2
center_y = domain_height / 2
distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
max_distance = np.sqrt(center_x**2 + center_y**2)
return distance / max_distance
```

### 4. Parabolic Gradient
```python
# High at edges, low in center
normalized_x = x / domain_width
return 4 * (normalized_x - 0.5)**2
```

### 5. Step Function
```python
# Discrete levels
normalized_x = x / domain_width
if normalized_x < 0.33:
    return 0.0
elif normalized_x < 0.67:
    return 0.5
else:
    return 1.0
```

### 6. Time-Varying Gradient
```python
# Changes over time
normalized_x = x / domain_width
base_gradient = normalized_x
time_modulation = 0.1 * np.sin(2 * np.pi * time / 12.0)  # 12-hour cycle
return base_gradient + time_modulation
```

## Testing

Run the test script to see gradient boundary conditions in action:

```bash
python test_gradient_boundaries.py
```

This will show:
1. Default gradient visualization
2. Custom gradient patterns
3. Comparison of different boundary patterns

## Implementation Details

### Face-by-Face Application

The gradient system applies boundary conditions face by face:

```python
def _apply_gradient_boundary_conditions(self, var, substance_name, default_boundary_value):
    # Left side: 0
    var.constrain(0.0, self.fipy_mesh.facesLeft)
    
    # Right side: 1  
    var.constrain(1.0, self.fipy_mesh.facesRight)
    
    # Top faces: linear gradient
    for face_id in range(len(self.fipy_mesh.facesTop.value)):
        if self.fipy_mesh.facesTop.value[face_id]:
            face_center_x = self.fipy_mesh.faceCenters[0][face_id]
            normalized_x = face_center_x / domain_width
            var.constrain(normalized_x, where=face_id)
    
    # Bottom faces: same linear gradient
    # ... similar implementation
```

### Custom Function Integration

For `boundary_type: "gradient"`, the system:

1. Calls your `custom_calculate_boundary_conditions()` function for each boundary face
2. Passes the face center coordinates and current time
3. Applies the returned value as a constraint
4. Falls back to default gradient if custom function fails

## Configuration Examples

### Example 1: Simple Test Configuration

```yaml
# gradient_test_config.yaml
domain:
  size_x: 400.0
  size_x_unit: "um"
  size_y: 400.0  
  size_y_unit: "um"
  nx: 20
  ny: 20

substances:
  TestSubstance:
    diffusion_coeff: 1.0e-9
    boundary_type: "fixed"      # Uses default gradient
    initial_value: 0.5
    boundary_value: 0.5         # Overridden by gradient
```

### Example 2: Multiple Custom Gradients

```yaml
# custom_gradients_config.yaml
substances:
  LinearGradient:
    boundary_type: "fixed"      # Default linear gradient
    
  SinusoidalGradient:
    boundary_type: "gradient"   # Custom sinusoidal
    
  RadialGradient:
    boundary_type: "gradient"   # Custom radial
```

## Troubleshooting

### Common Issues

1. **Domain size mismatch**: Ensure your custom function uses the correct domain dimensions
2. **Value range**: Boundary values should typically be in [0, 1] range or physically meaningful
3. **Convergence**: Complex gradients may require more iterations to converge

### Debug Tips

```python
# Add debugging to custom function
def custom_calculate_boundary_conditions(substance_name, position, time):
    x, y = position
    print(f"Debug: {substance_name} at ({x*1e6:.1f}, {y*1e6:.1f}) um")
    
    # Your gradient logic here
    value = calculate_gradient(x, y)
    print(f"       -> boundary value: {value:.3f}")
    return value
```

## Migration from Constant Boundaries

To convert existing simulations:

1. **Keep original behavior**: `boundary_type: "fixed"` still uses constant boundaries (no changes needed)
2. **Add linear gradients**: Change to `boundary_type: "linear_gradient"` for default gradients
3. **Add custom gradients**: Change to `boundary_type: "gradient"` and implement custom functions

The gradient system is fully backward-compatible and doesn't change existing behavior. 