import React from 'react';
import { Handle, Position } from 'reactflow';
import { List, Settings } from 'lucide-react';
import './ListParameterNode.css';

/**
 * List Parameter Node - Stores a list of values (strings or floats)
 * 
 * Props:
 *   data.label: Display name
 *   data.listType: 'string' or 'float'
 *   data.items: Array of values
 *   data.onEdit: Callback when edit button is clicked
 */
const ListParameterNode = ({ data, selected }) => {
  const { label, listType = 'string', items = [], onEdit } = data;

  // Format item for display
  const formatItem = (item, index) => {
    if (typeof item === 'object' && item !== null) {
      // Nested structure - show type indicator
      if (Array.isArray(item)) {
        return `[list: ${item.length} items]`;
      }
      return `{dict: ${Object.keys(item).length} keys}`;
    }
    const strVal = String(item);
    return strVal.length > 20 ? strVal.substring(0, 17) + '...' : strVal;
  };

  const typeLabel = listType === 'float' ? 'Float' : 'String';
  const typeColor = listType === 'float' ? '#10b981' : '#8b5cf6';

  return (
    <div className={`list-parameter-node ${selected ? 'selected' : ''}`} style={{ borderColor: typeColor }}>
      {/* List output handle on RIGHT side */}
      <Handle
        type="source"
        position={Position.Right}
        id="list-out"
        className="list-handle"
        style={{ background: typeColor }}
      />

      <div className="list-node-header">
        <div className="list-node-icon" style={{ color: typeColor }}>
          <List size={14} />
          <span className="list-brackets">[  ]</span>
        </div>
        <div className="list-node-title">
          {label || `${typeLabel} List`}
        </div>
        {onEdit && (
          <button
            className="list-node-edit-btn"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            title="Edit list"
          >
            <Settings size={12} />
          </button>
        )}
      </div>

      <div className="list-node-type-badge" style={{ background: typeColor }}>
        {typeLabel} List
      </div>

      <div className="list-node-count">
        {items.length} item{items.length !== 1 ? 's' : ''}
      </div>

      {/* Preview of items */}
      {items.length > 0 && (
        <div className="list-node-preview">
          {items.slice(0, 3).map((item, index) => (
            <div key={index} className="list-preview-item">
              <span className="list-index">[{index}]</span>
              <span className="list-value">{formatItem(item, index)}</span>
            </div>
          ))}
          {items.length > 3 && (
            <div className="list-preview-more">
              +{items.length - 3} more...
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ListParameterNode;

