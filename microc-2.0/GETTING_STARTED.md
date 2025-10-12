# [RUN] Getting Started with MicroC 2.0

Welcome to MicroC 2.0! This guide will walk you through setting up and running your first biological simulation.

##  Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (for cloning the repository)

## [TOOL] Step-by-Step Setup

### Step 1: Create an Isolated Environment

To avoid conflicts with other projects, create a virtual environment:

```bash
# Create a virtual environment
python -m venv microc_env

# Activate the environment
# On macOS/Linux:
source microc_env/bin/activate
# On Windows:
# microc_env\Scripts\activate
```

### Step 2: Navigate to the Project Directory

```bash
cd microc-2.0
```

### Step 3: Install Dependencies

Install all required packages:

```bash
pip install fipy numpy scipy matplotlib pyyaml psutil
```

### Step 4: Verify Installation

Run the test suite to ensure everything is working:

```bash
python -m pytest tests/ -v
```

##  Quick Start Examples

### Example 1: Run a Complete Demo

```bash
python examples/complete_simulation_demo.py
```

### Example 2: Run All Substances Demo

```bash
python examples/run_all_substances_demo.py
```

### Example 3: Generic Simulation Runner

Use the flexible YAML-based runner:

```bash
# Run with complete substances
python run_sim.py config/complete_substances_config.yaml

# Run a simple oxygen-glucose simulation
python run_sim.py config/simple_oxygen_glucose.yaml --steps 10 --verbose

# Run with custom output directory
python run_sim.py config/simple_oxygen_glucose.yaml --output results/my_test
```

## [CHART] What You'll See

After running a simulation, you'll get:

- **Plots**: High-quality visualizations in the `plots/` directory
- **Data**: Numerical results in the `results/` directory
- **Performance metrics**: Timing and memory usage statistics

## [SEARCH] Verify Your Setup

Test that FiPy is working correctly:

```bash
python -c "import fipy; print('FiPy version:', fipy.__version__)"
```

## [TARGET] Next Steps

1. **Explore Examples**: Check out the `examples/` directory for more demos
2. **Read Documentation**: Review the various `.md` files for detailed guides
3. **Customize**: Create your own YAML configuration files
4. **Experiment**: Modify parameters and see how they affect the simulation

##  Troubleshooting

If you encounter issues:

1. **Check Python version**: Ensure you're using Python 3.8+
2. **Verify dependencies**: Make sure all packages installed correctly
3. **Run tests**: Use `python -m pytest tests/ -v` to identify problems
4. **Check FiPy**: Ensure FiPy is properly installed and importable

##  Additional Resources

- `README.md`: Comprehensive project overview
- `HOW_TO_RUN_NEW_SIMULATIONS.md`: Detailed simulation guide
- `YAML_CONFIGURATION_GUIDE.md`: Configuration file documentation
- `CUSTOM_FUNCTIONS_GUIDE.md`: Customization instructions

Happy simulating! 
