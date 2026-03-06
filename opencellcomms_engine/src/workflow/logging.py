"""
Centralized logging utility for workflow functions.

This module provides a consistent logging interface for workflow functions
with support for global and per-node verbosity control.
"""

import sys
from typing import Dict, Any, Optional


def _safe_print(text: str) -> None:
    """Print text, replacing characters that the console encoding cannot handle."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace'))


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
            _safe_print(f"{prefix} {message}")
        else:
            _safe_print(message)


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
        _safe_print(f"{prefix} {message}")
    else:
        _safe_print(message)


def cli_log(context: Dict[str, Any], message: str,
            prefix: str = "", node_verbose: Optional[bool] = None) -> None:
    """
    Log a message ONLY when running from CLI (not from GUI).

    Useful for CLI-specific debug information or progress messages that
    should not appear in the GUI console.

    Args:
        context: Workflow context dictionary
        message: Message to log
        prefix: Prefix for the message (e.g., "[CLI]")
        node_verbose: Per-node verbose setting (None = use global setting)
    """
    # Only log if NOT running from GUI (i.e., running from CLI)
    if not context.get('running_from_gui', False):
        if should_log(context, node_verbose):
            if prefix:
                _safe_print(f"{prefix} {message}")
            else:
                _safe_print(message)


def gui_log(context: Dict[str, Any], message: str,
            prefix: str = "", node_verbose: Optional[bool] = None) -> None:
    """
    Log a message ONLY when running from GUI (not from CLI).

    Useful for GUI-specific messages or progress updates that should only
    appear in the GUI console, not in CLI output.

    Args:
        context: Workflow context dictionary
        message: Message to log
        prefix: Prefix for the message (e.g., "[GUI]")
        node_verbose: Per-node verbose setting (None = use global setting)
    """
    # Only log if running from GUI
    if context.get('running_from_gui', False):
        if should_log(context, node_verbose):
            if prefix:
                _safe_print(f"{prefix} {message}")
            else:
                _safe_print(message)

