"""Test_GUI plankton_init — generated print-only functions."""

from src.workflow.decorators import register_function


@register_function(
    display_name="Plankton Spawn",
    description="[Test_GUI] plankton_spawn",
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
def plankton_spawn(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_init/plankton_spawn] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_spawn fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plankton Set State",
    description="[Test_GUI] plankton_set_state",
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
def plankton_set_state(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_init/plankton_set_state] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_set_state fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plankton Log Init",
    description="[Test_GUI] plankton_log_init",
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
def plankton_log_init(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_init/plankton_log_init] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_log_init fired (context keys: {list((context or {}).keys())[:5]})")
    return True
