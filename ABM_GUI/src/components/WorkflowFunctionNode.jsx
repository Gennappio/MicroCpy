import { Handle, Position, useEdges, useNodes } from 'reactflow';
import { Settings, Play, Pause, FileCode } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './WorkflowFunctionNode.css';

/**
 * Custom node component for workflow functions
 */
const WorkflowFunctionNode = ({ id, data, selected }) => {
  const toggleFunctionEnabled = useWorkflowStore((state) => state.toggleFunctionEnabled);
  const edges = useEdges(); // Use reactflow's useEdges hook
  const nodes = useNodes(); // Use reactflow's useNodes hook to get parameter node labels

  const { label, functionName, enabled, onEdit, functionFile, parameters, customName, isCustom, stepCount } = data;

  // Get function file from data or parameters
  const filePath = functionFile || parameters?.function_file || '';
  const fileName = filePath ? filePath.split('/').pop() : '';

  // Determine display name and whether to show template indicator
  const isTemplate = !customName && !isCustom;
  const displayName = customName || label;

  // Note: We no longer use parameterDefs directly since we create handles
  // based on incoming edges, not function metadata

  const handleToggleEnabled = (e) => {
    e.stopPropagation();
    toggleFunctionEnabled(id);
  };

  return (
    <div
      className={`workflow-function-node ${!enabled ? 'disabled' : ''} ${selected ? 'selected' : ''} ${isCustom ? 'custom' : ''}`}
      style={{ width: '350px', padding: '8px', fontSize: '13px' }}
    >
      {/* Function flow handles (top and bottom) */}
      <Handle type="target" position={Position.Top} id="func-in" className="function-handle" />

      <div className="node-header">
        <button
          className="node-status"
          onClick={handleToggleEnabled}
          title={enabled ? 'Disable node' : 'Enable node'}
        >
          {enabled ? (
            <Play size={14} className="status-icon enabled" />
          ) : (
            <Pause size={14} className="status-icon disabled" />
          )}
        </button>
        <div className="node-title">
          {displayName}
          {isTemplate && <span className="template-badge">(template)</span>}
          {isCustom && <span className="custom-badge-small">CUSTOM</span>}
        </div>
        {onEdit && (
          <button
            className="node-edit-btn"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            title="Edit parameters"
          >
            <Settings size={14} />
          </button>
        )}
      </div>

      {/* Description hidden - only visible in settings dialog */}

      {/* Parameter handles section - create handles for incoming parameter connections */}
      {/* We need handles that match the targetHandle IDs used in edges (params-0, params-1, etc.) */}
      <div className="node-parameters">
        {/* Create handles for each connected parameter node (by index) */}
        {(edges || [])
          .filter(edge => edge.target === id && edge.targetHandle?.startsWith('params-'))
          .map((edge) => {
            const handleId = edge.targetHandle; // Use the exact handle ID from the edge
            const paramNode = (nodes || []).find(n => n.id === edge.source);
            const paramLabel = paramNode?.data?.label || 'Parameters';
            // Get the parameter names from the connected node
            const paramNames = paramNode?.data?.parameters
              ? Object.keys(paramNode.data.parameters).join(', ')
              : '';

            return (
              <div key={`param-handle-${handleId}`} className="parameter-row connected">
                <Handle
                  type="target"
                  position={Position.Left}
                  id={handleId}
                  className="parameter-handle-input"
                  style={{
                    top: 'auto',
                    background: '#3b82f6',
                    backgroundColor: '#3b82f6',
                    width: '8px',
                    height: '8px',
                    border: '2px solid white',
                    left: '-16px'
                  }}
                  title={`From: ${paramLabel}`}
                />
                <span className="parameter-label" title={paramNames}>
                  {paramLabel.replace(' Parameters', '').substring(0, 20)}
                  {paramLabel.length > 20 ? '...' : ''}
                </span>
              </div>
            );
          })}
      </div>

      <div className="node-function-name">{functionName}</div>

      {fileName && (
        <div className="node-file-path" title={filePath}>
          <FileCode size={12} />
          <span>{fileName}</span>
        </div>
      )}

      {stepCount && stepCount > 1 && (
        <div className="node-step-count" title="Number of times this function executes">
          Steps: {stepCount}
        </div>
      )}

      {/* Function flow output handle on BOTTOM only - no right-side handles */}
      <Handle type="source" position={Position.Bottom} id="func-out" className="function-handle" />
    </div>
  );
};

export default WorkflowFunctionNode;

