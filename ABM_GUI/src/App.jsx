import { useState, useEffect } from 'react';
import { Download, Upload, FileJson, BarChart3, Plus, X, Edit2, Play } from 'lucide-react';
import FunctionPalette from './components/FunctionPalette';
import WorkflowCanvas from './components/WorkflowCanvas';
import SimulationRunner from './components/SimulationRunner';
import ResultsExplorer from './components/ResultsExplorer';
import MainTabSelector from './components/MainTabSelector';
import useWorkflowStore from './store/workflowStore';
import { fetchRegistry } from './data/functionRegistry';
import './App.css';

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
        currentMainTab,
        setCurrentMainTab,
        workflow,
        loadWorkflow,
        exportWorkflow,
        addSubWorkflow,
        deleteSubWorkflow,
        renameSubWorkflow
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

          {/* Main Content */}
          <div className="app-content">
            <FunctionPalette currentStage={currentStage} />
            <WorkflowCanvas key={currentStage} stage={currentStage} />
          </div>
        </>
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

