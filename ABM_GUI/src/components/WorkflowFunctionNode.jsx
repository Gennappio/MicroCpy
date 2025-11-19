import React from 'react';
import { Handle, Position } from 'reactflow';
import { Settings, Play, Pause, FileCode } from 'lucide-react';
import './WorkflowFunctionNode.css';

/**
 * Custom node component for workflow functions
 */
const WorkflowFunctionNode = ({ data, selected }) => {
  const { label, functionName, enabled, description, onEdit, functionFile, parameters, customName, isCustom, stepCount } = data;

  // Get function file from data or parameters
  const filePath = functionFile || parameters?.function_file || '';
  const fileName = filePath ? filePath.split('/').pop() : '';

  // Determine display name and whether to show template indicator
  const isTemplate = !customName && !isCustom;
  const displayName = customName || label;

  return (
    <div className={`workflow-function-node ${!enabled ? 'disabled' : ''} ${selected ? 'selected' : ''} ${isCustom ? 'custom' : ''}`}>
      {/* Function flow handles (top and bottom) */}
      <Handle type="target" position={Position.Top} id="func-in" className="function-handle" />

      {/* Parameter input handle (left side, blue) */}
      <Handle
        type="target"
        position={Position.Left}
        id="params"
        className="parameter-handle-input"
        style={{ top: '50%' }}
      />

      <div className="node-header">
        <div className="node-status">
          {enabled ? (
            <Play size={14} className="status-icon enabled" />
          ) : (
            <Pause size={14} className="status-icon disabled" />
          )}
        </div>
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

      <Handle type="source" position={Position.Bottom} id="func-out" className="function-handle" />
    </div>
  );
};

export default WorkflowFunctionNode;

