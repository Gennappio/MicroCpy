import React, { useState } from 'react';
import { X, Plus, Trash2, Code } from 'lucide-react';
import './CustomFunctionModal.css';

/**
 * Modal for creating custom workflow functions
 * Allows users to define function name, description, and parameters
 */
const CustomFunctionModal = ({ onSave, onClose, currentStage }) => {
  const [functionName, setFunctionName] = useState('');
  const [description, setDescription] = useState('');
  const [functionFile, setFunctionFile] = useState('');
  const [parameters, setParameters] = useState([]);

  const addParameter = () => {
    setParameters([
      ...parameters,
      {
        id: Date.now(),
        name: '',
        type: 'float',
        value: '',
        description: '',
      },
    ]);
  };

  const removeParameter = (id) => {
    setParameters(parameters.filter((p) => p.id !== id));
  };

  const updateParameter = (id, field, value) => {
    setParameters(
      parameters.map((p) => (p.id === id ? { ...p, [field]: value } : p))
    );
  };

  const handleSave = () => {
    // Validate
    if (!functionName.trim()) {
      alert('Please enter a function name');
      return;
    }

    if (!functionFile.trim()) {
      alert('Please enter a function file path');
      return;
    }

    // Check for duplicate parameter names
    const paramNames = parameters.map((p) => p.name.trim()).filter((n) => n);
    const uniqueNames = new Set(paramNames);
    if (paramNames.length !== uniqueNames.size) {
      alert('Parameter names must be unique');
      return;
    }

    // Convert parameters to key-value object
    const paramObject = {
      function_file: functionFile.trim(),
    };

    parameters.forEach((p) => {
      if (p.name.trim()) {
        let value = p.value;
        
        // Type conversion
        if (p.type === 'integer') {
          value = parseInt(value, 10) || 0;
        } else if (p.type === 'float') {
          value = parseFloat(value) || 0.0;
        } else if (p.type === 'boolean') {
          value = value === 'true' || value === true;
        }
        
        paramObject[p.name.trim()] = value;
      }
    });

    const customFunction = {
      functionName: functionName.trim(),
      description: description.trim(),
      parameters: paramObject,
      isCustom: true,
    };

    onSave(customFunction);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content custom-function-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <Code size={20} />
            <h2>Create Custom Function</h2>
          </div>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* Function Name */}
          <div className="form-field">
            <label className="form-label">
              Function Name <span className="required">*</span>
            </label>
            <input
              type="text"
              value={functionName}
              onChange={(e) => setFunctionName(e.target.value)}
              placeholder="my_custom_function"
              className="form-input"
            />
            <div className="form-hint">
              The name of the Python function to call (e.g., calculate_custom_metric)
            </div>
          </div>

          {/* Description */}
          <div className="form-field">
            <label className="form-label">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this function do?"
              className="form-textarea"
              rows={2}
            />
          </div>

          {/* Function File */}
          <div className="form-field">
            <label className="form-label">
              Function File <span className="required">*</span>
            </label>
            <input
              type="text"
              value={functionFile}
              onChange={(e) => setFunctionFile(e.target.value)}
              placeholder="path/to/my_functions.py"
              className="form-input"
            />
            <div className="form-hint">
              Path to the Python file containing this function
            </div>
          </div>

          {/* Parameters */}
          <div className="form-field">
            <div className="form-label-row">
              <label className="form-label">Parameters</label>
              <button className="btn-add-param" onClick={addParameter}>
                <Plus size={14} />
                Add Parameter
              </button>
            </div>

            {parameters.length === 0 ? (
              <div className="no-parameters">
                No parameters defined. Click "Add Parameter" to add one.
              </div>
            ) : (
              <div className="parameters-list">
                {parameters.map((param) => (
                  <div key={param.id} className="parameter-row">
                    <div className="param-row-header">
                      <input
                        type="text"
                        value={param.name}
                        onChange={(e) => updateParameter(param.id, 'name', e.target.value)}
                        placeholder="parameter_name"
                        className="param-name-input"
                      />
                      <select
                        value={param.type}
                        onChange={(e) => updateParameter(param.id, 'type', e.target.value)}
                        className="param-type-select"
                      >
                        <option value="float">Float</option>
                        <option value="integer">Integer</option>
                        <option value="string">String</option>
                        <option value="boolean">Boolean</option>
                      </select>
                      <button
                        className="btn-remove-param"
                        onClick={() => removeParameter(param.id)}
                        title="Remove parameter"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <div className="param-row-body">
                      <input
                        type="text"
                        value={param.description}
                        onChange={(e) => updateParameter(param.id, 'description', e.target.value)}
                        placeholder="Parameter description (optional)"
                        className="param-desc-input"
                      />
                      {param.type === 'boolean' ? (
                        <select
                          value={param.value}
                          onChange={(e) => updateParameter(param.id, 'value', e.target.value)}
                          className="param-value-input"
                        >
                          <option value="">Select value...</option>
                          <option value="true">true</option>
                          <option value="false">false</option>
                        </select>
                      ) : (
                        <input
                          type={param.type === 'integer' || param.type === 'float' ? 'number' : 'text'}
                          step={param.type === 'float' ? 'any' : '1'}
                          value={param.value}
                          onChange={(e) => updateParameter(param.id, 'value', e.target.value)}
                          placeholder="Default value"
                          className="param-value-input"
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave}>
            Create Function
          </button>
        </div>
      </div>
    </div>
  );
};

export default CustomFunctionModal;

