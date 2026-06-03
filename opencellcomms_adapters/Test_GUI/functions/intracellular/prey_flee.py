"""Test_GUI prey_flee — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Prey Detect Threat",
    description="[Test_GUI] prey_detect_threat",
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
def prey_detect_threat(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_flee/prey_detect_threat] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_detect_threat fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Prey Sprint",
    description="[Test_GUI] prey_sprint",
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
def prey_sprint(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_flee/prey_sprint] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_sprint fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Prey Hide",
    description="[Test_GUI] prey_hide",
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
def prey_hide(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_flee/prey_hide] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_hide fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
