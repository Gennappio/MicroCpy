"""Test_GUI proc_make_plots — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Plot Populations",
    description="[Test_GUI] plot_populations",
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
def plot_populations(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/processing/proc_make_plots/plot_populations] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plot_populations fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plot Environment",
    description="[Test_GUI] plot_environment",
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
def plot_environment(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/processing/proc_make_plots/plot_environment] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plot_environment fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Plot Interactions",
    description="[Test_GUI] plot_interactions",
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
def plot_interactions(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/processing/proc_make_plots/plot_interactions] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: plot_interactions fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
