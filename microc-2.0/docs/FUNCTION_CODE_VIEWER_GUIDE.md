# Function Code Viewer - Implementation Guide

## Overview

The workflow system now supports **viewing and editing function source code** directly from the GUI. Each granular function is stored in its own file, making it easy to view, edit, and customize the simulation logic.

## Architecture

### Backend: One Function Per File

Granular functions are organized in a clear directory structure:

```
src/workflow/functions/
├── __init__.py                    # Re-exports all functions
├── intracellular/
│   ├── __init__.py
│   ├── update_metabolism.py       # ← Individual function file
│   ├── update_gene_networks.py
│   ├── update_phenotypes.py
│   └── remove_dead_cells.py
├── diffusion/
│   ├── __init__.py
│   └── run_diffusion_solver.py
└── intercellular/
    ├── __init__.py
    ├── update_cell_division.py
    └── update_cell_migration.py
```

**Benefits**:
- ✅ Each function is isolated and easy to find
- ✅ Clear organization by simulation stage
- ✅ Git-friendly (small, focused diffs)
- ✅ Backward compatible (re-exported from `__init__.py`)

### Function Registry with Source Paths

Each function in the registry now includes a `source_file` field:

```python
registry.register(FunctionMetadata(
    name="update_metabolism",
    display_name="Update Metabolism",
    description="Update intracellular metabolism (ATP, metabolites)",
    category=FunctionCategory.INTRACELLULAR,
    source_file="src/workflow/functions/intracellular/update_metabolism.py",  # ← NEW
    ...
))
```

This allows the GUI to:
1. Find the source file for any function
2. Display the code to the user
3. Save edits back to the correct file

### Flask API Endpoints

Three new endpoints provide robust code viewing/editing:

#### 1. `GET /api/function/source`

Get source code for a function.

**Query Parameters**:
- `name` (required): Function name (e.g., `update_metabolism`)
- `file` (optional): Source file path (auto-detected from registry if not provided)

**Response**:
```json
{
  "success": true,
  "source": "def update_metabolism(...):\n    ...",
  "file_path": "src/workflow/functions/intracellular/update_metabolism.py",
  "function_name": "update_metabolism"
}
```

**Example**:
```bash
curl "http://localhost:5000/api/function/source?name=update_metabolism"
```

#### 2. `POST /api/function/save`

Save edited source code.

**Request Body**:
```json
{
  "name": "update_metabolism",
  "source": "def update_metabolism(...):\n    # Modified code\n    ...",
  "file": "src/workflow/functions/intracellular/update_metabolism.py"  // optional
}
```

**Response**:
```json
{
  "success": true,
  "file_path": "src/workflow/functions/intracellular/update_metabolism.py",
  "message": "Successfully saved update_metabolism",
  "backup_path": "update_metabolism.py.bak"
}
```

**Safety Features**:
- ✅ Validates Python syntax before saving
- ✅ Creates backup file (`.py.bak`) before overwriting
- ✅ Restores from backup if write fails
- ✅ Cannot create new files (only edit existing ones)
- ✅ Returns detailed error messages for syntax errors

**Example**:
```bash
curl -X POST http://localhost:5000/api/function/save \
  -H "Content-Type: application/json" \
  -d '{"name": "update_metabolism", "source": "..."}'
```

#### 3. `POST /api/function/validate`

Validate Python code without saving.

**Request Body**:
```json
{
  "source": "def update_metabolism(...):\n    ..."
}
```

**Response (valid)**:
```json
{
  "valid": true,
  "errors": []
}
```

**Response (invalid)**:
```json
{
  "valid": false,
  "errors": [{
    "type": "SyntaxError",
    "message": "invalid syntax",
    "line": 15,
    "offset": 4,
    "text": "    helpers['update_intracellular'()\n"
  }]
}
```

**Example**:
```bash
curl -X POST http://localhost:5000/api/function/validate \
  -H "Content-Type: application/json" \
  -d '{"source": "def test():\n    print(\"hello\")"}'
```

## GUI Integration (Recommended Approach)

### Option A: Code Tab in Node Settings Panel (Recommended)

When a user clicks on a workflow node:

1. **Settings panel opens** on the right side
2. **Two tabs appear**:
   - **Parameters** tab: Shows function parameters (existing)
   - **Code** tab: Shows function source code (NEW)

