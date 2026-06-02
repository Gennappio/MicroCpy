"""Pytest path bootstrap.

Ensures both import roots are available regardless of how pytest is invoked:
- the engine root (parent of ``tests/``) so ``import src...`` resolves;
- the repository root (parent of the engine) so ``import
  opencellcomms_adapters...`` resolves (the PhysiBoSS adapter lives there).
"""
import os
import sys

_ENGINE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_ENGINE_ROOT, ".."))

for _p in (_ENGINE_ROOT, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
