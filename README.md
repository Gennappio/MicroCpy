# OpenCellComms

**Multi-scale cellular simulation platform with visual workflow designer.**

OpenCellComms is a Python-based simulation framework for modeling gene regulatory networks, substance diffusion, and cell behavior in biological systems — featuring a visual drag-and-drop workflow editor.

## ✨ Features

- 🧬 **Gene Regulatory Networks** — Boolean network models for cell fate decisions
- 🌊 **Substance Diffusion** — FiPy-based PDE solvers for chemical gradients
- 🔬 **Cell Populations** — Agent-based modeling of cell behavior, division, migration
- 🔗 **Multi-scale Integration** — Coupling intracellular, intercellular, and microenvironment dynamics
- 🎨 **Visual Workflow Designer** — Drag-and-drop interface for building simulations
- 📊 **Real-time Visualization** — Live results and interactive plots

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- npm 7+

### Installation

**macOS / Linux:**
```bash
git clone <your-repo-url>
cd OpenCellComms
chmod +x install.sh
./install.sh
```

**Windows:**
```batch
git clone <your-repo-url>
cd OpenCellComms
install.bat
```

### Run

**macOS / Linux:**
```bash
./run.sh
```

**Windows:**
```batch
run.bat
```

Open http://localhost:3000 in your browser.

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/INSTALL.md) | Detailed installation instructions |
| [Usage Guide](docs/USAGE.md) | How to use the GUI and CLI |
| [Engine README](opencellcomms_engine/README.md) | Simulation engine documentation |
| [GUI README](opencellcomms_gui/README.md) | Visual designer documentation |
| [Getting Started](opencellcomms_engine/GETTING_STARTED.md) | Step-by-step tutorial |

## 📁 Project Structure

```
OpenCellComms/
├── opencellcomms_engine/     # Python simulation engine
│   ├── src/                  # Source code
│   ├── tests/                # Test suites
│   ├── tools/                # Utility scripts
│   └── run_workflow.py       # Main CLI entry point
├── opencellcomms_gui/        # React visual workflow designer
│   ├── src/                  # React components
│   ├── server/               # Flask API backend
│   └── dist/                 # Production build
├── docs/                     # Documentation
│   ├── INSTALL.md            # Installation guide
│   └── USAGE.md              # Usage guide
├── install.sh / install.bat  # One-click installers
├── run.sh / run.bat          # One-click launchers
└── README.md                 # This file
```

## 🖥️ Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| macOS | ✅ Fully supported | Intel and Apple Silicon |
| Linux | ✅ Fully supported | Ubuntu, Debian, Fedora, etc. |
| Windows | ✅ Fully supported | Windows 10/11 |

## 🔧 Command Line Usage

For advanced users who prefer the command line:

```bash
# Activate environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Run a workflow
cd opencellcomms_engine
python run_workflow.py --workflow path/to/workflow.json

# See all options
python run_workflow.py --help
```

## 🤖 Claude Code Commands

When working in this repo with [Claude Code](https://claude.ai/code), the following slash commands are available:

| Command | Description |
|---------|-------------|
| `/occ_new-function` | Scaffold a new OpenCellComms simulation function. Asks what biological event to model, reads the target workflow JSON to discover its actual subworkflows, and generates a complete, registered Python function placed in the right category. Works for any workflow structure — not limited to a fixed set of stages. |
| `/occ_add-to-workflow` | Add an existing registered function to a workflow JSON file. Reads the target workflow to present its subworkflows and existing functions, then inserts the node and edges correctly without breaking existing connections. |

These commands are workflow-aware and designed for biologists: no Python or JSON knowledge required.

## 🧪 Running Tests

```bash
cd opencellcomms_engine
python -m pytest tests/ -v
```

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📞 Support

- Check the [documentation](docs/) for guides
- Review existing [issues](../../issues) for known problems
- Open a new issue for bugs or feature requests

