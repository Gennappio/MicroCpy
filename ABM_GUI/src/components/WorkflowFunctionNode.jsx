import { useState, useEffect } from 'react';
import { Handle, Position, useEdges, useNodes } from 'reactflow';
import { Settings, Play, Pause, FileCode } from 'lucide-react';
import { getFunction, getFunctionAsync } from '../data/functionRegistry';
import useWorkflowStore from '../store/workflowStore';
import './WorkflowFunctionNode.css';

/**
 * Custom node component for workflow functions
 */
const WorkflowFunctionNode = ({ id, data, selected }) => {
  const toggleFunctionEnabled = useWorkflowStore((state) => state.toggleFunctionEnabled);
  const edges = useEdges(); // Use reactflow's useEdges hook
  const nodes = useNodes(); // Use reactflow's useNodes hook to get parameter node labels
  const [functionMetadata, setFunctionMetadata] = useState(null);

  const { label, functionName, enabled, onEdit, functionFile, parameters, customName, isCustom, stepCount } = data;

  // Load function metadata asynchronously to ensure registry is loaded
  useEffect(() => {
    const loadMetadata = async () => {
      const metadata = await getFunctionAsync(functionName);
      setFunctionMetadata(metadata || { inputs: [], outputs: [], parameters: [] });
    };
    // Try sync first (if cache is ready), otherwise async
    const syncMetadata = getFunction(functionName);
    if (syncMetadata) {
      setFunctionMetadata(syncMetadata);
    } else {
      loadMetadata();
    }
  }, [functionName]);

  // Get function file from data or parameters
  const filePath = functionFile || parameters?.function_file || '';
  const fileName = filePath ? filePath.split('/').pop() : '';

  // Determine display name and whether to show template indicator
  const isTemplate = !customName && !isCustom;
  const displayName = customName || label;

  // Get parameter definitions from function metadata - these define the sockets
  const parameterDefs = functionMetadata?.parameters || [];

  // Find which parameter nodes are connected and which parameters they provide
  // Build a map from parameter name to the node that provides it
  const parameterToNode = {};
  (edges || [])
    .filter(edge => edge.target === id && edge.targetHandle?.startsWith('params-'))
    .forEach(edge => {
      const paramNode = (nodes || []).find(n => n.id === edge.source);
      if (paramNode && paramNode.data && paramNode.data.parameters) {
        // This parameter node provides all the parameters in its data.parameters object
        Object.keys(paramNode.data.parameters).forEach(paramName => {
          parameterToNode[paramName] = {
            id: edge.source,
            label: paramNode.data.label || edge.source,
          };
        });
      }
    });

  const handleToggleEnabled = (e) => {
    e.stopPropagation();
    toggleFunctionEnabled(id);
  };

  return (
    <div className={`workflow-function-node ${!enabled ? 'disabled' : ''} ${selected ? 'selected' : ''} ${isCustom ? 'custom' : ''}`}>
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

      {/* Parameter labels and handles section - based on function metadata */}
      {parameterDefs.length > 0 && (
        <div className="node-parameters">
          {parameterDefs.map((param, index) => {
            const handleId = `params-${index}`;
            const isConnected = parameterToNode[param.name];

            return (
              <div key={`param-${param.name}`} className={`parameter-row ${isConnected ? 'connected' : 'disconnected'}`}>
                <Handle
                  type="target"
                  position={Position.Left}
                  id={handleId}
                  className="parameter-handle-input"
                  style={{ top: 'auto' }}
                  title={isConnected ? `Provided by: ${isConnected.label}` : (param.description || param.name)}
                />
                <span className="parameter-label" title={param.description}>
                  {param.name}
                  {!isConnected && param.required !== false && <span className="required-indicator">*</span>}
                </span>
              </div>
            );
          })}
        </div>
      )}

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

