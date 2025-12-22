import React from 'react';
import './FunctionParameterGroup.css';

/**
 * Function Parameter Group - Visual container that groups a function node with its parameters
 * This component wraps function and parameter nodes in a rectangular container for better readability
 */
const FunctionParameterGroup = ({ children, functionName, paramCount }) => {
  return (
    <div className="function-parameter-group">
      <div className="group-header">
        <span className="group-title">{functionName}</span>
        {paramCount > 0 && (
          <span className="group-param-count">{paramCount} param{paramCount !== 1 ? 's' : ''}</span>
        )}
      </div>
      <div className="group-content">
        {children}
      </div>
    </div>
  );
};

export default FunctionParameterGroup;

