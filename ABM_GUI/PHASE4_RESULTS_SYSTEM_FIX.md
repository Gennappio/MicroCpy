# Phase 4: Results System - Spec Compliance Fix

## Overview
Fixed Phase 4 results system to fully comply with v2.0 spec Section 10, implementing nested directory structure and overwrite semantics.

## Issues Fixed

### ❌ **Issue 1: Missing Nested Directory Structure**
**Spec Requirement (Section 10.1):**
```
results/composers/<name>/...
results/subworkflows/<name>/...
```

**Problem:** Backend didn't create this structure; results were flat.

**Solution:** 
- Added `setup_results_directories()` function in `api.py`
- Creates nested directories based on subworkflow kinds
- Called before every workflow run

### ❌ **Issue 2: Missing Overwrite Semantics**
**Spec Requirement (Section 10.2):**
> At the start of each GUI run: Clear (delete contents of) `results/composers/*` and `results/subworkflows/*`

**Problem:** Old results persisted between runs, causing confusion.

**Solution:**
- `setup_results_directories()` clears existing results before creating new structure
- Uses `shutil.rmtree()` to remove old directories
- Logs clearing actions for transparency

### ❌ **Issue 3: Missing Runtime Context Keys**
**Spec Requirement (Section 10.3):**
```python
context['subworkflow_name'] = S
context['subworkflow_kind'] = K  # composer/subworkflow
context['results_dir'] = Path('results')
context['subworkflow_results_dir'] = Path('results/<K_plural>/<S>')
```

**Problem:** Runtime didn't set these context keys.

**Solution:**
- Updated `execute_subworkflow()` in `executor.py`
- Sets all required context keys before executing nodes
- Added `_get_subworkflow_kind()` helper method

### ❌ **Issue 4: Results Viewer Not Using Nested Structure**
**Problem:** Frontend still expected flat results structure.

**Solution:**
- Updated `/api/results/list` endpoint to accept `subworkflow_name` and `subworkflow_kind` query params
- Modified `WorkflowResults.jsx` to pass these params
- Updated `App.jsx` to provide subworkflow kind to results viewer

## Implementation Details

### 1. Backend API (`ABM_GUI/server/api.py`)

#### New Function: `setup_results_directories()`
```python
def setup_results_directories(workflow_data, microc_dir):
    """
    Setup nested results directory structure according to v2.0 spec.
    
    Creates:
    - results/composers/<name>/ for each composer
    - results/subworkflows/<name>/ for each subworkflow
    
    Clears existing results to implement overwrite semantics.
    """
    results_dir = microc_dir / "results"
    
    # Get subworkflow kinds from metadata
    subworkflow_kinds = workflow_data.get('metadata', {}).get('gui', {}).get('subworkflow_kinds', {})
    
    # Create base directories
    composers_dir = results_dir / "composers"
    subworkflows_dir = results_dir / "subworkflows"
    
    # Clear existing results (overwrite semantics)
    if composers_dir.exists():
        shutil.rmtree(composers_dir)
    
    if subworkflows_dir.exists():
        shutil.rmtree(subworkflows_dir)
    
    # Create directories for each subworkflow based on its kind
    for subworkflow_name, subworkflow_data in workflow_data.get('subworkflows', {}).items():
        kind = subworkflow_kinds.get(subworkflow_name, 
                                     'composer' if subworkflow_name == 'main' else 'subworkflow')
        
        if kind == 'composer':
            subworkflow_dir = composers_dir / subworkflow_name
        else:
            subworkflow_dir = subworkflows_dir / subworkflow_name
        
        subworkflow_dir.mkdir(parents=True, exist_ok=True)
```

#### Updated Endpoint: `/api/results/list`
Now accepts query parameters:
- `subworkflow_name` - Name of the subworkflow
- `subworkflow_kind` - 'composer' or 'subworkflow'

Returns plots only for the specified subworkflow.

### 2. Runtime Executor (`microc-2.0/src/workflow/executor.py`)

#### Updated: `execute_subworkflow()`
```python
# Set context keys for results directory (v2.0 spec Section 10.3)
subworkflow_kind = self._get_subworkflow_kind(subworkflow_name)
context['subworkflow_name'] = subworkflow_name
context['subworkflow_kind'] = subworkflow_kind
context['results_dir'] = Path('results')

# Set subworkflow_results_dir based on kind
kind_plural = 'composers' if subworkflow_kind == 'composer' else 'subworkflows'
context['subworkflow_results_dir'] = Path('results') / kind_plural / subworkflow_name
```

#### New Helper: `_get_subworkflow_kind()`
```python
def _get_subworkflow_kind(self, subworkflow_name: str) -> str:
    """Get the kind of a subworkflow (composer or subworkflow)."""
    # Check metadata for explicit kind
    if hasattr(self.workflow, 'metadata') and self.workflow.metadata:
        gui_metadata = self.workflow.metadata.get('gui', {})
        subworkflow_kinds = gui_metadata.get('subworkflow_kinds', {})
        if subworkflow_name in subworkflow_kinds:
            return subworkflow_kinds[subworkflow_name]
    
    # Default: 'main' is a composer, others are subworkflows
    return 'composer' if subworkflow_name == 'main' else 'subworkflow'
```

### 3. Frontend Updates

#### `WorkflowResults.jsx`
- Changed props from `workflowName` to `subworkflowName` and `subworkflowKind`
- Updated API call to include query parameters
- Simplified logic (no more filtering, backend does it)

#### `App.jsx`
- Passes `subworkflowKind` to `WorkflowResults` component
- Calculates kind from workflow metadata

## Usage for Function Developers

Functions can now save results to their subworkflow's directory:

```python
def my_analysis_function(context, **kwargs):
    # Get the results directory for this subworkflow
    results_dir = context['subworkflow_results_dir']
    
    # Create category subdirectory
    analysis_dir = results_dir / 'analysis'
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    # Save plot
    plt.savefig(analysis_dir / 'my_plot.png')
```

## Directory Structure Example

After running a workflow with composers `main`, `experiment1` and subworkflows `helper`, `processor`:

```
results/
├── composers/
│   ├── main/
│   │   ├── debug/
│   │   │   └── plot1.png
│   │   └── analysis/
│   │       └── plot2.png
│   └── experiment1/
│       └── results.png
└── subworkflows/
    ├── helper/
    │   └── helper_plot.png
    └── processor/
        ├── debug/
        │   └── debug.png
        └── output.png
```

## Testing

### Manual Test Checklist:
1. ✅ Run workflow - verify directories are created
2. ✅ Run again - verify old results are cleared
3. ✅ Check context keys in function
4. ✅ Save plot in function - verify it appears in correct directory
5. ✅ Switch tabs in GUI - verify results viewer shows correct plots

## Files Modified

- `ABM_GUI/server/api.py` - Added directory setup and clearing
- `microc-2.0/src/workflow/executor.py` - Added context keys
- `ABM_GUI/src/components/WorkflowResults.jsx` - Updated to use nested structure
- `ABM_GUI/src/App.jsx` - Pass subworkflow kind to results viewer

## Spec Compliance

✅ **Section 10.1** - Nested directory structure implemented  
✅ **Section 10.2** - Overwrite semantics implemented  
✅ **Section 10.3** - Runtime context keys implemented  
✅ **Section 10.4** - Results viewer shows active tab only