3. **Code tab features**:
   - Syntax-highlighted Python code (Monaco Editor)
   - Read-only by default
   - "Edit" button → enables editing
   - "Save" button → validates and saves changes
   - "Revert" button → discards changes
   - Live syntax validation (shows errors as you type)

**Benefits**:
- Less screen clutter
- Users focus on workflow first, code second
- Can still view/edit code when needed
- Better for beginners

### Monaco Editor Integration

Use Monaco Editor (VS Code's editor) for the best experience:

```bash
npm install @monaco-editor/react
```

```jsx
import Editor from '@monaco-editor/react';

function CodeViewer({ functionName }) {
  const [code, setCode] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  // Load code when component mounts
  useEffect(() => {
    fetch(`http://localhost:5000/api/function/source?name=${functionName}`)
      .then(res => res.json())
      .then(data => setCode(data.source));
  }, [functionName]);

  const handleSave = async () => {
    // Validate first
    const validateRes = await fetch('http://localhost:5000/api/function/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: code })
    });
    const validateData = await validateRes.json();

    if (!validateData.valid) {
      alert(`Syntax error: ${validateData.errors[0].message}`);
      return;
    }

    // Save
    const saveRes = await fetch('http://localhost:5000/api/function/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: functionName, source: code })
    });
    const saveData = await saveRes.json();

    if (saveData.success) {
      alert('Saved successfully!');
      setIsEditing(false);
    } else {
      alert(`Error: ${saveData.error}`);
    }
  };

  return (
    <div>
      <div className="toolbar">
        {!isEditing && <button onClick={() => setIsEditing(true)}>Edit</button>}
        {isEditing && (
          <>
            <button onClick={handleSave}>Save</button>
            <button onClick={() => setIsEditing(false)}>Cancel</button>
          </>
        )}
      </div>
      <Editor
        height="400px"
        language="python"
        value={code}
        onChange={setCode}
        options={{
          readOnly: !isEditing,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
        }}
      />
    </div>
  );
}
```

## Safety and Best Practices

### For Users

1. **Always test after editing** - Run the simulation to make sure your changes work
2. **Start small** - Make small changes and test frequently
3. **Use version control** - Commit your changes to git before editing
4. **Check backups** - Backup files (`.py.bak`) are created automatically

### For Developers

1. **Validate before saving** - Always call `/api/function/validate` first
2. **Handle errors gracefully** - Show clear error messages to users
3. **Provide undo/revert** - Let users discard changes easily
4. **Syntax highlighting** - Use Monaco Editor for the best experience
5. **Auto-save** - Consider auto-saving to local storage (not server)

## Testing

### Test the API Endpoints

```bash
# 1. Get function source
curl "http://localhost:5000/api/function/source?name=update_metabolism" | python -m json.tool

# 2. Validate code
curl -X POST http://localhost:5000/api/function/validate \
  -H "Content-Type: application/json" \
  -d '{"source": "def test():\n    print(\"hello\")"}'

# 3. Save code (creates backup first)
curl -X POST http://localhost:5000/api/function/save \
  -H "Content-Type: application/json" \
  -d '{"name": "update_metabolism", "source": "..."}'
```

### Test the Workflow

```bash
# Run workflow to verify functions still work
python microc-2.0/run_microc.py --workflow microc-2.0/tests/jayatilake_experiment/jaya_workflow_2d_csv.json
```

## Future Enhancements

1. **Function templates** - Create new functions from templates
2. **Diff viewer** - Show changes before saving
3. **Version history** - Git integration to view/restore previous versions
4. **Live validation** - Show errors as you type (Monaco supports this)
5. **Function testing** - Test individual functions without running full simulation
6. **Code snippets** - Provide common code patterns (loops, conditionals, etc.)
7. **Documentation** - Show function docstrings and parameter descriptions

## Summary

✅ **Backend restructuring complete** - Granular functions in separate files
✅ **Registry updated** - All functions have `source_file` paths
✅ **API endpoints ready** - Read, write, and validate function code
✅ **Backward compatible** - Existing workflows still work
✅ **Robust and safe** - Syntax validation, backups, error handling

The GUI can now provide a powerful code editing experience that makes the ABM truly customizable! 🚀

