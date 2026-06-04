"""Test_GUI prey_graze — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Prey Forage",
    description="[Test_GUI] prey_forage",
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
def prey_forage(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_graze/prey_forage] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_forage fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Prey Chew",
    description="[Test_GUI] prey_chew",
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
def prey_chew(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_graze/prey_chew] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_chew fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Prey Swallow",
    description="[Test_GUI] prey_swallow",
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
def prey_swallow(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_graze/prey_swallow] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_swallow fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
