# Building and Development Guide

## Overview

This guide covers setting up the MicroC development environment, building the code, running tests, and contributing to the project.

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Git
- Make (optional, for convenience commands)
- C compiler (for optional performance packages)

### Operating System Support
- Linux (Ubuntu 18.04+, CentOS 7+)
- macOS (10.14+)
- Windows (10+, native support available)

## Quick Setup

### 1. Clone Repository
```bash
git clone https://github.com/microc/microc.git
cd microc-2.0
```

### 2. Create Virtual Environment
```bash
# Using venv
python3 -m venv microc-env
source microc-env/bin/activate  # Linux/macOS
# microc-env\Scripts\activate   # Windows

# Using conda
conda create -n microc python=3.9
conda activate microc
```

### 3. Install Development Dependencies
```bash
# Option 1: Using Make (recommended)
make install-dev

# Option 2: Using pip directly
pip install -e ".[dev,docs,jupyter,performance,visualization]"

# Option 3: Minimal installation
pip install -e .
```

### 4. Verify Installation
```bash
# Run tests
make test

# Run example simulation
make run-example
```

## Windows-Specific Setup

### Overview
MicroC was originally developed on macOS/Linux but has been successfully ported to Windows. This section covers Windows-specific setup procedures, common issues, and solutions discovered during the porting process.

### Windows Prerequisites

#### Required Software
- **64-bit Python 3.9+** (Critical: 32-bit Python will not work)
- **Git for Windows** or **GitHub Desktop**
- **Visual Studio Build Tools** (for compiling scientific packages)
- **Windows Terminal** (recommended for better command-line experience)

#### Architecture Requirements
⚠️ **Important**: MicroC requires **64-bit Python** on Windows. Modern scientific packages (SciPy, Matplotlib, FiPy) no longer provide 32-bit wheels and cannot be compiled on 32-bit Python installations.

### Windows Installation Process

#### Step 1: Install 64-bit Python
```bash
# Download from python.org
# Choose "Windows installer (64-bit)" for Python 3.9+
# During installation:
# ✅ Check "Add Python to PATH"
# ✅ Check "Install for all users" (optional but recommended)

# Verify installation
python --version
python -c "import platform; print(platform.architecture())"
# Should output: ('64bit', 'WindowsPE')
```

#### Step 2: Install Build Tools (if needed)
```bash
# Option 1: Visual Studio Build Tools (recommended)
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Option 2: Full Visual Studio Community (includes build tools)
# Download from: https://visualstudio.microsoft.com/vs/community/
```

#### Step 3: Clone and Setup
```bash
# Clone repository
git clone https://github.com/microc/microc.git
cd microc-2.0

# Create virtual environment
python -m venv microc-env
microc-env\Scripts\activate

# Upgrade pip (important for Windows)
python -m pip install --upgrade pip
```

#### Step 4: Install Dependencies
```bash
# Option 1: Use Windows batch script (recommended)
setup_windows.bat install-dev

# Option 2: Direct pip installation
python -m pip install -e ".[dev,docs,jupyter,performance]"

# Option 3: Install core dependencies only
python -m pip install -e .
```

#### Step 5: Handle Unicode Issues
If you encounter encoding errors with configuration files:
```bash
# The project includes Unicode characters (μ for micrometers)
# These have been replaced with ASCII equivalents (um) in Windows-compatible configs
# Use the provided Windows-compatible configuration files
```

### Windows-Specific Tools

#### Windows Batch Script
A `setup_windows.bat` script replaces Unix Makefile functionality:

```batch
# Available commands:
setup_windows.bat install          # Install MicroC in production mode
setup_windows.bat install-dev      # Install MicroC in development mode
setup_windows.bat install-minimal  # Install only core dependencies
setup_windows.bat test             # Run all tests
setup_windows.bat test-fast        # Run fast tests only
setup_windows.bat clean            # Clean build artifacts
setup_windows.bat run-example      # Run example simulation
setup_windows.bat help             # Show all options
```

