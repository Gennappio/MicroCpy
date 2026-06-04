"""Test_GUI env_replenish — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Refill Food",
    description="[Test_GUI] refill_food",
    category="DIFFUSION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    requires=['simulator'],
)
def refill_food(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_replenish/refill_food] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: refill_food fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Refill Oxygen",
    description="[Test_GUI] refill_oxygen",
    category="DIFFUSION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    requires=['simulator'],
)
def refill_oxygen(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_replenish/refill_oxygen] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: refill_oxygen fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Log Replenish",
    description="[Test_GUI] log_replenish",
    category="DIFFUSION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    requires=['simulator'],
)
def log_replenish(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_replenish/log_replenish] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: log_replenish fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
