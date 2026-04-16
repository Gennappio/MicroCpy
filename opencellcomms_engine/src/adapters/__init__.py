"""
Adapters for integrating external simulation frameworks into OpenCellComms.

Each adapter provides:
- Config loader: parses the external format into Python dataclasses
- Coupling logic: maps between the external model and OpenCellComms cell state
- Workflow functions: registered functions usable in the workflow engine and GUI
"""