#### Command Equivalents
| Unix/macOS Command | Windows Equivalent |
|-------------------|-------------------|
| `make install-dev` | `setup_windows.bat install-dev` |
| `make test` | `setup_windows.bat test` |
| `make clean` | `setup_windows.bat clean` |
| `python3` | `python` |
| `pip3` | `pip` |

### Common Windows Issues and Solutions

#### Issue 1: 32-bit Python Architecture Error
**Error**: `Need python for x86_64, but found x86`

**Cause**: Using 32-bit Python installation

**Solution**:
1. Uninstall 32-bit Python via Windows Settings → Apps
2. Download and install 64-bit Python from python.org
3. Verify with: `python -c "import platform; print(platform.architecture())"`

#### Issue 2: Unicode Encoding Errors
**Error**: `Invalid length unit: Î¼m` (corrupted μ character)

**Cause**: Windows encoding issues with Unicode characters in config files

**Solution**:
- Unicode characters (μ) have been replaced with ASCII equivalents (um)
- Use the provided Windows-compatible configuration files
- If creating new configs, use "um" instead of "μm"

#### Issue 3: Mayavi/VTK Installation Failures
**Error**: Mayavi compilation errors during installation

**Cause**: Complex 3D visualization dependencies don't compile well on Windows

**Solution**:
```bash
# Install without problematic visualization dependencies
python -m pip install -e ".[dev,docs,jupyter,performance]"
# Note: excludes visualization extras that include Mayavi
```

#### Issue 4: Missing Build Tools
**Error**: `Microsoft Visual C++ 14.0 is required`

**Cause**: Missing C++ compiler for building scientific packages

**Solution**:
1. Install Visual Studio Build Tools
2. Or install Visual Studio Community
3. Restart command prompt after installation

#### Issue 5: Path Separator Issues
**Error**: File path errors with forward slashes

**Cause**: Unix-style paths in originally Mac-developed code

**Solution**:
- The codebase has been updated to use `os.path.join()` and `pathlib`
- Windows path separators are handled automatically

### Windows Performance Considerations

#### Memory Usage
- Windows may use more memory than Unix systems for the same simulation
- Consider reducing grid size for large simulations on Windows

#### File I/O
- Windows file I/O can be slower than Unix systems
- Use SSD storage for better performance
- Avoid deep directory nesting

#### Parallel Processing
- Windows handles multiprocessing differently than Unix
- Some parallel features may have reduced performance
- Test parallel settings on your specific Windows configuration

### Windows Development Workflow

#### Using Windows Terminal
```bash
# Install Windows Terminal from Microsoft Store
# Configure for better development experience:
# - Set default profile to Command Prompt or PowerShell
# - Enable copy/paste with Ctrl+C/Ctrl+V
# - Use Cascadia Code font for better readability
```

#### IDE Integration
```bash
# Visual Studio Code (recommended)
# Install Python extension
# Configure Python interpreter to use virtual environment
# Set terminal to use activated environment

# PyCharm
# Configure Python interpreter
# Set up run configurations for simulations
```

#### Testing on Windows
```bash
# Run Windows-specific tests
setup_windows.bat test

# Test with example simulation
setup_windows.bat run-example

# Verify Unicode handling
python run_sim.py tests/jayatilake_experiment/jayatilake_experiment_config.yaml --steps 5
```

### Windows Deployment Notes

#### Package Distribution
- Windows wheels are built automatically for releases
- Use `python -m build` to create Windows-compatible distributions
- Test installations on clean Windows environments

#### System Requirements for End Users
- Windows 10 or later
- 64-bit architecture
- 4GB+ RAM (8GB+ recommended for large simulations)
- 2GB+ free disk space

### Troubleshooting Windows-Specific Issues

#### Debug Information Collection
```bash
# Collect system information
python -c "import platform; print(platform.platform())"
python -c "import sys; print(sys.version)"
python -c "import platform; print(platform.architecture())"

# Check installed packages
python -m pip list

# Verify critical packages
python -c "import numpy, scipy, matplotlib, pandas, yaml, fipy; print('All imports successful')"
```

