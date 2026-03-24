"""
OpenCellComms Adapters — experiment-specific functions and data.

This package adds the engine directory to sys.path so that adapter
function files can import from ``src.workflow.decorators`` etc. without
any edits to the moved files.
"""

import sys
from pathlib import Path

engine_dir = Path(__file__).parent.parent / "opencellcomms_engine"
if str(engine_dir) not in sys.path:
    sys.path.insert(0, str(engine_dir))
