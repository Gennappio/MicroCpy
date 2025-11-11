import React, { useState, useEffect } from 'react';
import { X, Save, Edit2 } from 'lucide-react';
import { getFunction } from '../data/functionRegistry';
import './ParameterEditor.css';

/**
 * Parameter Editor Modal - Edit function parameters
 */
const ParameterEditor = ({ node, onSave, onClose }) => {
  const functionMetadata = getFunction(node.data.functionName);
  const [parameters, setParameters] = useState(node.data.parameters || {});
  const [customName, setCustomName] = useState(node.data.customName || '');

  useEffect(() => {
    setParameters(node.data.parameters || {});
    setCustomName(node.data.customName || '');
  }, [node]);

  const handleChange = (paramName, value) => {
    setParameters((prev) => ({
      ...prev,
      [paramName]: value,
    }));
  };

  const handleSave = () => {
    onSave(parameters, customName);
  };

  const renderParameterInput = (param) => {
    const value = parameters[param.name] ?? param.default;

    switch (param.type) {
      case 'integer':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => handleChange(param.name, parseInt(e.target.value, 10))}
            min={param.min}
            max={param.max}
            step={1}
            className="param-input"
          />
        );

      case 'float':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => handleChange(param.name, parseFloat(e.target.value))}
            min={param.min}
            max={param.max}
            step="any"
            className="param-input"
          />
        );

      case 'string':
        if (param.options) {
          return (
            <select
              value={value}
              onChange={(e) => handleChange(param.name, e.target.value)}
              className="param-input"
            >
              {param.options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          );
        }
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleChange(param.name, e.target.value)}
            className="param-input"
          />
        );

      case 'boolean':
        return (
          <input
            type="checkbox"
            checked={value}
            onChange={(e) => handleChange(param.name, e.target.checked)}
            className="param-checkbox"
          />
        );

      default:
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleChange(param.name, e.target.value)}
            className="param-input"
          />
        );
    }
  };

  if (!functionMetadata) {
    return null;
  }

  return (
    <div className="parameter-editor-overlay" onClick={onClose}>
      <div className="parameter-editor" onClick={(e) => e.stopPropagation()}>
        <div className="editor-header">
          <h3>{functionMetadata.displayName}</h3>
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="editor-description">{functionMetadata.description}</div>

        <div className="editor-content">
          {/* Custom Name Field */}
          <div className="parameter-field rename-field">
            <label className="param-label">
              <Edit2 size={14} />
              Component Name
            </label>
            <div className="param-description">
              Give this component a custom name. Leave empty to use template name.
            </div>
            <input
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder={`${functionMetadata.displayName} (template)`}
              className="param-input"
            />
            {!customName && (
              <div className="param-hint">
                Currently showing as: <strong>{functionMetadata.displayName}</strong> <em>(template)</em>
              </div>
            )}
          </div>

          <div className="section-divider">Parameters</div>

          {functionMetadata.parameters.length === 0 ? (
            <div className="no-parameters">This function has no parameters</div>
          ) : (
            functionMetadata.parameters.map((param) => (
              <div key={param.name} className="parameter-field">
                <label className="param-label">
                  {param.name}
                  {param.required && <span className="required">*</span>}
                </label>
                <div className="param-description">{param.description}</div>
                {renderParameterInput(param)}
                {param.default !== undefined && (
                  <div className="param-default">Default: {param.default}</div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="editor-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSave}>
            <Save size={16} />
            Save Parameters
          </button>
        </div>
      </div>
    </div>
  );
};

export default ParameterEditor;

