# Phase 6: Path Handling - Implementation

## Overview
Implemented relative path handling for function libraries to ensure workflows are portable across different systems and directory structures.

## Features Implemented

### ✅ 1. Relative Paths on Export
**Spec Requirement (Section 12.1):**
> When exporting workflow JSON to a file path W, all library paths stored in metadata must be made relative to W.parent.

**Implementation:**
- Prompts user for workflow directory when exporting (if libraries are present)
- Converts absolute library paths to relative paths
- Stores relative paths in exported JSON

**Example:**
```
Workflow saved to: /proj/workflows/my.json
Library located at: /proj/libs/custom.py
Stored as:         ../libs/custom.py
```

### ✅ 2. Absolute Paths on Import
**Spec Requirement (Section 12.2):**
> When loading workflow JSON from file path W, resolve library paths relative to W.parent.

**Implementation:**
- Accepts file path when loading workflow
- Resolves relative library paths to absolute paths
- Stores absolute paths internally for runtime use

**Example:**
```
Workflow loaded from: /proj/workflows/my.json
Library stored as:    ../libs/custom.py
Resolved to:          /proj/libs/custom.py
```

### ✅ 3. Library Import Path Handling
**Implementation:**
- In Electron: Uses `file.path` (absolute path)
- In browser: Prompts user for absolute path
- Stores absolute paths in metadata

## Implementation Details

### 1. Path Utilities (`workflowStore.js`)

#### `pathUtils.makeRelative(absolutePath, basePath)`
Converts an absolute path to a relative path based on a base directory.

```javascript
pathUtils.makeRelative('/proj/libs/custom.py', '/proj/workflows')
// Returns: '../libs/custom.py'
```

**Algorithm:**
1. Normalize paths (convert backslashes, remove trailing slashes)
2. Split into parts
3. Find common prefix
4. Build relative path with `..` for up-levels

#### `pathUtils.resolve(relativePath, basePath)`
Resolves a relative path against a base directory to get an absolute path.

```javascript
pathUtils.resolve('../libs/custom.py', '/proj/workflows')
// Returns: '/proj/libs/custom.py'
```

**Algorithm:**
1. Check if path is already absolute (return as-is)
2. Normalize base path
3. Process `..` and `.` in relative path
4. Build absolute path

#### `pathUtils.dirname(filePath)`
Extracts directory path from a file path.

```javascript
pathUtils.dirname('/proj/workflows/my.json')
// Returns: '/proj/workflows'
```

### 2. Workflow Store Updates

#### New State:
```javascript
{
  workflowFilePath: null  // Stores current workflow file path
}
```

#### Updated `loadWorkflow(workflowJson, filePath)`
```javascript
loadWorkflow: (workflowJson, filePath = null) => {
  // ... version validation ...
  
  // Resolve library paths relative to workflow file
  if (filePath && workflowJson.metadata?.gui?.function_libraries) {
    const workflowDir = pathUtils.dirname(filePath);
    workflowJson.metadata.gui.function_libraries = 
      workflowJson.metadata.gui.function_libraries.map(lib => ({
        ...lib,
        path: pathUtils.resolve(lib.path, workflowDir)
      }));
  }
  
  // Store workflow file path
  set({ workflowFilePath: filePath });
  
  // ... load workflow ...
}
```

#### Updated `exportWorkflow()`
```javascript
exportWorkflow: () => {
  // ... validation and workflow building ...
  
  // Make library paths relative to workflow file
  const exportedMetadata = { ...workflow.metadata };
  if (state.workflowFilePath && exportedMetadata.gui?.function_libraries) {
    const workflowDir = pathUtils.dirname(state.workflowFilePath);
    exportedMetadata.gui.function_libraries = 
      exportedMetadata.gui.function_libraries.map(lib => ({
        ...lib,
        path: pathUtils.makeRelative(lib.path, workflowDir)
      }));
  }
  
  return {
    version: '2.0',
    // ...
    metadata: exportedMetadata,
    // ...
  };
}
```

#### New Action: `setWorkflowFilePath(filePath)`
Allows manual setting of workflow file path.

### 3. App.jsx Updates

#### Updated `handleImportWorkflow()`
```javascript
const handleImportWorkflow = () => {
  // ... file picker ...
  reader.onload = (event) => {
    const workflowData = JSON.parse(event.target.result);
    const filePath = file.path || null;  // Electron provides file.path
    loadWorkflow(workflowData, filePath);
  };
};
```

