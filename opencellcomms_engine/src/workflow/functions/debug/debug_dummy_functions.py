"""Dummy debug workflow functions.

Each function:
- Prints its own name and the stage it belongs to
- Uses an optional "message" parameter (typically coming from a
  connected parameter node)
- Appends the final message to context["debug_workflow_log"] if a
  context dict is provided.

These functions are safe no-ops from the simulation point of view and
are intended only for debugging the workflow wiring.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from src.workflow.decorators import register_function


def _log_debug(stage: str, function_name: str, context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    """Common helper used by all debug functions.

    Parameters
    ----------
    stage: str
        Workflow stage name (e.g. "initialization").
    function_name: str
        Name of the debug function.
    context: dict, optional
        Global workflow context, if provided by the executor.
    message: str
        Optional message coming from parameters / parameter nodes.
    """
    base = message or f"[DEBUG WORKFLOW] stage='{stage}', function='{function_name}'"

    # Include step information if available in context
    if isinstance(context, dict) and "current_step" in context:
        base = f"{base}, step={context['current_step']}"

    print(base)

    # Store in a simple log list on the context for later inspection
    if isinstance(context, dict):
        log = context.setdefault("debug_workflow_log", [])
        log.append(base)

    # Always return True so the executor can treat it as success
    return True


# =====================================================================
# INITIALIZATION STAGE DEBUG FUNCTIONS
# =====================================================================


@register_function(
    display_name="Debug Initialization 1",
    description="Debug function for initialization stage (prints message)",
    category="INITIALIZATION",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_initialization_1(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("initialization", "debug_initialization_1", context, message, **kwargs)


@register_function(
    display_name="Debug Initialization 2",
    description="Debug function for initialization stage (prints message)",
    category="INITIALIZATION",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_initialization_2(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("initialization", "debug_initialization_2", context, message, **kwargs)


@register_function(
    display_name="Debug Initialization 3",
    description="Debug function for initialization stage (prints message)",
    category="INITIALIZATION",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    outputs=[],
    cloneable=True
)
def debug_initialization_3(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("initialization", "debug_initialization_3", context, message, **kwargs)


# =====================================================================
# INTRACELLULAR STAGE DEBUG FUNCTIONS
# =====================================================================


@register_function(
    display_name="Debug Intracellular 1",
    description="Debug function for intracellular stage (prints message)",
    category="INTRACELLULAR",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_intracellular_1(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("intracellular", "debug_intracellular_1", context, message, **kwargs)


@register_function(
    display_name="Debug Intracellular 2",
    description="Debug function for intracellular stage (prints message)",
    category="INTRACELLULAR",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_intracellular_2(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("intracellular", "debug_intracellular_2", context, message, **kwargs)


@register_function(
    display_name="Debug Intracellular 3",
    description="Debug function for intracellular stage (prints message)",
    category="INTRACELLULAR",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_intracellular_3(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("intracellular", "debug_intracellular_3", context, message, **kwargs)


# =====================================================================
# MICROENVIRONMENT (DIFFUSION) STAGE DEBUG FUNCTIONS
# =====================================================================


@register_function(
    display_name="Debug Microenvironment 1",
    description="Debug function for microenvironment stage (prints message)",
    category="DIFFUSION",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_microenvironment_1(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("microenvironment", "debug_microenvironment_1", context, message, **kwargs)


@register_function(
    display_name="Debug Microenvironment 2",
    description="Debug function for microenvironment stage (prints message)",
    category="DIFFUSION",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_microenvironment_2(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("microenvironment", "debug_microenvironment_2", context, message, **kwargs)


@register_function(
    display_name="Debug Microenvironment 3",
    description="Debug function for microenvironment stage (prints message)",
    category="DIFFUSION",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_microenvironment_3(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("microenvironment", "debug_microenvironment_3", context, message, **kwargs)


# =====================================================================
# INTERCELLULAR STAGE DEBUG FUNCTIONS
# =====================================================================


@register_function(
    display_name="Debug Intercellular 1",
    description="Debug function for intercellular stage (prints message)",
    category="INTERCELLULAR",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_intercellular_1(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("intercellular", "debug_intercellular_1", context, message, **kwargs)


@register_function(
    display_name="Debug Intercellular 2",
    description="Debug function for intercellular stage (prints message)",
    category="INTERCELLULAR",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_intercellular_2(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("intercellular", "debug_intercellular_2", context, message, **kwargs)


@register_function(
    display_name="Debug Intercellular 3",
    description="Debug function for intercellular stage (prints message)",
    category="INTERCELLULAR",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_intercellular_3(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("intercellular", "debug_intercellular_3", context, message, **kwargs)


# =====================================================================
# FINALIZATION STAGE DEBUG FUNCTIONS
# =====================================================================


@register_function(
    display_name="Debug Finalization 1",
    description="Debug function for finalization stage (prints message)",
    category="FINALIZATION",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_finalization_1(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("finalization", "debug_finalization_1", context, message, **kwargs)


@register_function(
    display_name="Debug Finalization 2",
    description="Debug function for finalization stage (prints message)",
    category="FINALIZATION",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_finalization_2(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("finalization", "debug_finalization_2", context, message, **kwargs)


@register_function(
    display_name="Debug Finalization 3",
    description="Debug function for finalization stage (prints message)",
    category="FINALIZATION",
    parameters=[{"name": "message", "type": "STRING", "description": "Debug message", "default": ""}],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_finalization_3(context: Optional[Dict[str, Any]] = None, message: str = "", **kwargs: Any) -> bool:
    return _log_debug("finalization", "debug_finalization_3", context, message, **kwargs)


# =====================================================================
# DEBUG IMAGE GENERATION FUNCTION
# =====================================================================


@register_function(
    display_name="Debug Generate Image",
    description="Generate a test image with current date/time and optional message. Useful for testing the results viewer.",
    category="FINALIZATION",
    parameters=[
        {"name": "message", "type": "STRING", "description": "Optional message to display on image", "default": "Test Image"},
        {"name": "filename", "type": "STRING", "description": "Output filename (without extension)", "default": "debug_plot"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=True
)
def debug_generate_image(context: Optional[Dict[str, Any]] = None, message: str = "Test Image", filename: str = "debug_plot", **kwargs: Any) -> bool:
    """Generate a test image with timestamp for results viewer testing.

    Creates a simple plot with:
    - Current date and time
    - Step number (if available)
    - Random data visualization
    - Custom message
    """
    import datetime
    from pathlib import Path

    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as e:
        print(f"[DEBUG GENERATE IMAGE] Missing dependency: {e}")
        return False

    # Get step info
    step = 0
    if isinstance(context, dict):
        step = context.get("current_step", 0)

    # Generate timestamp - MUST be fresh on each call
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # millisecond precision
    timestamp_short = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # for filename

    # Debug: Print timestamp to verify it's updating
    print(f"[DEBUG GENERATE IMAGE] Timestamp: {timestamp}")

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Generate random data that changes each time
    np.random.seed(int(now.timestamp() * 1000) % (2**31))
    x = np.linspace(0, 10, 100)
    y = np.sin(x + step * 0.5) + np.random.normal(0, 0.1, 100)

    # Plot
    ax.plot(x, y, 'b-', linewidth=2, label='Signal')
    ax.fill_between(x, y - 0.3, y + 0.3, alpha=0.2, color='blue')

    # Add some random scatter points
    scatter_x = np.random.uniform(0, 10, 20)
    scatter_y = np.sin(scatter_x + step * 0.5) + np.random.normal(0, 0.3, 20)
    ax.scatter(scatter_x, scatter_y, c='red', s=50, alpha=0.6, label='Data points')

    # Title and labels
    ax.set_title(f"{message}\nStep: {step}", fontsize=16, fontweight='bold')
    ax.set_xlabel('X Value', fontsize=12)
    ax.set_ylabel('Y Value', fontsize=12)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # Add timestamp text box
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.98, f"Generated: {timestamp}", transform=ax.transAxes,
            fontsize=10, verticalalignment='top', bbox=props, family='monospace')

    # Determine output path - use subworkflow_results_dir if available (v2.0)
    output_dir = Path("results")
    if isinstance(context, dict):
        # v2.0 spec: use subworkflow_results_dir from context
        if "subworkflow_results_dir" in context:
            output_dir = Path(context["subworkflow_results_dir"])
        elif "config" in context:
            config = context["config"]
            if hasattr(config, 'output_dir'):
                output_dir = Path(config.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save with timestamp and step number in filename to prevent overwriting
    # Format: {filename}_{timestamp}_step_{step}.png
    # Example: processing_plot_20260116_151345_123_step_0000.png
    out_filename = f"{filename}_{timestamp_short}_step_{step:04d}.png"
    filepath = output_dir / out_filename
    fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    print(f"[DEBUG GENERATE IMAGE] Saved: {filepath}")

    # Also log to context
    if isinstance(context, dict):
        log = context.setdefault("debug_workflow_log", [])
        log.append(f"[DEBUG GENERATE IMAGE] Created {filepath} at {timestamp}")

    return True
