"""Test_GUI proc_summary — generated print-only functions."""

from src.workflow.decorators import register_function


@register_function(
    display_name="Print Counts",
    description="[Test_GUI] print_counts",
    category="FINALIZATION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def print_counts(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/processing/proc_summary/print_counts] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: print_counts fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Print Max Step",
    description="[Test_GUI] print_max_step",
    category="FINALIZATION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def print_max_step(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/processing/proc_summary/print_max_step] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: print_max_step fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Print Final Message",
    description="[Test_GUI] print_final_message",
    category="FINALIZATION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def print_final_message(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/processing/proc_summary/print_final_message] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: print_final_message fired (context keys: {list((context or {}).keys())[:5]})")
    return True
