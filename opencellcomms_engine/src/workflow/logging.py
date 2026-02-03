"""
Centralized logging utility for workflow functions.

This module provides a consistent logging interface for workflow functions
with support for global and per-node verbosity control.
"""

from typing import Dict, Any, Optional


def should_log(context: Dict[str, Any], node_verbose: Optional[bool] = None) -> bool:
    """
    Determine if logging should be enabled based on context and node settings.
    
    Args:
        context: Workflow context dictionary
        node_verbose: Per-node verbose setting (None = use global setting)
        
    Returns:
        True if logging should be enabled, False otherwise
    """
    # Per-node override takes precedence
    if node_verbose is not None:
        return node_verbose
    
    # Otherwise use global context setting (default: False)
    return context.get('verbose', False)


def log(context: Dict[str, Any], message: str, 
        prefix: str = "", node_verbose: Optional[bool] = None) -> None:
    """
    Log a message if logging is enabled.
    
    Args:
        context: Workflow context dictionary
        message: Message to log
        prefix: Prefix for the message (e.g., "[COUPLED]")
        node_verbose: Per-node verbose setting (None = use global setting)
    """
    if should_log(context, node_verbose):
        if prefix:
            print(f"{prefix} {message}")
        else:
            print(message)


def log_debug(context: Dict[str, Any], message: str, 
              prefix: str = "", node_verbose: Optional[bool] = None) -> None:
    """
    Log a debug message (alias for log).
    
    Args:
        context: Workflow context dictionary
        message: Message to log
        prefix: Prefix for the message (e.g., "[DEBUG]")
        node_verbose: Per-node verbose setting (None = use global setting)
    """
    log(context, message, prefix, node_verbose)


def log_always(message: str, prefix: str = "") -> None:
    """
    Always log a message regardless of verbosity settings.
    Use for critical information, errors, or warnings.
    
    Args:
        message: Message to log
        prefix: Prefix for the message (e.g., "[ERROR]")
    """
    if prefix:
        print(f"{prefix} {message}")
    else:
        print(message)

