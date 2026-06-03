"""Test_GUI plankton_drift — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Plankton Brownian",
    description="[Test_GUI] plankton_brownian",
    category="INTRACELLULAR",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    requires=['population'],
)
def plankton_brownian(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_drift/plankton_brownian] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_brownian fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plankton Current",
    description="[Test_GUI] plankton_current",
    category="INTRACELLULAR",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    requires=['population'],
)
def plankton_current(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_drift/plankton_current] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_current fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plankton Tide",
    description="[Test_GUI] plankton_tide",
    category="INTRACELLULAR",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    requires=['population'],
)
def plankton_tide(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_drift/plankton_tide] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_tide fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
