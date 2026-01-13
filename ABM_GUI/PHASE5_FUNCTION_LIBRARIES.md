# Phase 5: Function Libraries - Implementation

## Overview
Implemented workflow-global function library system with conflict resolution, allowing users to import custom Python files containing workflow functions.

## Features Implemented

### ✅ 1. Library Import Button
**Location:** Function Palette toolbar (v2.0 workflows only)

**Implementation:**
- Added Upload icon button in palette header
- Hidden file input for `.py` file selection
- Triggers library parsing and conflict detection

### ✅ 2. Conflict Resolution Dialog
**Component:** `LibraryConflictDialog.jsx`

**Features:**
- Detects conflicts with existing functions
- Provides 3 resolution options per function:
  1. **Overwrite** - Replace existing function globally
  2. **Create Variant** - Add as new variant with `(filename)` suffix
  3. **Skip** - Don't import this function
- Default selection: Variant (safest option)
- Visual indication of existing vs. new source

### ✅ 3. Library Grouping in Palette
**Display:**
- New "Imported Libraries" section in palette
- Functions grouped by library file name
- Collapsible sections for organization
- Shows total function count

### ✅ 4. Variant Display
**Format:** `function_name (library.py)`

**Implementation:**
- Variant suffix shown in palette
- Dragging variant creates node with `function_file` property
- Non-variant functions use default resolution

### ✅ 5. Metadata Storage
**Location:** `workflow.metadata.gui.function_libraries`

**Structure:**
```json
{
  "metadata": {
    "gui": {
      "function_libraries": [
        {
          "path": "/path/to/library.py",
          "functions": {
            "function_name": "overwrite",
            "another_function": "variant",
            "skipped_function": "skip"
          }
        }
      ]
    }
  }
}
```

## Implementation Details

### 1. Backend API (`ABM_GUI/server/api.py`)

#### New Endpoint: `/api/library/parse`
```python
POST /api/library/parse
{
  "library_path": "/path/to/library.py"
}

Response:
{
  "success": true,
  "functions": [
    {
      "name": "function_name",
      "signature": "def function_name(context, **kwargs)",
      "docstring": "Function description",
      "category": "utility"
    }
  ],
  "library_name": "library.py"
}
```

**Features:**
- Parses Python AST to extract function definitions
- Skips private functions (starting with `_`)
- Extracts docstrings for descriptions
- Attempts to extract category from decorators
- Returns syntax errors if file is invalid

### 2. Workflow Store (`ABM_GUI/src/store/workflowStore.js`)

#### New Actions:

**`addFunctionLibrary(libraryPath, functionMappings)`**
- Adds or updates a library in metadata
- Stores function resolution modes
- Updates existing library if path matches

**`removeFunctionLibrary(libraryPath)`**
- Removes library from metadata
- Cleans up function mappings

**`getFunctionLibraries()`**
- Returns array of imported libraries
- Used for palette display

### 3. Function Palette (`ABM_GUI/src/components/FunctionPalette.jsx`)

#### New State:
- `libraryFunctions` - Functions from imported libraries
- `conflictDialog` - Conflict resolution dialog state
- `fileInputRef` - Reference to hidden file input

#### New Functions:

**`handleImportLibrary()`**
- Triggers file picker

**`handleFileSelected(event)`**
- Parses selected library file
- Detects conflicts with existing functions
- Shows conflict dialog or adds library directly

**`handleConflictResolution(resolutions)`**
- Applies user's resolution choices
- Updates workflow metadata
- Adds functions to palette display

#### Drag Behavior:
- Variant functions include `function_file` property
- Non-variant functions use default resolution
- Label shows variant suffix when applicable

### 4. Conflict Dialog (`ABM_GUI/src/components/LibraryConflictDialog.jsx`)

#### Props:
- `conflicts` - Array of conflicting functions
- `libraryName` - Name of library being imported
- `onResolve(resolutions)` - Callback with resolution choices
- `onCancel()` - Callback to cancel import

#### UI Elements:
- Warning icon and header
- List of conflicts with radio buttons
- Existing vs. new source display
- Apply/Cancel buttons

## Usage Guide

### For GUI Users:

1. **Import a Library:**
   - Click the Upload icon in the Function Palette toolbar
   - Select a `.py` file containing workflow functions
   - If conflicts exist, resolve them in the dialog
   - Functions appear in "Imported Libraries" section

