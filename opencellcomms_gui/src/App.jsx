import { useState, useEffect } from 'react';
import { Download, Upload, FileJson, Plus, X, Edit2, Save } from 'lucide-react';
import FunctionPalette from './components/FunctionPalette';
import WorkflowCanvas from './components/WorkflowCanvas';
import NodeInspector from './components/NodeInspector';
import MainTabSelector from './components/MainTabSelector';
import ResultsExplorer from './components/ResultsExplorer';
import ParametersDashboard from './components/ParametersDashboard';
import useWorkflowStore from './store/workflowStore';
import { fetchRegistry } from './data/functionRegistry';
import './App.css';

function App() {
		  const {
        currentStage,
        setCurrentStage,
        currentMainTab,
        setCurrentMainTab,
        workflow,
        loadWorkflow,
        exportWorkflow,
        setWorkflowFilePath,
        workflowFilePath,
        addSubWorkflow,
        deleteSubWorkflow,
        renameSubWorkflow,
        inspector,
      } = useWorkflowStore();

  const [showNewSubWorkflowDialog, setShowNewSubWorkflowDialog] = useState(false);
  const [newSubWorkflowName, setNewSubWorkflowName] = useState('');
  const [renamingSubWorkflow, setRenamingSubWorkflow] = useState(null);

  // Resizable panel widths
  const [paletteWidth, setPaletteWidth] = useState(308);  // Increased by 10% (280 * 1.1 = 308)
  const [inspectorWidth, setInspectorWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(null);

  // Resize handlers
  const handleMouseDown = (panel) => (e) => {
    e.preventDefault();
    setIsResizing(panel);
  };

  useEffect(() => {
    if (!isResizing) {
      document.body.classList.remove('resizing');
      return;
    }

    document.body.classList.add('resizing');

    const handleMouseMove = (e) => {
      if (isResizing === 'palette') {
        // Palette: min 250px, max matches content width (no arbitrary limit)
        const newWidth = Math.max(250, Math.min(400, e.clientX));
        setPaletteWidth(newWidth);
      } else if (isResizing === 'inspector') {
        const newWidth = Math.max(280, Math.min(600, window.innerWidth - e.clientX));
        setInspectorWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(null);
      document.body.classList.remove('resizing');
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.classList.remove('resizing');
    };
  }, [isResizing]);

  // Preload function registry on app mount
  useEffect(() => {
    fetchRegistry().then(() => {
      console.log('[APP] Function registry loaded');
    }).catch((error) => {
      console.error('[APP] Failed to load function registry:', error);
    });
  }, []);

  // When main tab changes, switch to first available subworkflow of that kind
  useEffect(() => {
    if (currentMainTab === 'parameters' || currentMainTab === 'results') return;

    const subworkflowsOfCurrentKind = Object.keys(workflow.subworkflows || {}).filter((name) => {
      const kind = workflow.metadata?.gui?.subworkflow_kinds?.[name] ||
                  (name === 'main' ? 'composer' : 'subworkflow');
      return currentMainTab === 'composers' ? kind === 'composer' : kind === 'subworkflow';
    });

    // If current stage is not in the filtered list, switch to the first one
    if (subworkflowsOfCurrentKind.length > 0 && !subworkflowsOfCurrentKind.includes(currentStage)) {
      setCurrentStage(subworkflowsOfCurrentKind[0]);
    }
  }, [currentMainTab, workflow.subworkflows, workflow.metadata, currentStage, setCurrentStage]);

  const handleImportWorkflow = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          try {
            const workflowData = JSON.parse(event.target.result);
            // Pass file path for library path resolution (Phase 6)
            // Note: file.path is only available in Electron, not in browser
            // Use file.name as fallback so Save button appears
            const filePath = file.path || file.name;
            loadWorkflow(workflowData, filePath);
            alert(`Workflow "${workflowData.name}" loaded successfully!`);
          } catch (error) {
            alert('Error loading workflow: ' + error.message);
          }
        };
        reader.readAsText(file);
      }
    };
    input.click();
  };

  const handleExportWorkflow = () => {
    // Phase 6: Prompt for workflow directory to enable relative path handling
    // Note: In browser, we can't get the actual save path, so we ask the user
    let workflowDir = null;

    if (workflow.metadata?.gui?.function_libraries?.length > 0) {
      workflowDir = prompt(
        'Enter the directory where you will save this workflow file:\n' +
        '(This is needed to make library paths relative)\n\n' +
        'Example: /Users/yourname/projects/workflows\n' +
        'or C:\\Users\\yourname\\projects\\workflows',
        ''
      );

      if (workflowDir) {
        // Store the workflow file path (directory + filename)
        const filename = `${workflow.name.replace(/\s+/g, '_').toLowerCase()}.json`;
        const fullPath = `${workflowDir}/${filename}`;
        setWorkflowFilePath(fullPath);
      }
    }

    const workflowData = exportWorkflow();
    const blob = new Blob([JSON.stringify(workflowData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflow.name.replace(/\s+/g, '_').toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);

    if (workflowDir) {
      alert(
        'Workflow exported!\n\n' +
        'Library paths have been made relative to the workflow directory.\n' +
        'Make sure to save the file in the directory you specified.'
      );
    }
  };

  // Store file handle for direct saving (File System Access API)
  const [fileHandle, setFileHandle] = useState(null);

  const handleSaveWorkflow = async () => {
    // Ask for confirmation before saving
    const confirmed = window.confirm(
      `Are you sure you want to save the current project?\n\n` +
      `File: ${workflowFilePath || 'New file'}\n\n` +
      `This will overwrite the existing file.`
    );

    if (!confirmed) {
      return;
    }

    try {
      const workflowData = exportWorkflow();
      const jsonContent = JSON.stringify(workflowData, null, 2);

      console.log('[SAVE] Workflow data to save:', workflowData);
      console.log('[SAVE] JSON content length:', jsonContent.length);

      // If we have a file handle from a previous save, use it
      if (fileHandle) {
        try {
          console.log('[SAVE] Using existing file handle:', fileHandle.name);
          const writable = await fileHandle.createWritable();
          await writable.write(jsonContent);
          await writable.close();
          console.log('[SAVE] Successfully wrote to file');
          alert(`Project saved successfully!\n\nFile: ${fileHandle.name}`);
          return;
        } catch (err) {
          console.log('[SAVE] Could not write to existing handle:', err);
        }
      }

      // Use File System Access API to let user pick save location
      if ('showSaveFilePicker' in window) {
        console.log('[SAVE] Using File System Access API');
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: workflowFilePath || `${workflow.name.replace(/\s+/g, '_').toLowerCase()}.json`,
            types: [{
              description: 'JSON Files',
              accept: { 'application/json': ['.json'] }
            }]
          });

          console.log('[SAVE] Got file handle:', handle.name);

          const writable = await handle.createWritable();
          await writable.write(jsonContent);
          await writable.close();

          console.log('[SAVE] Successfully wrote to new file');

          // Store the handle for future saves
          setFileHandle(handle);
          setWorkflowFilePath(handle.name);

          alert(`Project saved successfully!\n\nFile: ${handle.name}`);
        } catch (err) {
          if (err.name !== 'AbortError') {
            console.error('[SAVE] Save failed:', err);
            alert('Error saving project: ' + err.message);
          } else {
            console.log('[SAVE] User cancelled save dialog');
          }
        }
      } else {
        console.log('[SAVE] File System Access API not available, using download fallback');
        // Fallback for browsers without File System Access API
        const blob = new Blob([jsonContent], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = workflowFilePath || `${workflow.name.replace(/\s+/g, '_').toLowerCase()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        alert('Project downloaded. Please replace the original file manually.');
      }
    } catch (error) {
      console.error('[SAVE] Error:', error);
      alert('Error saving project: ' + error.message);
    }
  };

  const handleCreateSubWorkflow = () => {
    if (!newSubWorkflowName.trim()) {
      alert('Please enter a sub-workflow name');
      return;
    }

    // Validate name
    if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(newSubWorkflowName)) {
      alert('Invalid name. Must start with a letter and contain only letters, numbers, and underscores.');
      return;
    }

    addSubWorkflow(newSubWorkflowName.trim(), '');
    setNewSubWorkflowName('');
    setShowNewSubWorkflowDialog(false);
    setCurrentStage(newSubWorkflowName.trim());
  };

  const handleDeleteSubWorkflow = (name) => {
    if (name === 'main') {
      alert('Cannot delete main workflow');
      return;
    }

    if (confirm(`Are you sure you want to delete sub-workflow "${name}"?`)) {
      deleteSubWorkflow(name);
    }
  };

  const handleRenameSubWorkflow = (oldName, newName) => {
    if (!newName.trim() || newName === oldName) {
      setRenamingSubWorkflow(null);
      return;
    }

    // Validate name
    if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(newName)) {
      alert('Invalid name. Must start with a letter and contain only letters, numbers, and underscores.');
      return;
    }

    renameSubWorkflow(oldName, newName.trim());
    setRenamingSubWorkflow(null);
  };



  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <FileJson size={24} className="logo-icon" />
          <div className="header-title">
            <h1>OpenCellComms</h1>
            <p>{workflow.name}</p>
          </div>
        </div>

        <div className="header-actions">
          <button className="btn btn-secondary" onClick={handleImportWorkflow}>
            <Upload size={16} />
            Import Project
          </button>
          <button
            className="btn btn-success"
            onClick={handleSaveWorkflow}
            disabled={!workflowFilePath}
            title={workflowFilePath ? `Save to: ${workflowFilePath}` : 'Import a project first'}
          >
            <Save size={16} />
            Save Project
          </button>
          <button className="btn btn-primary" onClick={handleExportWorkflow}>
            <Download size={16} />
            Export Project
          </button>
        </div>
      </header>

      {/* Main Tab Selector */}
      <MainTabSelector
        currentMainTab={currentMainTab}
        onTabChange={setCurrentMainTab}
      />

      {/* === Workflow Designer View (Composers / Sub-workflows) === */}
      {(currentMainTab === 'composers' || currentMainTab === 'subworkflows') && (
        <>
          {/* Stage/Sub-workflow Tabs */}
          <div className="stage-tabs">
            {/* V2.0: Dynamic sub-workflow tabs filtered by kind */}
            {Object.keys(workflow.subworkflows || {})
              .filter((subworkflowName) => {
                const kind = workflow.metadata?.gui?.subworkflow_kinds?.[subworkflowName] ||
                            (subworkflowName === 'main' ? 'composer' : 'subworkflow');
                return currentMainTab === 'composers' ? kind === 'composer' : kind === 'subworkflow';
              })
              .map((subworkflowName) => {
                  const subworkflow = workflow.subworkflows[subworkflowName];
                  const isEnabled = subworkflow.enabled !== false;
                  const isDeletable = subworkflow.deletable !== false;
                  const isMain = subworkflowName === 'main';
                  const kind = workflow.metadata?.gui?.subworkflow_kinds?.[subworkflowName] ||
                              (subworkflowName === 'main' ? 'composer' : 'subworkflow');
                  const isComposer = kind === 'composer';

                  return (
                    <button
                      key={subworkflowName}
                      className={`stage-tab ${isComposer ? 'composer' : 'subworkflow'} ${currentStage === subworkflowName ? 'active' : ''} ${!isEnabled ? 'disabled' : ''}`}
                      onClick={() => setCurrentStage(subworkflowName)}
                      style={{
                        '--stage-color': isComposer ? '#10b981' : '#8b5cf6',
                      }}
                    >
                      <span className="stage-indicator" style={{ background: isComposer ? '#10b981' : '#8b5cf6' }} />
                      {renamingSubWorkflow === subworkflowName ? (
                        <input
                          type="text"
                          className="stage-rename-input"
                          defaultValue={subworkflowName}
                          autoFocus
                          onBlur={(e) => handleRenameSubWorkflow(subworkflowName, e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleRenameSubWorkflow(subworkflowName, e.target.value);
                            } else if (e.key === 'Escape') {
                              setRenamingSubWorkflow(null);
                            }
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <span className="stage-label">{subworkflowName}</span>
                      )}

                      {!isMain && isDeletable && (
                        <>
                          <span
                            className="stage-action-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              setRenamingSubWorkflow(subworkflowName);
                            }}
                            title="Rename sub-workflow"
                          >
                            <Edit2 size={12} />
                          </span>
                          <span
                            className="stage-action-btn delete"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteSubWorkflow(subworkflowName);
                            }}
                            title="Delete sub-workflow"
                          >
                            <X size={14} />
                          </span>
                        </>
                      )}
                    </button>
                  );
                })}

            {/* Add Composer/Sub-workflow Button */}
            <button
              className="stage-tab add-tab"
              onClick={() => setShowNewSubWorkflowDialog(true)}
              title={currentMainTab === 'composers' ? 'Add new composer' : 'Add new sub-workflow'}
            >
              <Plus size={16} />
              <span className="stage-label">
                {currentMainTab === 'composers' ? 'New Composer' : 'New Sub-workflow'}
              </span>
            </button>
          </div>

          {/* Main Content - Responsive Grid Layout */}
          {(() => {
            const inspectorOpen = inspector.isOpen;

            // Build dynamic grid template
            const gridStyle = {};
            if (inspectorOpen) {
              gridStyle.gridTemplateColumns = `${paletteWidth}px 1fr ${inspectorWidth}px`;
            } else {
              gridStyle.gridTemplateColumns = `${paletteWidth}px 1fr`;
            }

            return (
              <div className={`workflow-grid ${inspectorOpen ? 'with-inspector' : ''}`} style={gridStyle}>
                <div className="grid-palette">
                  <FunctionPalette currentStage={currentStage} />
                  <div className="resize-handle resize-handle-right" onMouseDown={handleMouseDown('palette')} />
                </div>
                <div className="grid-canvas">
                  <WorkflowCanvas key={currentStage} stage={currentStage} />
                </div>
                {/* Node Inspector - appears when open */}
                {inspectorOpen && (
                  <div className="grid-inspector">
                    <div className="resize-handle resize-handle-left" onMouseDown={handleMouseDown('inspector')} />
                    <NodeInspector />
                  </div>
                )}
              </div>
            );
          })()}
        </>
      )}

      {/* === Parameters Dashboard View === */}
      {currentMainTab === 'parameters' && (
        <div className="fullpage-content">
          <ParametersDashboard />
        </div>
      )}

      {/* === Results View === */}
      {currentMainTab === 'results' && (
        <div className="fullpage-content">
          <ResultsExplorer />
        </div>
      )}

      {/* New Composer/Sub-workflow Dialog */}
      {showNewSubWorkflowDialog && (
        <div className="dialog-overlay" onClick={() => setShowNewSubWorkflowDialog(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Create New {currentMainTab === 'composers' ? 'Composer' : 'Sub-workflow'}</h3>
            <input
              type="text"
              className="dialog-input"
              placeholder={currentMainTab === 'composers'
                ? 'Enter composer name (e.g., my_experiment)'
                : 'Enter sub-workflow name (e.g., my_workflow)'}
              value={newSubWorkflowName}
              onChange={(e) => setNewSubWorkflowName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleCreateSubWorkflow();
                } else if (e.key === 'Escape') {
                  setShowNewSubWorkflowDialog(false);
                }
              }}
              autoFocus
            />
            <div className="dialog-actions">
              <button className="btn btn-secondary" onClick={() => setShowNewSubWorkflowDialog(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleCreateSubWorkflow}>
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-info">
          <span>
            {workflow.version === '2.0' ? 'Sub-workflow' : 'Stage'}: {
              workflow.version === '2.0'
                ? currentStage
                : STAGES.find((s) => s.id === currentStage)?.label
            }
          </span>
          <span>•</span>
          <span>Version: {workflow.version}</span>
        </div>
        <div className="footer-hint">
          💡 Drag functions from the palette to the canvas • Double-click nodes to edit parameters
          {workflow.version === '2.0' && ' • Purple nodes with ⚡ icon are sub-workflow calls'}
        </div>
      </footer>
    </div>
  );
}

export default App;
