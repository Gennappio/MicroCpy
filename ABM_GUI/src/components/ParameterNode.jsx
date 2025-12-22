import React from 'react';
import { Handle, Position } from 'reactflow';
import { Database, Settings } from 'lucide-react';
import ParameterItem from './ParameterItem';
import './ParameterNode.css';

/**
 * Parameter Node - Stores parameters that can be connected to function nodes
 * Can display parameters as a compact preview or as individual items
 */
const ParameterNode = ({ data, selected }) => {
  const { label, parameters, onEdit, expandedView = false } = data;

  // Count number of parameters
  const paramCount = parameters ? Object.keys(parameters).length : 0;

  return (
    <div className={`parameter-node ${selected ? 'selected' : ''} ${expandedView ? 'expanded' : ''}`}>
      {/* Parameter output handle on RIGHT side - connects to function node's LEFT input */}
      <Handle
        type="source"
        position={Position.Right}
        id="params"
        className="parameter-handle"
      />

      <div className="param-node-header">
        <div className="param-node-icon">
          <Database size={14} />
        </div>
        <div className="param-node-title">
          {label}
        </div>
        {onEdit && (
          <button
            className="param-node-edit-btn"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            title="Edit parameters"
          >
            <Settings size={12} />
          </button>
        )}
      </div>

      <div className="param-node-count">
        {paramCount} parameter{paramCount !== 1 ? 's' : ''}
      </div>

      {parameters && Object.keys(parameters).length > 0 && (
        expandedView ? (
          <div className="param-node-expanded">
            {Object.entries(parameters).map(([key, value]) => (
              <ParameterItem key={key} paramKey={key} paramValue={value} />
            ))}
          </div>
        ) : (
          <div className="param-node-preview">
            {Object.entries(parameters).slice(0, 3).map(([key, value]) => (
              <div key={key} className="param-preview-item">
                <span className="param-key">{key}:</span>
                <span className="param-value">
                  {typeof value === 'object' ? JSON.stringify(value).slice(0, 20) : String(value).slice(0, 20)}
                  {String(value).length > 20 ? '...' : ''}
                </span>
              </div>
            ))}
            {Object.keys(parameters).length > 3 && (
              <div className="param-preview-more">
                +{Object.keys(parameters).length - 3} more
              </div>
            )}
          </div>
        )
      )}
    </div>
  );
};

export default ParameterNode;

