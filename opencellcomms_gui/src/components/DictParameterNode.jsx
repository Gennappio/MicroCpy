import React from 'react';
import { Handle, Position } from 'reactflow';
import { Braces, Settings } from 'lucide-react';
import './DictParameterNode.css';

/**
 * Dictionary Parameter Node - Stores key-value pairs with typed values
 * 
 * Props:
 *   data.label: Display name
 *   data.entries: Array of { key, value, valueType } objects
 *   data.onEdit: Callback when edit button is clicked
 */
const DictParameterNode = ({ data, selected }) => {
  const { label, entries = [], onEdit } = data;

  // Format value for display based on type
  const formatValue = (entry) => {
    const { value, valueType } = entry;
    if (valueType === 'list') {
      if (Array.isArray(value)) {
        return `[list: ${value.length} items]`;
      }
      return '[list]';
    }
    if (valueType === 'dict') {
      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        return `{dict: ${Object.keys(value).length} keys}`;
      }
      return '{dict}';
    }
    const strVal = String(value);
    return strVal.length > 15 ? strVal.substring(0, 12) + '...' : strVal;
  };

  // Get type badge color
  const getTypeColor = (valueType) => {
    switch (valueType) {
      case 'float': return '#10b981';
      case 'int': return '#3b82f6';
      case 'bool': return '#f59e0b';
      case 'list': return '#8b5cf6';
      case 'dict': return '#ec4899';
      default: return '#6b7280'; // string
    }
  };

  return (
    <div className={`dict-parameter-node ${selected ? 'selected' : ''}`}>
      {/* Dict output handle on RIGHT side */}
      <Handle
        type="source"
        position={Position.Right}
        id="dict-out"
        className="dict-handle"
      />

      <div className="dict-node-header">
        <div className="dict-node-icon">
          <Braces size={14} />
          <span className="dict-braces">{"{ }"}</span>
        </div>
        <div className="dict-node-title">
          {label || 'Dictionary'}
        </div>
        {onEdit && (
          <button
            className="dict-node-edit-btn"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            title="Edit dictionary"
          >
            <Settings size={12} />
          </button>
        )}
      </div>

      <div className="dict-node-type-badge">
        Dictionary
      </div>

      <div className="dict-node-count">
        {entries.length} entr{entries.length !== 1 ? 'ies' : 'y'}
      </div>

      {/* Preview of entries */}
      {entries.length > 0 && (
        <div className="dict-node-preview">
          {entries.slice(0, 3).map((entry, index) => (
            <div key={index} className="dict-preview-item">
              <span className="dict-key">{entry.key}:</span>
              <span 
                className="dict-type-indicator" 
                style={{ background: getTypeColor(entry.valueType) }}
              >
                {entry.valueType}
              </span>
              <span className="dict-value">{formatValue(entry)}</span>
            </div>
          ))}
          {entries.length > 3 && (
            <div className="dict-preview-more">
              +{entries.length - 3} more...
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DictParameterNode;

