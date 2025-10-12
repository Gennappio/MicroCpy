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
- Windows (10+, with WSL recommended)

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
 unit/           # Unit tests for individual components
 integration/    # Integration tests for full workflows
 fixtures/       # Test data and configurations
 conftest.py     # Pytest configuration
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
 src/microc/          # Main package code
 tests/               # Test suite
 docs/                # Documentation
 examples/            # Example configurations
 setup.py             # Setup script
 pyproject.toml       # Modern Python packaging
 requirements.txt     # Dependencies
 Makefile            # Development commands
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
 source/
    index.rst
    api/
    tutorials/
    examples/
 Makefile
 conf.py
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
```

**Test Environment Issues**
```bash
# Clean test environment
make clean-all

# Reinstall in clean environment
pip uninstall microc
make install-dev
```

### Getting Help
- Check existing issues: https://github.com/microc/microc/issues
- Read documentation: https://microc.readthedocs.io/
- Ask questions in discussions
- Contact maintainers for urgent issues

This guide provides everything needed to set up a development environment and contribute to MicroC effectively.
