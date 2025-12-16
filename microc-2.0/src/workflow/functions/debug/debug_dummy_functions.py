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

