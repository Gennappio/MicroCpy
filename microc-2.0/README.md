# MicroC 2.0 🧬

## Overview

MicroC 2.0 is a multi-scale biological simulation framework that integrates:
- **Substance diffusion-reaction dynamics** with FiPy-based PDE solving
- **Cell population behavior** with spatial tracking and phenotype dynamics
- **Gene regulatory networks** with configurable Boolean logic
- **Multi-timescale orchestration** for simulation coordination
- **Complete configurability** - every parameter comes from YAML configuration


## 📦 Installation

### Quick Installation
```bash
# Clone the repository
git clone <repository-url>
cd microc-2.0

# Install with all dependencies
pip install -e ".[dev,docs,jupyter,performance,visualization]"

# Or minimal installation
pip install -e .

# Verify installation
make test
```

### Development Setup
```bash
# Setup development environment
make install-dev

# Run all quality checks
make ci-test

# Build documentation
make docs
```

## 🏃‍♂️ Quick Start

### Basic Simulation
```python
# Run the complete demo
python examples/complete_simulation_demo.py
```

### Custom Simulation
```python
from core.domain import MeshManager
from core.units import Length, Concentration
from simulation.substance_simulator import SubstanceSimulator
from biology.population import CellPopulation
from config import DomainConfig, SubstanceConfig

# Create domain
domain = DomainConfig(
    size_x=Length(800.0, "μm"),
    size_y=Length(800.0, "μm"),
    nx=40, ny=40
)
mesh = MeshManager(domain)

# Set up substance
substance = SubstanceConfig(
    name="lactate",
    diffusion_coeff=6.70e-11,
    initial_value=Concentration(5.0, "mM")
)
simulator = SubstanceSimulator(mesh, substance)

# Create cell population
population = CellPopulation(grid_size=(40, 40))
population.add_cell((20, 20), "normal")

# Run simulation step
cell_reactions = population.get_substance_reactions()
simulator.solve_steady_state(cell_reactions)
```

## 🏗️ Architecture

### Core Components

1. **Core Layer** (`src/core/`)
   - `units.py`: Bulletproof unit system with automatic conversion
   - `domain.py`: Mesh management and spatial validation
   - `config.py`: Type-safe configuration management

2. **Biology Layer** (`src/biology/`)
   - `cell.py`: Individual cell behavior and state management
   - `population.py`: Spatial cell population dynamics
   - `gene_network.py`: Boolean gene regulatory networks

3. **Simulation Layer** (`src/simulation/`)
   - `substance_simulator.py`: FiPy-based diffusion-reaction solving
   - `orchestrator.py`: Multi-timescale process coordination
   - `performance.py`: Real-time monitoring and profiling

4. **Interface Layer** (`src/interfaces/`)
   - `base.py`: Abstract base classes and contracts
   - `hooks.py`: Customization and extension system

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_units.py -v          # Unit system tests
python -m pytest tests/test_biology.py -v       # Biology component tests
python -m pytest tests/test_simulation.py -v    # Simulation engine tests
python -m pytest tests/test_interfaces.py -v    # Interface contract tests
```

## 📊 Performance

MicroC 2.0 includes comprehensive performance monitoring:

```python
from simulation.performance import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.start_monitoring()

# Your simulation code here
with monitor.profile("simulation_step"):
    # ... simulation logic ...
    pass

# Get performance statistics
stats = monitor.get_statistics()
print(f"CPU: {stats['current_metrics']['cpu_percent']:.1f}%")
print(f"Memory: {stats['current_metrics']['memory_mb']:.1f} MB")
```

## 🔧 Customization

### Hook System
```python
# Custom boundary conditions
def custom_boundary_condition(mesh, substance_config):
    # Your custom logic here
    return boundary_values

# Register the hook
from interfaces.hooks import get_hook_manager
hook_manager = get_hook_manager()
hook_manager.register_custom_function("apply_boundary_conditions", custom_boundary_condition)
```

### Custom Cell Behavior
```python
from biology.cell import Cell

class CustomCell(Cell):
    def custom_phenotype_update(self, local_environment):
        # Your custom phenotype logic
        pass

# Use in population
population = CellPopulation(grid_size=(40, 40), cell_class=CustomCell)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for your changes
4. Ensure all tests pass (`python -m pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📚 Documentation

- **API Reference**: See docstrings in source code
- **Examples**: Check `examples/` directory
- **Getting Started**: See `GETTING_STARTED.md`

## 🐛 Troubleshooting

### Common Issues

1. **FiPy Installation**: Ensure you have a working FiPy installation
   ```bash
   python -c "import fipy; print('FiPy version:', fipy.__version__)"
   ```

2. **Unit Conversion Errors**: Check that all quantities have proper units
   ```python
   from core.units import Length
   size = Length(800.0, "μm")  # ✅ Correct
   size = 800.0                # ❌ Will cause errors
   ```

3. **Memory Issues**: Use performance monitoring to track memory usage
   ```python
   monitor = PerformanceMonitor()
   monitor.set_threshold('memory_mb', 1000.0)  # Alert at 1GB
   ```

## 🛠️ Development and Build System

### Make Commands
```bash
# Development setup
make install-dev        # Install with all dev dependencies
make test               # Run all tests
make test-fast          # Run fast tests only
make test-coverage      # Run tests with coverage report

# Code quality
make format             # Format code with black and isort
make lint               # Run linting (flake8, mypy)
make ci-test            # Run all CI checks

# Documentation
make docs               # Build documentation
make serve-docs         # Serve docs locally

# Build and distribution
make build              # Build distribution packages
make clean              # Clean build artifacts
```

### Project Structure
```
microc-2.0/
├── src/microc/          # Main package code
├── tests/               # Test suite
├── docs/                # Documentation
├── examples/            # Example configurations
├── setup.py             # Setup script
├── pyproject.toml       # Modern Python packaging
├── requirements.txt     # Dependencies
├── Makefile            # Development commands
└── README.md           # This file
```

### Documentation
- [Running Simulations](docs/running_simulations.md)
- [Custom Functions and Gene Manipulation](docs/custom_functions_and_gene_manipulation.md)
- [Building and Development](docs/building_and_development.md)

## 🤝 Contributing

We welcome contributions! Please see our [Building and Development Guide](docs/building_and_development.md) for details on:
- Setting up development environment
- Code standards and formatting
- Testing requirements
- Documentation guidelines

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- FiPy team for the excellent PDE solving framework
- NumPy and SciPy communities for foundational scientific computing
- The original MicroC team for inspiration and domain knowledge

---