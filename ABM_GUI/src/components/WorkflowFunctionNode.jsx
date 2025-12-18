import React from 'react';
import { Handle, Position } from 'reactflow';
import { Settings, Play, Pause, FileCode } from 'lucide-react';
import { getFunction } from '../data/functionRegistry';
import useWorkflowStore from '../store/workflowStore';
import './WorkflowFunctionNode.css';

/**
 * Custom node component for workflow functions
 */
const WorkflowFunctionNode = ({ id, data, selected }) => {
  const toggleFunctionEnabled = useWorkflowStore((state) => state.toggleFunctionEnabled);

  const { label, functionName, enabled, description, onEdit, functionFile, parameters, customName, isCustom, stepCount } = data;

  // Get function metadata to know inputs/outputs
  const functionMetadata = getFunction(functionName) || { inputs: [], outputs: [], parameters: [] };

  // Get function file from data or parameters
  const filePath = functionFile || parameters?.function_file || '';
  const fileName = filePath ? filePath.split('/').pop() : '';

  // Determine display name and whether to show template indicator
  const isTemplate = !customName && !isCustom;
  const displayName = customName || label;

  // Get parameter definitions from metadata
  const parameterDefs = functionMetadata.parameters || [];

  const handleToggleEnabled = (e) => {
    e.stopPropagation();
    toggleFunctionEnabled(id);
  };

  return (
    <div className={`workflow-function-node ${!enabled ? 'disabled' : ''} ${selected ? 'selected' : ''} ${isCustom ? 'custom' : ''}`}>
      {/* Function flow handles (top and bottom) */}
      <Handle type="target" position={Position.Top} id="func-in" className="function-handle" />

      {/* General parameter input handle on LEFT side */}
      <Handle
        type="target"
        position={Position.Left}
        id="params"
        className="parameter-handle-input"
        style={{ top: '50%' }}
        title="Parameter input"
      />

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

      {description && (
        <div className="node-description">{description}</div>
      )}

      {/* Parameter labels and handles section */}
      {parameterDefs.length > 0 && (
        <div className="node-parameters">
          {parameterDefs.map((param) => (
            <div key={`param-${param.name}`} className="parameter-row">
              <Handle
                type="target"
                position={Position.Left}
                id={`param-${param.name}`}
                className="parameter-handle-input"
                style={{ top: 'auto', left: '-6px' }}
                title={param.description || param.name}
              />
              <span className="parameter-label">{param.name}</span>
            </div>
          ))}
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