#### Clean Reinstallation
```bash
# If issues persist, perform clean reinstallation:
# 1. Deactivate virtual environment
deactivate

# 2. Remove virtual environment
rmdir /s microc-env

# 3. Create new environment
python -m venv microc-env
microc-env\Scripts\activate

# 4. Reinstall
python -m pip install --upgrade pip
setup_windows.bat install-dev
```

### Windows Testing Results

The Windows port has been successfully tested with:
- ✅ Python 3.13.5 (64-bit)
- ✅ All core scientific packages (NumPy, SciPy, Matplotlib, Pandas)
- ✅ FiPy finite difference solver
- ✅ Complete simulation workflows
- ✅ Visualization and plotting
- ✅ Gene network evaluation
- ✅ Multi-substance diffusion
- ✅ Cell biology simulation

**Test Configuration**:
- Domain: 600×600 μm
- Grid: 60×60 cells
- Substances: 16 tracked molecules
- Cells: 100 biological cells
- Simulation time: Successfully completed 5 time steps

This Windows port maintains full compatibility with the original macOS/Linux functionality while providing Windows-specific tools and documentation for a smooth development experience.

## Development Workflow

### Code Formatting
MicroC uses Black and isort for code formatting:

```bash
# Format code
make format

# Check formatting without changes
make format-check

# Manual formatting
black src/ tests/
isort src/ tests/
```

### Linting
Code quality is enforced with flake8 and mypy:

```bash
# Run all linting
make lint

# Individual tools
flake8 src/ tests/
mypy src/
```

### Testing

#### Test Structure
```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for full workflows
├── fixtures/       # Test data and configurations
└── conftest.py     # Pytest configuration
```

#### Running Tests
```bash
# All tests
make test

# Fast tests only (skip slow integration tests)
make test-fast

# With coverage report
make test-coverage

# Specific test categories
make test-unit
make test-integration

# Specific test file
pytest tests/unit/test_gene_network.py -v

# Specific test function
pytest tests/unit/test_gene_network.py::test_boolean_evaluation -v
```

#### Writing Tests
```python
# tests/unit/test_example.py
import pytest
from microc.biology.gene_network import BooleanNetwork

class TestGeneNetwork:
    def test_node_creation(self):
        network = BooleanNetwork()
        network.add_node("TestGene", "input1 & input2")
        assert "TestGene" in network.nodes
    
    def test_boolean_evaluation(self):
        network = BooleanNetwork()
        network.add_node("output", "input1 & input2")
        network.set_input_states({"input1": True, "input2": False})
        result = network.evaluate_node("output")
        assert result == False

# Integration test example
def test_full_simulation():
    config_file = "tests/fixtures/test_config.yaml"
    result = run_simulation(config_file, steps=10)
    assert result["population_count"] > 0
```

## Building and Distribution

### Building Packages
```bash
# Build source and wheel distributions
make build

# Manual build
python -m build

# Check package
twine check dist/*
```

### Package Structure
```
microc-2.0/
├── src/microc/          # Main package code
├── tests/               # Test suite
├── docs/                # Documentation
├── examples/            # Example configurations
├── setup.py             # Setup script
├── pyproject.toml       # Modern Python packaging
├── requirements.txt     # Dependencies
└── Makefile            # Development commands
```

## Documentation

### Building Documentation
```bash
# Build HTML documentation
make docs

# Serve locally
make serve-docs

# Clean documentation
make docs-clean
```

### Documentation Structure
```
docs/
├── source/
│   ├── index.rst
│   ├── api/
│   ├── tutorials/
│   └── examples/
├── Makefile
└── conf.py
```

### Writing Documentation
- Use Sphinx with reStructuredText or Markdown
- Include docstrings in all public functions
- Add examples for complex features
- Update API documentation when adding new modules

## Configuration Management

### Environment Variables
```bash
# Development settings
export MICROC_DEBUG=1
export MICROC_LOG_LEVEL=DEBUG
export MICROC_DATA_DIR=/path/to/data

# Testing settings
export MICROC_TEST_MODE=1
export MICROC_FAST_TESTS=1
```

