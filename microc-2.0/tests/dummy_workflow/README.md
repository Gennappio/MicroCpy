# Dummy Workflow Tests

This directory contains test workflows for validating the custom function system.

## ⚠️ IMPORTANT: Workflows Must Match Configs

**Workflows and configs must be compatible!**

- `simple_workflow.json` + `dummy_config.yaml` ✓ (for testing)
- `simple_workflow.json` + `jayatilake_experiment_config.yaml` ✗ (won't work!)
- `jaya_workflow.json` + `jayatilake_experiment_config.yaml` ✓ (real simulation)

The dummy logging functions (`dummy_logs.py`) are for **testing the workflow system only**. They don't perform actual simulation operations. For real simulations, use workflows with actual simulation functions.

---

## Test Files

### Simple Logging Test (Recommended for Quick Validation)

**Purpose:** Quickly verify that the workflow system is working.

**Files:**
- `dummy_logs.py` - Simple functions that just print their names and parameters
- `simple_workflow.json` - Workflow using the logging functions
- `run_simple_test.py` - Test runner

**Run:**
```bash
python run_simple_test.py
```

**Expected Output:**
```
>>> init_function called
    param1 = 42
    param2 = 3.14
    param3 = hello

>>> metabolism_function called
    rate = 2.5
    threshold = 0.75
    enabled = True
...
```

**What It Tests:**
- ✓ Functions are loaded from external Python file
- ✓ Functions are called in correct execution order
- ✓ Parameters are passed correctly from JSON to functions
- ✓ All 5 workflow stages execute (initialization, intracellular, diffusion, intercellular, finalization)

---

### Full Dummy Test (Comprehensive Validation)

**Purpose:** Test realistic simulation functions with detailed output.

**Files:**
- `dummy_functions.py` - 8 realistic simulation functions with detailed logging
- `dummy_workflow.json` - Complete workflow with all stages
- `run_dummy_test.py` - Test runner with validation
- `dummy_config.yaml` - Minimal simulation configuration

**Run:**
```bash
python run_dummy_test.py
```

**Expected Output:**
```
[DUMMY] Initializing 20 cells with energy=150.0
  Cell 0: position=(15.8, 3.0, 88.5), energy=150.0
  Cell 1: position=(30.2, 96.3, 29.7), energy=150.0
  ...

[DUMMY] Updating cell metabolism:
  glucose_rate=2.0
  oxygen_threshold=0.6
  enable_warburg=True
  ...
```

**What It Tests:**
- ✓ All features from simple test
- ✓ Complex parameter types (float, int, bool, string)
- ✓ Multiple functions per stage
- ✓ Context passing between functions
- ✓ Realistic simulation workflow patterns

---

## Creating Your Own Custom Functions

### 1. Create a Python File

Create a file with your custom functions (e.g., `my_functions.py`):

```python
def my_custom_function(context, param1=10, param2=5.0, param3=True):
    """
    Your custom function.
    
    Args:
        context: Dictionary with simulation state (population, mesh, timestep, etc.)
        param1: Your first parameter
        param2: Your second parameter
        param3: Your third parameter
    """
    # Access simulation state
    population = context['population']
    timestep = context.get('timestep', 0)
    
    # Your custom logic here
    print(f"Running my_custom_function at timestep {timestep}")
    print(f"  param1={param1}, param2={param2}, param3={param3}")
    
    # Return True on success
    return True
```

**Important:**
- First parameter must be `context`
- Context contains: `population`, `mesh`, `timestep`, `output_dir`, etc.
- All other parameters should have default values
- Return `True` on success, `False` or `None` on failure

### 2. Create a Workflow JSON

Create a workflow file (e.g., `my_workflow.json`):

```json
{
  "version": "1.0",
  "name": "My Custom Workflow",
  "description": "My workflow description",
  "stages": {
    "initialization": {
      "enabled": true,
      "execution_order": ["my_func_1"],
      "functions": [
        {
          "id": "my_func_1",
          "function_name": "my_custom_function",
          "enabled": true,
          "parameters": {
            "function_file": "path/to/my_functions.py",
            "param1": 42,
            "param2": 3.14,
            "param3": false
          },
          "position": {
            "x": 100,
            "y": 100
          }
        }
      ]
    }
  }
}
```

**Important:**
- `execution_order` must list function IDs in the order you want them to execute
- `function_file` is the path to your Python file (relative to `microc-2.0` directory)
- `function_name` must match the function name in your Python file
- Parameters in JSON will be passed to your function (except `function_file` and `custom_name`)

### 3. Test Your Workflow

Create a test script (e.g., `test_my_workflow.py`):

```python
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_path))

from workflow.loader import WorkflowLoader
from workflow.executor import WorkflowExecutor

# Load workflow
loader = WorkflowLoader()
workflow = loader.load('my_workflow.json')

# Create executor
executor = WorkflowExecutor(workflow)

# Create context
context = {
    'timestep': 0,
    'population': None,
    'mesh': None,
    'output_dir': 'results',
}

# Execute stage
context = executor.execute_stage('initialization', context)
```

---

## Running Workflows with Real Simulations

### Option 1: Use Existing Jayatilake Workflow

The jayatilake experiment already has a complete workflow:

```bash
cd microc-2.0
python run_microc.py --sim tests/jayatilake_experiment/jayatilake_experiment_config.yaml \
                     --workflow tests/jayatilake_experiment/jaya_workflow.json
```

This workflow has real simulation functions that:
- Initialize cell placement and ages
- Calculate metabolism using Michaelis-Menten kinetics
- Update ATP and metabolic state
- Check for cell division based on ATP threshold
- Update phenotype from gene network
- Handle cell aging and death
- Calculate migration and division direction

### Option 2: Test Workflow System with Dummy Config

To test that the workflow system is working (without running a full simulation):

```bash
cd microc-2.0/tests/dummy_workflow
python test_with_real_config.py
```

This runs `simple_workflow.json` with `dummy_config.yaml` - the functions will just print their names and parameters to verify the workflow system is working.

### Option 3: Load Workflow in GUI

1. **Open the GUI** at http://localhost:3000/
2. **Load an existing workflow:**
   - For testing: Load `simple_workflow.json` (dummy logging functions)
   - For real simulation: Load `jaya_workflow.json` (actual simulation functions)
3. **Set the config path:**
   - For testing: `tests/dummy_workflow/dummy_config.yaml`
   - For real simulation: `tests/jayatilake_experiment/jayatilake_experiment_config.yaml`
4. **Click "Run Simulation"**
5. **Watch the logs** stream in real-time

**⚠️ IMPORTANT:** Make sure the workflow and config match! Don't load `simple_workflow.json` and try to run it with `jayatilake_experiment_config.yaml` - it won't work because the dummy logging functions don't perform actual simulation operations.

---

## Creating Custom Workflows in GUI

1. **Create your custom functions** in a Python file
2. **Open the GUI** at http://localhost:3000/
3. **Click "Create Custom Function"** in the Function Palette
4. **Drag the template** to the canvas
5. **Double-click the node** to edit:
   - Set **Function Name** (e.g., `my_custom_function`)
   - Set **Function File** (e.g., `experiments/my_functions.py`)
   - Set **Description**
   - Click **"+ Add Parameter"** to add parameters
   - Set parameter names and values
6. **Save** and **Export Workflow** to JSON
7. **Test** using a test script or run via GUI

---

## Tips

- **Start simple:** Use `dummy_logs.py` as a template
- **Test early:** Run `run_simple_test.py` to verify your workflow loads
- **Check paths:** Function file paths are relative to `microc-2.0` directory
- **Use execution_order:** Always specify the order you want functions to run
- **Print debug info:** Add print statements to see what's happening
- **Return values:** Return `True` on success, `False` on failure

---

## Troubleshooting

**Problem:** "Function file not found"
- **Solution:** Check that the path in `function_file` is correct and relative to `microc-2.0` directory

**Problem:** "Function not found in file"
- **Solution:** Check that `function_name` matches the function name in your Python file exactly

**Problem:** "Function called with wrong arguments"
- **Solution:** Make sure your function has `context` as the first parameter and all other parameters have default values

**Problem:** "No functions execute"
- **Solution:** Check that `execution_order` is set and contains the function IDs

---

## File Structure

```
tests/dummy_workflow/
├── README.md                  # This file
├── dummy_logs.py              # Simple logging functions
├── simple_workflow.json       # Simple workflow (recommended for testing)
├── run_simple_test.py         # Simple test runner
├── dummy_functions.py         # Realistic simulation functions
├── dummy_workflow.json        # Full workflow with all stages
├── run_dummy_test.py          # Full test runner
└── dummy_config.yaml          # Minimal simulation config
```

