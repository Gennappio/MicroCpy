import React, { useState, useEffect } from 'react';
import { Download, Upload, FileJson, Play, Pause, BarChart3, Plus, X, Edit2, Zap } from 'lucide-react';
import FunctionPalette from './components/FunctionPalette';
import WorkflowCanvas from './components/WorkflowCanvas';
import SimulationRunner from './components/SimulationRunner';
import ResultsExplorer from './components/ResultsExplorer';
import useWorkflowStore from './store/workflowStore';
import { fetchRegistry } from './data/functionRegistry';
import './App.css';

const STAGES = [
  { id: 'initialization', label: 'Initialization', color: '#10b981' },
  { id: 'macrostep', label: 'Macrostep', color: '#06b6d4' },
  { id: 'intracellular', label: 'Intracellular', color: '#3b82f6' },
  { id: 'microenvironment', label: 'Microenvironment', color: '#8b5cf6' },
  { id: 'intercellular', label: 'Intercellular', color: '#f59e0b' },
  { id: 'finalization', label: 'Finalization', color: '#ef4444' },
];

const VIEWS = [
  { id: 'workflow', label: 'Workflow Designer' },
  { id: 'run', label: 'Run Simulation', icon: Play },
  { id: 'results', label: 'Results', icon: BarChart3 },
];

function App() {
		  const [currentView, setCurrentView] = useState('workflow');
		  const {
        currentStage,
        setCurrentStage,
        workflow,
        loadWorkflow,
        exportWorkflow,
        toggleStageEnabled,
        setStageSteps,
        addSubWorkflow,
        deleteSubWorkflow,
        renameSubWorkflow,
        updateSubWorkflowDescription
      } = useWorkflowStore();

  const [showNewSubWorkflowDialog, setShowNewSubWorkflowDialog] = useState(false);
  const [newSubWorkflowName, setNewSubWorkflowName] = useState('');
  const [renamingSubWorkflow, setRenamingSubWorkflow] = useState(null);

  // Preload function registry on app mount
  useEffect(() => {
    fetchRegistry().then(() => {
      console.log('[APP] Function registry loaded');
    }).catch((error) => {
      console.error('[APP] Failed to load function registry:', error);
    });
  }, []);

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
            loadWorkflow(workflowData);
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
            <h1>MicroC Workflow Designer</h1>
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

      {/* View Tabs */}
      <div className="view-tabs">
        {VIEWS.map((view) => (
          <button
            key={view.id}
            className={`view-tab ${currentView === view.id ? 'active' : ''}`}
            onClick={() => setCurrentView(view.id)}
          >
            {view.icon && <view.icon size={16} />}
            {view.label}
          </button>
        ))}
      </div>

      {/* Workflow Designer View */}
      {currentView === 'workflow' && (
        <>
          {/* Stage/Sub-workflow Tabs */}
          <div className="stage-tabs">
            {workflow.version === '2.0' ? (
              // V2.0: Dynamic sub-workflow tabs
              <>
                {Object.keys(workflow.subworkflows || {}).map((subworkflowName) => {
                  const subworkflow = workflow.subworkflows[subworkflowName];
                  const isEnabled = subworkflow.enabled !== false;
                  const isDeletable = subworkflow.deletable !== false;
                  const isMain = subworkflowName === 'main';

                  return (
                    <button
                      key={subworkflowName}
                      className={`stage-tab ${currentStage === subworkflowName ? 'active' : ''} ${!isEnabled ? 'disabled' : ''}`}
                      onClick={() => setCurrentStage(subworkflowName)}
                      style={{
                        '--stage-color': isMain ? '#10b981' : '#8b5cf6',
                      }}
                    >
                      <span className="stage-indicator" style={{ background: isMain ? '#10b981' : '#8b5cf6' }} />
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

                {/* Add Sub-workflow Button */}
                <button
                  className="stage-tab add-tab"
                  onClick={() => setShowNewSubWorkflowDialog(true)}
                  title="Add new sub-workflow"
                >
                  <Plus size={16} />
                  <span className="stage-label">New Sub-workflow</span>
                </button>
              </>
            ) : (
              // V1.0: Fixed stage tabs
              STAGES.map((stage) => {
                const isEnabled = workflow.stages[stage.id]?.enabled !== false;
                return (
                  <button
                    key={stage.id}
                    className={`stage-tab ${currentStage === stage.id ? 'active' : ''} ${!isEnabled ? 'disabled' : ''}`}
                    onClick={() => setCurrentStage(stage.id)}
                    style={{
                      '--stage-color': stage.color,
                    }}
                  >
                    <span className="stage-indicator" style={{ background: stage.color }} />
                    <span className="stage-label">{stage.label}</span>
                    <span
                      className="stage-toggle-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleStageEnabled(stage.id);
                      }}
                      title={isEnabled ? 'Disable stage' : 'Enable stage'}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.stopPropagation();
                          toggleStageEnabled(stage.id);
                        }
                      }}
                    >
                      {isEnabled ? (
                        <Play size={14} className="stage-status enabled" />
                      ) : (
                        <Pause size={14} className="stage-status disabled" />
                      )}
                    </span>
                  </button>
                );
              })
            )}
          </div>

          {/* Main Content */}
          <div className="app-content">
            <FunctionPalette currentStage={currentStage} />
            <WorkflowCanvas key={currentStage} stage={currentStage} />
          </div>
        </>
      )}

      {/* New Sub-workflow Dialog */}
      {showNewSubWorkflowDialog && (
        <div className="dialog-overlay" onClick={() => setShowNewSubWorkflowDialog(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Create New Sub-workflow</h3>
            <input
              type="text"
              className="dialog-input"
              placeholder="Enter sub-workflow name (e.g., my_workflow)"
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

      {/* Run Simulation View */}
      {currentView === 'run' && (
        <div className="app-content-full">
          <SimulationRunner />
        </div>
      )}

      {/* Results View */}
      {currentView === 'results' && (
        <div className="app-content-full">
          <ResultsExplorer />
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

