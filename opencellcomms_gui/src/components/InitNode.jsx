import { Handle, Position } from 'reactflow';
import { Zap, Settings, Code2 } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import { BEHAVIOR_KINDS } from '../store/subworkflowKinds';
import './InitNode.css';

const InitNode = ({ id, data, selected }) => {
  const label = data?.label || 'INIT';
  const { workflow, currentStage } = useWorkflowStore();

  // Determine if the current subworkflow is a behavior (agent/env/processing)
  const currentKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage];
  const isBehaviorCanvas = BEHAVIOR_KINDS.has(currentKind);

  // Check if this is the macrostep controller (needs "Number of steps" parameter)
  const isMacrostepController = id.includes('macrostep');

  // Get the number of steps value (default to 1)
  const numberOfSteps = data?.numberOfSteps || 1;

  // Check if the parameter is connected to a parameter node
  const isParameterConnected = data?.isStepsParameterConnected || false;

  // Get the connected parameter value (if connected)
  const connectedParameterValue = data?.connectedStepsValue;

  const handleGenerateCode = async () => {
    const sw = workflow.subworkflows?.[currentStage];
    if (!sw) return;

    const functions = (sw.functions || []).map((f) => ({ name: f.function_name }));
    if (functions.length === 0) {
      alert('Add function nodes to this behavior before generating code.');
      return;
    }

    const categoryGuess = currentKind === 'agent_behavior' ? 'intracellular' : 'diffusion';
    const category = prompt(
      `Target category for ${currentStage}?\n(initialization / intracellular / diffusion / intercellular / finalization / output)`,
      categoryGuess
    );
    if (!category) return;

    const adapter = prompt('Adapter name (leave blank for generic engine functions):', 'jayatilake');

    try {
      const res = await fetch('http://localhost:5001/api/function/scaffold', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ behavior_name: currentStage, category, adapter: adapter || null, functions }),
      });
      const data = await res.json();
      if (data.success) {
        alert(`Code generated: ${data.file_path}\nAdded: ${data.added_functions?.join(', ') || 'none'}\nSkipped (existing): ${data.skipped_existing?.join(', ') || 'none'}`);
      } else {
        alert('Error: ' + data.error);
      }
    } catch (e) {
      alert('Failed to reach backend: ' + e.message);
    }
  };

  return (
    <div className={`init-node ${selected ? 'selected' : ''}`}>
      <div className="init-settings-icon">
        <Settings size={16} />
      </div>

      <div className="init-node-content">
        <Zap size={24} className="init-icon" />
        <span className="init-label">{label}</span>
      </div>

      {/* Generate code button — only on behavior canvases */}
      {isBehaviorCanvas && (
        <button
          className="init-generate-btn"
          onClick={handleGenerateCode}
          title="Generate Python file for this behavior"
        >
          <Code2 size={13} />
          Generate Code
        </button>
      )}

      {/* Number of steps parameter (only for macrostep controller) */}
      {isMacrostepController && (
        <div className="init-parameter-section">
          <div className={`init-parameter-row ${isParameterConnected ? 'connected' : ''}`}>
            <Handle
              type="target"
              position={Position.Left}
              id="steps-param"
              className="init-parameter-handle"
              style={{
                background: '#3b82f6',
                width: '10px',
                height: '10px',
                border: '2px solid white',
                left: '-5px',
              }}
            />
            <span className="init-parameter-label">
              Number of steps: {isParameterConnected && connectedParameterValue !== undefined ? connectedParameterValue : numberOfSteps}
            </span>
          </div>
        </div>
      )}

      {/* Output handle - connects to first function in execution chain */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="init-out"
        className="init-handle-output"
        style={{
          background: '#dc2626',
          width: '12px',
          height: '12px',
          border: '3px solid white',
        }}
      />
    </div>
  );
};

export default InitNode;

