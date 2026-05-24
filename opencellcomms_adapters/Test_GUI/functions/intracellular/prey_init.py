"""Test_GUI prey_init — generated print-only functions."""

from src.workflow.decorators import register_function


@register_function(
    display_name="Prey Spawn",
    description="[Test_GUI] prey_spawn",
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
def prey_spawn(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_init/prey_spawn] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_spawn fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Prey Set State",
    description="[Test_GUI] prey_set_state",
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
def prey_set_state(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_init/prey_set_state] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_set_state fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Prey Log Init",
    description="[Test_GUI] prey_log_init",
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
def prey_log_init(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/prey/prey_init/prey_log_init] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: prey_log_init fired (context keys: {list((context or {}).keys())[:5]})")
    return True
