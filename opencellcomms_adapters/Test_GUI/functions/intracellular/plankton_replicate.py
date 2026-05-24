"""Test_GUI plankton_replicate — generated print-only functions."""

from src.workflow.decorators import register_function


@register_function(
    display_name="Plankton Divide",
    description="[Test_GUI] plankton_divide",
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
def plankton_divide(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_replicate/plankton_divide] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_divide fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plankton Scatter",
    description="[Test_GUI] plankton_scatter",
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
def plankton_scatter(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_replicate/plankton_scatter] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_scatter fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plankton Settle",
    description="[Test_GUI] plankton_settle",
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
def plankton_settle(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/plankton/plankton_replicate/plankton_settle] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plankton_settle fired (context keys: {list((context or {}).keys())[:5]})")
    return True
