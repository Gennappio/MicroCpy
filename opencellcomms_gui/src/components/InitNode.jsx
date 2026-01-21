import { Handle, Position } from 'reactflow';
import { Zap, Settings } from 'lucide-react';
import './InitNode.css';

/**
 * Init Node - The starting point for execution flow
 * Only nodes connected (directly or indirectly) to Init will be executed
 * This node cannot be deleted and is always present in every stage
 */
const InitNode = ({ id, data, selected }) => {
  // Use custom label from data, or default to "INIT"
  const label = data?.label || 'INIT';

  // Check if this is the macrostep controller (needs "Number of steps" parameter)
  const isMacrostepController = id.includes('macrostep');

  // Get the number of steps value (default to 1)
  const numberOfSteps = data?.numberOfSteps || 1;

  // Check if the parameter is connected to a parameter node
  const isParameterConnected = data?.isStepsParameterConnected || false;

  // Get the connected parameter value (if connected)
  const connectedParameterValue = data?.connectedStepsValue;

  return (
    <div className={`init-node ${selected ? 'selected' : ''}`}>
      {/* Settings icon in top-right corner */}
      <div className="init-settings-icon">
        <Settings size={16} />
      </div>

      <div className="init-node-content">
        <Zap size={24} className="init-icon" />
        <span className="init-label">{label}</span>
      </div>

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

