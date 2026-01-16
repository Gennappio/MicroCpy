import { useState, useEffect } from 'react';
import { Download, Upload, FileJson, Plus, X, Edit2 } from 'lucide-react';
import FunctionPalette from './components/FunctionPalette';
import WorkflowCanvas from './components/WorkflowCanvas';
import WorkflowConsole from './components/WorkflowConsole';
import WorkflowResults from './components/WorkflowResults';
import NodeInspector from './components/NodeInspector';
import MainTabSelector from './components/MainTabSelector';
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
        addSubWorkflow,
        deleteSubWorkflow,
        renameSubWorkflow,
        inspector,
      } = useWorkflowStore();

  const [showNewSubWorkflowDialog, setShowNewSubWorkflowDialog] = useState(false);
  const [newSubWorkflowName, setNewSubWorkflowName] = useState('');
  const [renamingSubWorkflow, setRenamingSubWorkflow] = useState(null);

  // Resizable panel widths
  const [paletteWidth, setPaletteWidth] = useState(280);
  const [inspectorWidth, setInspectorWidth] = useState(320);
  const [consoleWidth, setConsoleWidth] = useState(380);
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
        const newWidth = Math.max(200, Math.min(500, e.clientX));
        setPaletteWidth(newWidth);
      } else if (isResizing === 'inspector') {
        const newWidth = Math.max(280, Math.min(600, window.innerWidth - e.clientX));
        setInspectorWidth(newWidth);
      } else if (isResizing === 'console') {
        const newWidth = Math.max(300, Math.min(600, window.innerWidth - e.clientX));
        setConsoleWidth(newWidth);
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
            const filePath = file.path || null;
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
            <h1>BioComposer</h1>
            <p>{workflow.name}</p>
          </div>
        </div>

        <div className="header-actions">
          <button className="btn btn-secondary" onClick={handleImportWorkflow}>
            <Upload size={16} />
            Import JSON
          </button>
          <button className="btn btn-primary" onClick={handleExportWorkflow}>
            <Download size={16} />
            Export JSON
          </button>
        </div>
      </header>

      {/* Main Tab Selector */}
      <MainTabSelector
        currentMainTab={currentMainTab}
        onTabChange={setCurrentMainTab}
      />

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
            const currentKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage] ||
                               (currentStage === 'main' ? 'composer' : 'subworkflow');
            const isComposer = currentKind === 'composer';
            const inspectorOpen = inspector.isOpen;

            // Build dynamic grid template
            const gridStyle = {};
            if (isComposer && inspectorOpen) {
              gridStyle.gridTemplateColumns = `${paletteWidth}px 1fr ${inspectorWidth}px ${consoleWidth}px`;
            } else if (isComposer) {
              gridStyle.gridTemplateColumns = `${paletteWidth}px 1fr ${consoleWidth}px`;
            } else if (inspectorOpen) {
              gridStyle.gridTemplateColumns = `${paletteWidth}px 1fr ${inspectorWidth}px`;
            } else {
              gridStyle.gridTemplateColumns = `${paletteWidth}px 1fr`;
            }

            return (
              <div className={`workflow-grid ${isComposer ? 'composer-layout' : 'subworkflow-layout'} ${inspectorOpen ? 'with-inspector' : ''}`} style={gridStyle}>
                <div className="grid-palette">
                  <FunctionPalette currentStage={currentStage} />
                  <div className="resize-handle resize-handle-right" onMouseDown={handleMouseDown('palette')} />
                </div>
                <div className="grid-canvas">
                  <WorkflowCanvas key={currentStage} stage={currentStage} />
                </div>
                {isComposer && (
                  <>
                    <div className="grid-console">
                      <div className="resize-handle resize-handle-left" onMouseDown={handleMouseDown('console')} />
                      <WorkflowConsole workflowName={currentStage} />
                    </div>
                    <div className="grid-results">
                      <WorkflowResults
                        subworkflowName={currentStage}
                        subworkflowKind={currentKind}
                      />
                    </div>
                  </>
                )}
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

