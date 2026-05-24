"""Test_GUI predator_init — generated print-only functions."""

from src.workflow.decorators import register_function


@register_function(
    display_name="Predator Spawn",
    description="[Test_GUI] predator_spawn",
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
def predator_spawn(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/predator/predator_init/predator_spawn] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: predator_spawn fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Predator Set Energy",
    description="[Test_GUI] predator_set_energy",
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
def predator_set_energy(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/predator/predator_init/predator_set_energy] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: predator_set_energy fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Predator Log Init",
    description="[Test_GUI] predator_log_init",
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
def predator_log_init(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/predator/predator_init/predator_log_init] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: predator_log_init fired (context keys: {list((context or {}).keys())[:5]})")
    return True
