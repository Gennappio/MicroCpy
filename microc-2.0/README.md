# MicroC 2.0 🧬

**A completely configurable cellular simulation framework with ZERO hardcoded values**

## 🎯 Perfect Configuration-Driven Design

MicroC 2.0 achieves **perfect configuration-driven behavior** with **absolute zero tolerance for hardcoded values**:

- 🚫 **ZERO hardcoded values** in source code
- 📋 **100% YAML-configurable** behavior
- 🛡️ **Enforced configuration** (system fails without proper config)
- 🧪 **Comprehensive testing** proving configurability
- 🔬 **Scientific reproducibility** through explicit parameter documentation

## Overview

MicroC 2.0 is a multi-scale biological simulation framework that integrates:
- **Substance diffusion-reaction dynamics** with FiPy-based PDE solving
- **Cell population behavior** with spatial tracking and phenotype dynamics
- **Gene regulatory networks** with configurable Boolean logic
- **Multi-timescale orchestration** for efficient simulation coordination
- **Complete configurability** - every parameter comes from YAML configuration

## 🚀 Key Features

### 🚫 Zero Hardcoded Values Achievement
- **Substance concentrations** → From config
- **Gene input thresholds** → From config
- **Environmental parameters** → From config
- **Composite gene logic** → From config
- **Gene network propagation steps** → From config
- **ALL behavior** → **100% configurable**

### Bulletproof Foundation
- **Unit System**: Automatic unit conversion and validation prevents dimensional errors
- **Immutable State**: Reliable state management with copy-on-write patterns
- **Configuration Enforcement**: System fails gracefully without proper configuration
- **Type Safety**: Full type annotations and runtime validation

### Complete Configurability
- **YAML-Driven**: Every parameter specified in configuration files
- **No Magic Numbers**: Zero hardcoded values anywhere in source code
- **Scientific Reproducibility**: All assumptions explicitly documented
- **Easy Experimentation**: Change behavior by editing YAML, not code

### Professional-Grade Simulation
- **FiPy Integration**: Industry-standard PDE solving for diffusion-reaction
- **Configurable Gene Networks**: Boolean logic with AND, OR, NOT, XOR operations
- **Spatial Cell Dynamics**: Grid-based population with configurable behaviors
- **Automatic Visualization**: Built-in plotting and analysis tools

### Comprehensive Testing
- **Zero Hardcoding Tests**: Prove no hardcoded values exist
- **Configuration Tests**: Verify all parameters come from config
- **Failure Tests**: Ensure system fails without proper configuration
- **Integration Tests**: End-to-end validation of complex scenarios

## 📦 Installation

```bash
# Clone the repository
git clone <repository-url>
cd microc-2.0

# Install dependencies
pip install fipy numpy scipy matplotlib pyyaml psutil

# Verify installation
python -m pytest tests/ -v
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

### Design Patterns

- **Immutable State**: All state objects use copy-on-write patterns
- **Strategy Pattern**: Pluggable algorithms via interfaces
- **Observer Pattern**: Hook system for event handling
- **Factory Pattern**: Configuration-driven object creation

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

## 📈 Validation

MicroC 2.0 has been validated against:
- ✅ Analytical solutions for simple diffusion problems
- ✅ Published experimental data for cell population dynamics
- ✅ Benchmark problems from computational biology literature
- ✅ Performance regression tests for optimization

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

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- FiPy team for the excellent PDE solving framework
- NumPy and SciPy communities for foundational scientific computing
- The original MicroC team for inspiration and domain knowledge

---

**MicroC 2.0**: Where bulletproof engineering meets cutting-edge biology simulation. 🧬✨
