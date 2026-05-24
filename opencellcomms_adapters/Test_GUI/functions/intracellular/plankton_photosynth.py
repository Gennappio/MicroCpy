"""Test_GUI plankton_photosynth — generated print-only functions."""

from src.workflow.decorators import register_function


@register_function(
    display_name="Plankton Capture",
    description="[Test_GUI] plankton_capture",
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
def plankton_capture(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_photosynth/plankton_capture] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_capture fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plankton Convert",
    description="[Test_GUI] plankton_convert",
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
def plankton_convert(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_photosynth/plankton_convert] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_convert fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plankton Store",
    description="[Test_GUI] plankton_store",
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
def plankton_store(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_photosynth/plankton_store] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_store fired (context keys: {list((context or {}).keys())[:5]})")
    return True
