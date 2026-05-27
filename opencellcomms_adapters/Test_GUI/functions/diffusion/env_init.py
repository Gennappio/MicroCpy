"""Test_GUI env_init — generated print-only functions."""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="Setup Test Domain",
    description="[Test_GUI] setup_test_domain",
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
def setup_test_domain(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_init/setup_test_domain] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: setup_test_domain fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Setup Test Substances",
    description="[Test_GUI] setup_test_substances",
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
def setup_test_substances(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_init/setup_test_substances] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: setup_test_substances fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True

@register_function(
    display_name="Log Env Ready",
    description="[Test_GUI] log_env_ready",
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
def log_env_ready(env: BiologicalContext = None, intensity=1.0, verbose=False, **kwargs):
    step = (env.raw_context if env else {}).get('current_step', '?')
    print(f"[Test_GUI/environment/env_init/log_env_ready] step={step} intensity={intensity}")
    if verbose:
        print(f"  -> verbose: log_env_ready fired (context keys: {list((env.raw_context if env else {}).keys())[:5]})")
    return True