#### Updated `handleExportWorkflow()`
```javascript
const handleExportWorkflow = () => {
  // Prompt for workflow directory if libraries are present
  if (workflow.metadata?.gui?.function_libraries?.length > 0) {
    const workflowDir = prompt('Enter the directory where you will save this workflow file:');
    if (workflowDir) {
      const filename = `${workflow.name}.json`;
      const fullPath = `${workflowDir}/${filename}`;
      setWorkflowFilePath(fullPath);
    }
  }
  
  const workflowData = exportWorkflow();
  // ... download file ...
};
```

### 4. FunctionPalette.jsx Updates

#### Updated `handleFileSelected()`
```javascript
const handleFileSelected = async (event) => {
  const file = event.target.files?.[0];
  
  // Get absolute path for library
  let libraryPath = file.path;  // Electron
  if (!libraryPath) {
    // Browser: prompt user
    libraryPath = prompt(`Enter the absolute path to the library file:`);
  }
  
  // ... parse and add library with absolute path ...
};
```

## Usage Guide

### For GUI Users:

#### Exporting Workflows with Libraries:

1. Click "Export JSON"
2. If you have imported libraries, you'll be prompted:
   ```
   Enter the directory where you will save this workflow file:
   Example: /Users/yourname/projects/workflows
   ```
3. Enter the directory path
4. Save the file to that directory
5. Library paths in the JSON will be relative

#### Importing Workflows with Libraries:

1. Click "Import JSON"
2. Select the workflow file
3. Library paths will be automatically resolved relative to the workflow file location

#### Importing Libraries:

1. Click the Upload icon in the Function Palette
2. Select a `.py` file
3. If in browser mode, you'll be prompted:
   ```
   Enter the absolute path to the library file:
   Example: /Users/yourname/projects/libs/custom.py
   ```
4. Enter the full path to the library file

### For Electron Users:

- File paths are automatically detected
- No prompts needed for library or workflow paths
- Everything works seamlessly

### Example Workflow:

**Directory Structure:**
```
/proj/
├── workflows/
│   └── my_workflow.json
└── libs/
    ├── analysis.py
    └── visualization.py
```

**Workflow JSON (exported):**
```json
{
  "version": "2.0",
  "metadata": {
    "gui": {
      "function_libraries": [
        {
          "path": "../libs/analysis.py",
          "functions": { "analyze": "variant" }
        },
        {
          "path": "../libs/visualization.py",
          "functions": { "plot": "overwrite" }
        }
      ]
    }
  }
}
```

**When loaded:**
- Paths resolved to `/proj/libs/analysis.py` and `/proj/libs/visualization.py`
- Functions available in palette
- Runtime can find library files

## Browser Limitations

Since browsers don't provide access to file system paths:

1. **Export:** User must manually specify workflow directory
2. **Import:** File path not available (unless using File System Access API)
3. **Library Import:** User must manually specify library path

**Workaround:** Prompts guide users to provide necessary paths.

**Future Enhancement:** Use File System Access API for better browser support.

## Files Modified

1. **`ABM_GUI/src/store/workflowStore.js`**
   - Added `pathUtils` object with path manipulation functions
   - Added `workflowFilePath` state
   - Updated `loadWorkflow()` to resolve library paths
   - Updated `exportWorkflow()` to make library paths relative
   - Added `setWorkflowFilePath()` action

2. **`ABM_GUI/src/App.jsx`**
   - Updated `handleImportWorkflow()` to pass file path
   - Updated `handleExportWorkflow()` to prompt for directory
   - Added `setWorkflowFilePath` to store imports

3. **`ABM_GUI/src/components/FunctionPalette.jsx`**
   - Updated `handleFileSelected()` to prompt for library path in browser mode
   - Uses absolute paths for library storage

## Spec Compliance

✅ **Section 12.1** - Make library paths relative on export  
✅ **Section 12.2** - Resolve library paths relative to workflow file on import  
✅ **Section 12.3** - Per-node function_file paths (handled by MicroC runtime)

## Testing Checklist

- [ ] Export workflow with libraries (with directory prompt)
- [ ] Verify exported JSON has relative paths
- [ ] Import workflow with relative library paths
- [ ] Verify libraries are resolved to absolute paths
- [ ] Import library in browser mode (with path prompt)
- [ ] Move workflow and libraries to different directory
- [ ] Import moved workflow and verify libraries still work
- [ ] Test with multiple libraries in different directories

## Known Limitations

1. **Browser File Paths:** Requires manual user input for paths
2. **Path Validation:** No validation that entered paths are correct
3. **Cross-Platform:** Assumes forward slashes work (may need adjustment for Windows)

## Future Enhancements

1. Use File System Access API for better browser support
2. Add path validation and existence checking
3. Support drag-and-drop for library import with automatic path detection
4. Add library path management UI (view/edit library paths)
5. Detect and warn about broken library paths

