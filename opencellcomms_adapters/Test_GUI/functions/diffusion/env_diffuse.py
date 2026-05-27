"""Test_GUI env_diffuse — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Diffuse Food",
    description="[Test_GUI] diffuse_food",
    category="DIFFUSION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def diffuse_food(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_diffuse/diffuse_food] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: diffuse_food fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Diffuse Oxygen",
    description="[Test_GUI] diffuse_oxygen",
    category="DIFFUSION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def diffuse_oxygen(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_diffuse/diffuse_oxygen] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: diffuse_oxygen fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Log Diffusion",
    description="[Test_GUI] log_diffusion",
    category="DIFFUSION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def log_diffusion(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_diffuse/log_diffusion] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: log_diffusion fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