### Configuration Files
```yaml
# .microc/config.yaml (user configuration)
default_output_dir: "~/microc_results"
log_level: "INFO"
parallel_workers: 4

development:
  debug: true
  log_level: "DEBUG"
  
testing:
  fast_mode: true
  temp_dir: "/tmp/microc_tests"
```

## Performance Optimization

### Optional Performance Packages
```bash
# Install performance dependencies
pip install ".[performance]"

# Individual packages
pip install numba        # JIT compilation
pip install cython       # C extensions
pip install joblib       # Parallel processing
```

### Profiling
```bash
# Profile simulation
python -m cProfile -o profile.stats run_sim.py config.yaml

# Analyze profile
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# Memory profiling
pip install memory_profiler
python -m memory_profiler run_sim.py config.yaml
```

## Debugging

### Debug Mode
```bash
# Enable debug logging
export MICROC_DEBUG=1
python run_sim.py config.yaml --verbose

# Interactive debugging
python -i run_sim.py config.yaml --steps 1
```

### Common Issues

**Import Errors**
```bash
# Ensure package is installed in development mode
pip install -e .

# Check Python path
python -c "import sys; print(sys.path)"
```

**Test Failures**
```bash
# Run specific failing test with verbose output
pytest tests/unit/test_failing.py::test_function -v -s

# Debug test with pdb
pytest tests/unit/test_failing.py::test_function --pdb
```

**Performance Issues**
```bash
# Profile specific function
python -m cProfile -s cumulative -m microc.simulation.run config.yaml

# Check memory usage
python -m memory_profiler run_sim.py config.yaml
```

## Contributing

### Development Process
1. Fork repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Make changes with tests
4. Run quality checks: `make ci-test`
5. Commit changes: `git commit -m "Add new feature"`
6. Push branch: `git push origin feature/new-feature`
7. Create pull request

### Code Standards
- Follow PEP 8 style guide
- Use type hints for all public functions
- Write docstrings for all public APIs
- Include tests for new functionality
- Update documentation for user-facing changes

### Commit Message Format
```
type(scope): brief description

Longer description if needed

Fixes #issue_number
```

Types: feat, fix, docs, style, refactor, test, chore

## Release Process

### Version Management
```bash
# Update version in setup.py and pyproject.toml
# Create release branch
git checkout -b release/v2.1.0

# Run full test suite
make ci-test

# Build and check package
make check-release

# Tag release
git tag v2.1.0
git push origin v2.1.0
```

### Deployment
```bash
# Test deployment
make upload-test

# Production deployment
make upload
```

## Troubleshooting

### Common Build Issues

**Missing Dependencies**
```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Install build dependencies
pip install build twine
```

**Compilation Errors**
```bash
# Install system dependencies (Ubuntu)
sudo apt-get install build-essential python3-dev

# Install system dependencies (macOS)
xcode-select --install

# Install system dependencies (Windows)
# Download and install Visual Studio Build Tools
# Or install Visual Studio Community Edition
```

**Test Environment Issues**
```bash
# Clean test environment (Unix/macOS)
make clean-all

# Clean test environment (Windows)
setup_windows.bat clean

# Reinstall in clean environment (Unix/macOS)
pip uninstall microc
make install-dev

# Reinstall in clean environment (Windows)
pip uninstall microc
setup_windows.bat install-dev
```

**Windows-Specific Issues**
```bash
# 32-bit Python error
# Solution: Install 64-bit Python from python.org

# Unicode encoding errors
# Solution: Use ASCII equivalents (um instead of μm)

# Mayavi installation failures
# Solution: Install without visualization extras
python -m pip install -e ".[dev,docs,jupyter,performance]"

# Path separator issues
# Solution: Use setup_windows.bat instead of make commands

# Missing Visual C++ compiler
# Solution: Install Visual Studio Build Tools
```

### Getting Help
- Check existing issues: https://github.com/microc/microc/issues
- Read documentation: https://microc.readthedocs.io/
- Ask questions in discussions
- Contact maintainers for urgent issues

This guide provides everything needed to set up a development environment and contribute to MicroC effectively.
