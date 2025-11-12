import { useState, useEffect } from 'react';
import { X, Save, Edit2, Plus, Trash2 } from 'lucide-react';
import { getFunction } from '../data/functionRegistry';
import './ParameterEditor.css';

/**
 * Parameter Editor Modal - Edit function parameters
 */
const ParameterEditor = ({ node, onSave, onClose }) => {
  const functionMetadata = getFunction(node.data.functionName);
  const [parameters, setParameters] = useState(node.data.parameters || {});
  const [customName, setCustomName] = useState(node.data.customName || '');
  const [functionName, setFunctionName] = useState(node.data.functionName || '');
  const [functionFile, setFunctionFile] = useState(node.data.functionFile || '');
  const [description, setDescription] = useState(node.data.description || '');

  useEffect(() => {
    setParameters(node.data.parameters || {});
    setCustomName(node.data.customName || '');
    setFunctionName(node.data.functionName || '');
    setFunctionFile(node.data.functionFile || '');
    setDescription(node.data.description || '');
  }, [node]);

  const handleChange = (paramName, value) => {
    setParameters((prev) => ({
      ...prev,
      [paramName]: value,
    }));
  };

  const handleAddParameter = () => {
    const newParamName = `param_${Object.keys(parameters).length + 1}`;
    setParameters((prev) => ({
      ...prev,
      [newParamName]: '',
    }));
  };

  const handleRemoveParameter = (paramName) => {
    setParameters((prev) => {
      const newParams = { ...prev };
      delete newParams[paramName];
      return newParams;
    });
  };

  const handleRenameParameter = (oldName, newName) => {
    if (oldName === newName) return;
    if (newName in parameters) {
      alert('Parameter name already exists');
      return;
    }
    setParameters((prev) => {
      const newParams = { ...prev };
      newParams[newName] = newParams[oldName];
      delete newParams[oldName];
      return newParams;
    });
  };

  const handleSave = () => {
    if (isCustomFunction) {
      // For custom functions, also save function name, file, and description
      onSave(parameters, customName, {
        functionName,
        functionFile,
        description,
      });
    } else {
      onSave(parameters, customName);
    }
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

  // Handle custom functions (no metadata in registry)
  const isCustomFunction = node.data.isCustom || !functionMetadata;

  if (!functionMetadata && !isCustomFunction) {
    return null;
  }

  const displayName = isCustomFunction
    ? node.data.functionName
    : functionMetadata.displayName;

  const parametersList = isCustomFunction
    ? Object.keys(parameters)
        .filter(key => key !== 'function_file')
        .map(key => ({
          name: key,
          type: typeof parameters[key] === 'number'
            ? (Number.isInteger(parameters[key]) ? 'integer' : 'float')
            : typeof parameters[key] === 'boolean' ? 'boolean' : 'string',
          default: parameters[key],
        }))
    : functionMetadata.parameters;

  return (
    <div className="parameter-editor-overlay" onClick={onClose}>
      <div className="parameter-editor" onClick={(e) => e.stopPropagation()}>
        <div className="editor-header">
          <h3>{displayName}</h3>
          {isCustomFunction && <span className="custom-badge">Custom Function</span>}
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {!isCustomFunction && (
          <div className="editor-description">{functionMetadata.description}</div>
        )}

        <div className="editor-content">
          {/* Custom Function Configuration */}
          {isCustomFunction && (
            <>
              <div className="parameter-field">
                <label className="param-label">
                  <Edit2 size={14} />
                  Function Name
                </label>
                <div className="param-description">
                  The name of the Python function to call
                </div>
                <input
                  type="text"
                  value={functionName}
                  onChange={(e) => setFunctionName(e.target.value)}
                  placeholder="my_custom_function"
                  className="param-input"
                />
              </div>

              <div className="parameter-field">
                <label className="param-label">
                  Function File
                </label>
                <div className="param-description">
                  Path to the Python file containing this function
                </div>
                <input
                  type="text"
                  value={functionFile}
                  onChange={(e) => setFunctionFile(e.target.value)}
                  placeholder="path/to/my_functions.py"
                  className="param-input"
                />
              </div>

              <div className="parameter-field">
                <label className="param-label">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What does this function do?"
                  className="param-input"
                  rows={2}
                />
              </div>
            </>
          )}

          {/* Custom Name Field for Standard Functions */}
          {!isCustomFunction && (
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
          )}

          <div className="section-divider">
            Parameters
            {isCustomFunction && (
              <button className="btn-add-param" onClick={handleAddParameter}>
                <Plus size={14} />
                Add Parameter
              </button>
            )}
          </div>

          {parametersList.length === 0 ? (
            <div className="no-parameters">
              {isCustomFunction
                ? 'No parameters defined. Click "Add Parameter" to add one.'
                : 'This function has no parameters'}
            </div>
          ) : (
            parametersList.map((param) => (
              <div key={param.name} className="parameter-field">
                <div className="param-header">
                  {isCustomFunction ? (
                    <input
                      type="text"
                      value={param.name}
                      onChange={(e) => handleRenameParameter(param.name, e.target.value)}
                      className="param-name-input"
                      placeholder="parameter_name"
                    />
                  ) : (
                    <label className="param-label">
                      {param.name}
                      {param.required && <span className="required">*</span>}
                    </label>
                  )}
                  {isCustomFunction && (
                    <button
                      className="btn-remove-param"
                      onClick={() => handleRemoveParameter(param.name)}
                      title="Remove parameter"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
                {param.description && !isCustomFunction && (
                  <div className="param-description">{param.description}</div>
                )}
                {renderParameterInput(param)}
                {param.default !== undefined && !isCustomFunction && (
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

