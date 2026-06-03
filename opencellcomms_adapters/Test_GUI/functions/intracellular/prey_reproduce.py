"""Test_GUI prey_reproduce — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Prey Pair",
    description="[Test_GUI] prey_pair",
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
def prey_pair(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_reproduce/prey_pair] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_pair fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Prey Nest",
    description="[Test_GUI] prey_nest",
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
def prey_nest(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_reproduce/prey_nest] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_nest fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Prey Hatch",
    description="[Test_GUI] prey_hatch",
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
def prey_hatch(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_reproduce/prey_hatch] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_hatch fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
