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

```bash
pip install -e .
```

## GUI

The OpenCellComms GUI (`opencellcomms_gui/`) provides a visual workflow editor for designing and running simulations. See `opencellcomms_gui/README.md` for details.

## License

MIT License