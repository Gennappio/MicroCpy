import React from 'react';
import { Handle, Position } from 'reactflow';
import { Settings, Play, Pause, FileCode } from 'lucide-react';
import './WorkflowFunctionNode.css';

/**
 * Custom node component for workflow functions
 */
const WorkflowFunctionNode = ({ data, selected }) => {
  const { label, functionName, enabled, description, onEdit, functionFile, parameters, customName } = data;

  // Get function file from data or parameters
  const filePath = functionFile || parameters?.function_file || '';
  const fileName = filePath ? filePath.split('/').pop() : '';

  // Determine display name and whether to show template indicator
  const isTemplate = !customName;
  const displayName = customName || label;

  return (
    <div className={`workflow-function-node ${!enabled ? 'disabled' : ''} ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Top} />

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

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default WorkflowFunctionNode;

