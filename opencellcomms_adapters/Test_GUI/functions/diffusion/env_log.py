"""Test_GUI env_log — generated print-only functions."""

from src.workflow.decorators import register_function


@register_function(
    display_name="Snapshot State",
    description="[Test_GUI] snapshot_state",
    category="DIFFUSION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def snapshot_state(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_log/snapshot_state] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: snapshot_state fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Dump Grid",
    description="[Test_GUI] dump_grid",
    category="DIFFUSION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def dump_grid(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_log/dump_grid] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: dump_grid fired (context keys: {list((context or {}).keys())[:5]})")
    return True

@register_function(
    display_name="Log Env Step",
    description="[Test_GUI] log_env_step",
    category="DIFFUSION",
    parameters=[
        {"name": "intensity", "type": "FLOAT", "description": "arbitrary intensity (test)",
         "default": 1.0, "min_value": 0.0, "max_value": 10.0},
        {"name": "verbose", "type": "BOOL", "description": "extra logging", "default": False},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def log_env_step(context=None, intensity=1.0, verbose=False, **kwargs):
    step = (context or {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_log/log_env_step] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: log_env_step fired (context keys: {list((context or {}).keys())[:5]})")
    return True
