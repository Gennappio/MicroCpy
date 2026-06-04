"""Test_GUI proc_export_csv — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Write Predators Csv",
    description="[Test_GUI] write_predators_csv",
    category="FINALIZATION",
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
def write_predators_csv(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/processing/proc_export_csv/write_predators_csv] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: write_predators_csv fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Write Prey Csv",
    description="[Test_GUI] write_prey_csv",
    category="FINALIZATION",
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
def write_prey_csv(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/processing/proc_export_csv/write_prey_csv] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: write_prey_csv fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Write Plankton Csv",
    description="[Test_GUI] write_plankton_csv",
    category="FINALIZATION",
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
def write_plankton_csv(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/processing/proc_export_csv/write_plankton_csv] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: write_plankton_csv fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