2. **Resolve Conflicts:**
   - **Overwrite:** Use when you want to replace the existing function everywhere
   - **Variant:** Use when you want both versions available (safest)
   - **Skip:** Use when you don't want this particular function

3. **Use Library Functions:**
   - Drag from "Imported Libraries" section like any other function
   - Variants show `(filename.py)` suffix
   - Configure parameters in node settings

### For Function Developers:

Create a library file (e.g., `my_library.py`):

```python
def my_custom_function(context, **kwargs):
    """
    Description of what this function does.
    
    This will appear in the palette as the function description.
    """
    # Access context
    results_dir = context.get('subworkflow_results_dir')
    subworkflow_name = context.get('subworkflow_name')
    
    # Get parameters
    param1 = kwargs.get('param1', 'default')
    
    # Do work
    print(f"[my_custom_function] Running in {subworkflow_name}")
    
    # Save results
    if results_dir:
        output_dir = results_dir / 'custom'
        output_dir.mkdir(parents=True, exist_ok=True)
        # Save files...
    
    return {'status': 'success'}


def another_function(context, **kwargs):
    """Another custom function."""
    # Implementation...
    pass
```

**Requirements:**
- Functions must accept `context` and `**kwargs`
- Use docstrings for descriptions (first line shown in palette)
- Don't start function names with `_` (will be skipped)
- Save results to `context['subworkflow_results_dir']`

## Example Library

See `microc-2.0/example_library.py` for a complete example with:
- Custom analysis with matplotlib
- Data processing
- Result export to JSON
- Custom initialization

## Files Modified

1. **`ABM_GUI/server/api.py`**
   - Added `ast` and `inspect` imports
   - Added `/api/library/parse` endpoint

2. **`ABM_GUI/src/store/workflowStore.js`**
   - Added `function_libraries` to metadata
   - Added `addFunctionLibrary()` action
   - Added `removeFunctionLibrary()` action
   - Added `getFunctionLibraries()` getter

3. **`ABM_GUI/src/components/FunctionPalette.jsx`**
   - Added library import button
   - Added conflict detection logic
   - Added "Imported Libraries" section
   - Added variant display support

4. **`ABM_GUI/src/components/FunctionPalette.css`**
   - Added `.import-library-btn` styles
   - Added `.library-group` styles
   - Added `.variant-suffix` styles

5. **`ABM_GUI/src/components/LibraryConflictDialog.jsx`** (new)
   - Conflict resolution UI component

6. **`ABM_GUI/src/components/LibraryConflictDialog.css`** (new)
   - Dialog styling

7. **`microc-2.0/example_library.py`** (new)
   - Example library for testing

## Spec Compliance

✅ **Section 11.2** - Palette toolbar "Import Function Library" button  
✅ **Section 11.3** - Conflict resolution dialog (Overwrite/Variant/Skip)  
✅ **Section 11.4** - Library grouping in palette  
✅ **Section 11.4** - Variant display with `(<basename>)` suffix  
✅ **Section 11.3** - `metadata.gui.function_libraries` storage

## Testing Checklist

- [ ] Import library with no conflicts
- [ ] Import library with conflicts
- [ ] Test Overwrite resolution
- [ ] Test Variant resolution
- [ ] Test Skip resolution
- [ ] Verify variant suffix in palette
- [ ] Drag variant function to canvas
- [ ] Verify `function_file` property on variant nodes
- [ ] Save and reload workflow with libraries
- [ ] Test library grouping display

## Known Limitations

1. **File Path Handling:** Currently stores absolute paths. Section 12 (Path Handling) requires relative paths on export - not yet implemented.

2. **Library Reloading:** If library file is modified, must re-import to see changes.

3. **Function Source Tracking:** "Existing source" in conflict dialog currently shows "Built-in" for all existing functions. Could be enhanced to track actual source.

4. **Category Detection:** Only detects categories from `@workflow_function` decorator. Could be enhanced to support other patterns.

## Future Enhancements

1. Implement Section 12 (relative path handling on export/import)
2. Add library management UI (view/remove imported libraries)
3. Track function sources for better conflict resolution
4. Support hot-reloading of library files
5. Add library validation (check for required function signature)

