import React from 'react';
import './ParameterItem.css';

/**
 * Parameter Item - Individual parameter display
 * Shows a single parameter with its key and value
 */
const ParameterItem = ({ paramKey, paramValue, onEdit }) => {
  const displayValue = typeof paramValue === 'object' 
    ? JSON.stringify(paramValue) 
    : String(paramValue);

  return (
    <div className="parameter-item">
      <div className="param-item-key">{paramKey}</div>
      <div className="param-item-value" title={displayValue}>
        {displayValue.length > 40 ? displayValue.slice(0, 40) + '...' : displayValue}
      </div>
      {onEdit && (
        <button className="param-item-edit" onClick={onEdit} title="Edit parameter">
          ✎
        </button>
      )}
    </div>
  );
};

export default ParameterItem;

