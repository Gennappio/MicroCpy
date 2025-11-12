import React, { useState } from 'react';
import { Download, Upload, FileJson, Play } from 'lucide-react';
import FunctionPalette from './components/FunctionPalette';
import WorkflowCanvas from './components/WorkflowCanvas';
import SimulationRunner from './components/SimulationRunner';
import useWorkflowStore from './store/workflowStore';
import './App.css';

const STAGES = [
  { id: 'initialization', label: 'Initialization', color: '#10b981' },
  { id: 'intracellular', label: 'Intracellular', color: '#3b82f6' },
  { id: 'diffusion', label: 'Diffusion', color: '#8b5cf6' },
  { id: 'intercellular', label: 'Intercellular', color: '#f59e0b' },
  { id: 'finalization', label: 'Finalization', color: '#ef4444' },
];

const VIEWS = [
  { id: 'workflow', label: 'Workflow Designer' },
  { id: 'run', label: 'Run Simulation', icon: Play },
];

function App() {
  const [currentView, setCurrentView] = useState('workflow');
  const { currentStage, setCurrentStage, workflow, loadWorkflow, exportWorkflow, stageNodes, setStageNodes } =
    useWorkflowStore();

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

  const handleCustomFunctionCreate = (customFunction) => {
    // Create a new node for the custom function
    const newId = `${customFunction.functionName}_${Date.now()}`;
    const newNode = {
      id: newId,
      type: 'workflowFunction',
      position: { x: 250, y: 100 + (stageNodes[currentStage]?.length || 0) * 100 },
      data: {
        label: customFunction.functionName,
        functionName: customFunction.functionName,
        parameters: customFunction.parameters,
        enabled: true,
        description: customFunction.description,
        functionFile: customFunction.parameters.function_file || '',
        isCustom: true,
        onEdit: null, // Will be set by WorkflowCanvas
      },
    };

    // Add node to current stage
    const currentNodes = stageNodes[currentStage] || [];
    setStageNodes(currentStage, [...currentNodes, newNode]);
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
          {/* Stage Tabs */}
          <div className="stage-tabs">
            {STAGES.map((stage) => (
              <button
                key={stage.id}
                className={`stage-tab ${currentStage === stage.id ? 'active' : ''}`}
                onClick={() => setCurrentStage(stage.id)}
                style={{
                  '--stage-color': stage.color,
                }}
              >
                <span className="stage-indicator" style={{ background: stage.color }} />
                {stage.label}
              </button>
            ))}
          </div>

          {/* Main Content */}
          <div className="app-content">
            <FunctionPalette
              currentStage={currentStage}
              onCustomFunctionCreate={handleCustomFunctionCreate}
            />
            <WorkflowCanvas key={currentStage} stage={currentStage} />
          </div>
        </>
      )}

      {/* Run Simulation View */}
      {currentView === 'run' && (
        <div className="app-content-full">
          <SimulationRunner />
        </div>
      )}

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-info">
          <span>Stage: {STAGES.find((s) => s.id === currentStage)?.label}</span>
          <span>•</span>
          <span>Version: {workflow.version}</span>
        </div>
        <div className="footer-hint">
          💡 Drag functions from the palette to the canvas • Double-click nodes to edit parameters
        </div>
      </footer>
    </div>
  );
}

export default App;

