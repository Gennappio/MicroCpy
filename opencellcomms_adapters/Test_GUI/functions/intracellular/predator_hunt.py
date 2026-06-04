"""Test_GUI predator_hunt — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Predator Stalk",
    description="[Test_GUI] predator_stalk",
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
def predator_stalk(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/predator/predator_hunt/predator_stalk] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: predator_stalk fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Predator Strike",
    description="[Test_GUI] predator_strike",
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
def predator_strike(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/predator/predator_hunt/predator_strike] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: predator_strike fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Predator Digest",
    description="[Test_GUI] predator_digest",
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
def predator_digest(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/predator/predator_hunt/predator_digest] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: predator_digest fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
