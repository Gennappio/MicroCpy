# OpenCellComms v3.0 - Multi-Scale Biological Simulation Engine

A Python-based cellular simulation platform for modeling gene regulatory networks, substance diffusion, and cell behavior in biological systems.

## Overview

OpenCellComms provides a flexible, workflow-based simulation engine for:
- **Gene Regulatory Networks** - Boolean network models for cell fate decisions
- **Substance Diffusion** - FiPy-based PDE solvers for chemical gradients
- **Cell Populations** - Agent-based modeling of cell behavior, division, migration
- **Multi-scale Integration** - Coupling intracellular, intercellular, and microenvironment dynamics

## Quick Start

### Run a Workflow
```bash
python run_workflow.py --workflow path/to/your_workflow.json
```

### Run with Config File
```bash
python run_workflow.py --sim path/to/your_config.yaml
```

## Architecture

OpenCellComms uses a **workflow-based** architecture where simulations are defined as JSON workflows with:
- **Subworkflows** - Modular, reusable workflow components
- **Functions** - Registered Python functions for each simulation step
- **Context** - Shared state passed between functions

### Workflow Structure (v2.0 format)
```json
{
  "version": "2.0",
  "name": "My Simulation",
  "subworkflows": {
    "main": {
      "controller": { "number_of_steps": 100 },
      "subworkflow_calls": [
        { "subworkflow_name": "initialization", "iterations": 1 },
        { "subworkflow_name": "simulation_step", "iterations": 100 }
      ]
    },
    "initialization": { "functions": [...] },
    "simulation_step": { "functions": [...] }
  }
}
```

## Directory Structure
```
opencellcomms_engine/
├── run_workflow.py        # Main entry point
├── src/
│   ├── workflow/          # Workflow engine (loader, executor, registry)
│   ├── biology/           # Cell, Population, GeneNetwork models
│   ├── simulation/        # Substance simulators, orchestrator
│   ├── config/            # Configuration handling
│   ├── visualization/     # Plotting and export
│   └── io/                # File I/O (VTK, CSV, H5)
├── tools/                 # Utility scripts
├── tests/                 # Test suites
└── benchmarks/            # Performance validation
```

## Requirements

- Python 3.8+
- Core: NumPy, SciPy, Matplotlib, PyYAML
- Diffusion: FiPy
- Gene Networks: MaBoss (optional)

## Installation

### Engine Only
```bash
pip install -e .
```

### With Diffusion Support
```bash
pip install -e ".[diffusion]"
```

### Full Installation (Engine + GUI + All Extras)
From the parent `MicroCpy/` directory:
```bash
./install.sh
```
This automatically discovers and installs all adapter dependencies.

## Adapters

Adapters extend OpenCellComms with experiment-specific functions and dependencies. They are optional — the engine works standalone without any adapters installed.

### How Adapters Work

Adapters are located in `../opencellcomms_adapters/<adapter_name>/` and can provide:
- **Custom functions** - Experiment-specific simulation logic (hardcoded gene names, thresholds, etc.)
- **Dependencies** - External libraries needed by the adapter (e.g., `fipy` for jayatilake, `maboss` for boolean network tools)
- **Registration** - Functions auto-discovered by the engine's registry system

### Installing Adapters

#### Automatic (Recommended)
From the parent `MicroCpy/` directory:
```bash
./install.sh
```
This script automatically discovers all adapters and installs their dependencies from `requirements.txt` files.

#### Manual Installation
To install a specific adapter's dependencies:
```bash
pip install -r ../opencellcomms_adapters/<adapter_name>/requirements.txt
```

### Available Adapters

| Adapter | Purpose | Key Dependencies |
|---------|---------|------------------|
| `jayatilake` | Diffusion-based microenvironment simulation | `fipy>=3.4.0` |
| `maboss` | MaBoSS Boolean network tools (future) | `maboss>=0.8.0` |

### Creating a New Adapter

#### Step 1: Create Adapter Directory
```
../opencellcomms_adapters/<my_adapter>/
├── __init__.py
├── requirements.txt          # Declare adapter dependencies
├── register.py               # Auto-loaded; imports and registers functions
└── functions/
    ├── __init__.py
    ├── initialization/
    ├── intracellular/
    ├── diffusion/
    ├── intercellular/
    └── finalization/
```

#### Step 2: Declare Dependencies
**`requirements.txt`** — List all external libraries needed:
```
# My Custom Adapter
some-package>=1.0.0
another-package>=2.0.0
```

#### Step 3: Write Functions
Create functions in `functions/<stage>/` (e.g., `functions/intracellular/my_logic.py`):
```python
from src.workflow.decorators import register_function
from src.workflow.parameter_types import ParameterType

@register_function(
    name="my_custom_function",
    stage="intracellular",
    description="My experiment-specific logic",
    parameters=[
        {"name": "param1", "type": ParameterType.FLOAT, "default": 0.5},
    ],
)
def my_custom_function(context, param1):
    """Custom logic here."""
    for cell in context['population'].cells:
        # Do something with cell
        pass
```

#### Step 4: Register Functions
In **`register.py`**, import all functions:
```python
"""
Adapter registration — auto-loaded by the engine
"""

from opencellcomms_adapters.my_adapter.functions.intracellular.my_logic import my_custom_function

__all__ = [my_custom_function]
```

#### Step 5: Install & Test
```bash
# Install the adapter's dependencies
pip install -r ../opencellcomms_adapters/my_adapter/requirements.txt

# Verify the adapter loads (should see [Registry] messages)
python -c "from src.workflow.registry import get_default_registry; get_default_registry()"

# Use the adapter in a workflow JSON
# Your function now appears in the GUI function palette
```

### Best Practices

1. **Per-adapter `requirements.txt`** — Declare all dependencies (helps users and `install.sh` auto-discovery)
2. **Graceful degradation** — If a dependency is missing, log a clear message (the engine continues to work)
3. **Experiment-specific, not generic** — If a function is reusable across experiments, add it to the engine instead
4. **Guard imports** — If your adapter needs optional libraries, wrap imports:
   ```python
   try:
       import some_package
       PACKAGE_AVAILABLE = True
   except ImportError:
       PACKAGE_AVAILABLE = False

   def my_function(context):
       if not PACKAGE_AVAILABLE:
           raise ImportError("some_package is required. Install with: pip install some_package")
       # Use some_package
   ```
5. **Test coverage** — Add tests in `../opencellcomms_adapters/<adapter>/tests/`

## GUI

The OpenCellComms GUI (`opencellcomms_gui/`) provides a visual workflow editor for designing and running simulations. See `opencellcomms_gui/README.md` for details.

## License

MIT License