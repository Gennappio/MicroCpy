"""Test_GUI prey_graze — generated print-only functions."""

from src.workflow.decorators import register_function


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
)
def prey_forage(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_graze/prey_forage] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_forage fired (context keys: {list((context or {}).keys())[:5]})")
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
)
def prey_chew(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_graze/prey_chew] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_chew fired (context keys: {list((context or {}).keys())[:5]})")
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
)
def prey_swallow(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_graze/prey_swallow] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_swallow fired (context keys: {list((context or {}).keys())[:5]})")
    return True
