"""
PhysiCell Mechanics Adapter — pybind11 C++ extension.

Provides PhysiCell-faithful cell-cell mechanics:
- Hertzian repulsion with (1-d/R)^2 potential
- Adhesion forces with (1-d/S)^2 potential
- Uniform-grid neighbor search
- Adams-Bashforth position integration
- Per-cell pressure accumulation

The C++ kernel (_physicell_mechanics) is built from
src/adapters/physicell_mechanics/mechanics.cpp via pip install -e.

If the extension is not built, the module falls back to a NumPy
implementation (slower but functionally equivalent).
"""

from typing import Optional
import warnings

_ext = None
try:
    from . import _physicell_mechanics as _ext  # type: ignore
    HAS_CXX_EXTENSION = True
except ImportError:
    HAS_CXX_EXTENSION = False


def get_extension():
    """Return the compiled C++ extension or None if not built."""
    return _ext


def require_extension():
    """Raise ImportError with a helpful message if the extension isn't built."""
    if _ext is None:
        raise ImportError(
            "PhysiCell mechanics C++ extension is not built. "
            "Run: pip install -e opencellcomms_engine/ "
            "or python -m pip install pybind11 && "
            "python setup.py build_ext --inplace"
        )
    return _ext


__all__ = ["HAS_CXX_EXTENSION", "get_extension", "require_extension"]
