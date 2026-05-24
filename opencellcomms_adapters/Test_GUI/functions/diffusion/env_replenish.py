"""Test_GUI env_replenish — generated print-only functions."""

from src.workflow.decorators import register_function


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
)
def refill_food(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_replenish/refill_food] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: refill_food fired (context keys: {list((context or {}).keys())[:5]})")
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
)
def refill_oxygen(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_replenish/refill_oxygen] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: refill_oxygen fired (context keys: {list((context or {}).keys())[:5]})")
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
)
def log_replenish(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_replenish/log_replenish] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: log_replenish fired (context keys: {list((context or {}).keys())[:5]})")
    return True
