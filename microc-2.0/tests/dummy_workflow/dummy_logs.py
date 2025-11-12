"""
Simple logging functions for workflow testing.

Each function just prints its name and parameters to validate
that the workflow system is working correctly.
"""


def init_function(context, param1=10, param2=5.5, param3="test"):
    """Initialization function - just logs name and parameters."""
    print(f">>> init_function called")
    print(f"    param1 = {param1}")
    print(f"    param2 = {param2}")
    print(f"    param3 = {param3}")
    return True


def metabolism_function(context, rate=1.0, threshold=0.5, enabled=True):
    """Metabolism function - just logs name and parameters."""
    print(f">>> metabolism_function called")
    print(f"    rate = {rate}")
    print(f"    threshold = {threshold}")
    print(f"    enabled = {enabled}")
    return True


def division_function(context, min_size=100, max_rate=0.8):
    """Division function - just logs name and parameters."""
    print(f">>> division_function called")
    print(f"    min_size = {min_size}")
    print(f"    max_rate = {max_rate}")
    return True


def diffusion_function(context, coefficient=0.1, decay=0.01):
    """Diffusion function - just logs name and parameters."""
    print(f">>> diffusion_function called")
    print(f"    coefficient = {coefficient}")
    print(f"    decay = {decay}")
    return True


def signaling_function(context, range_value=10.0, strength=1.0):
    """Signaling function - just logs name and parameters."""
    print(f">>> signaling_function called")
    print(f"    range_value = {range_value}")
    print(f"    strength = {strength}")
    return True


def export_function(context, format_type="csv", compress=False):
    """Export function - just logs name and parameters."""
    print(f">>> export_function called")
    print(f"    format_type = {format_type}")
    print(f"    compress = {compress}")
    return True

