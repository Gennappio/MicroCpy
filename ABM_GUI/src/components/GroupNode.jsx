import React from 'react';
import './GroupNode.css';

/**
 * Group Node - Visual container that groups a function node with its parameter nodes
 * Creates a rectangular border around related nodes for better readability
 */
const GroupNode = ({ data }) => {
  const { label, functionName, paramCount, description } = data;

  return (
    <div className="group-node">
      <div className="group-node-header">
        <div className="group-node-title-section">
          <span className="group-node-label">{label || functionName}</span>
          {paramCount > 0 && (
            <span className="group-node-badge">{paramCount} params</span>
          )}
        </div>
        {description && (
          <div className="group-node-description">
            {description}
          </div>
        )}
      </div>
    </div>
  );
};

export default GroupNode;

