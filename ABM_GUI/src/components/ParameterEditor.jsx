import { useState, useEffect, useRef } from 'react';
import { X, Save, Edit2, Plus, Trash2, Eye, Copy, Upload, Check } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { getFunction } from '../data/functionRegistry';
import './ParameterEditor.css';
const API_BASE_URL = 'http://localhost:5001';


/**
 * Parameter Editor Modal - Edit function parameters or parameter node data
 */
const ParameterEditor = ({ node, onSave, onClose }) => {
  const isParameterNode = node.type === 'parameterNode';
  const functionMetadata = !isParameterNode ? getFunction(node.data.functionName) : null;
  const [parameters, setParameters] = useState(node.data.parameters || {});
  const [customName, setCustomName] = useState(node.data.customName || node.data.label || '');
  const [functionName, setFunctionName] = useState(node.data.functionName || '');
  const [functionFile, setFunctionFile] = useState(node.data.functionFile || '');
  const [description, setDescription] = useState(node.data.description || '');
  const [stepCount, setStepCount] = useState(node.data.stepCount || 1);

  const [showCode, setShowCode] = useState(false);
  const [codeLoading, setCodeLoading] = useState(false);
  const [codeError, setCodeError] = useState('');
  const [code, setCode] = useState('');
  const [sourcePath, setSourcePath] = useState('');
  const [isEditingCode, setIsEditingCode] = useState(false);
  const [editedCode, setEditedCode] = useState('');
  const [isSavingCode, setIsSavingCode] = useState(false);
  const codeTextareaRef = useRef(null);

  const loadCode = async () => {
    setCodeLoading(true);
    setCodeError('');
    try {
      const params = new URLSearchParams({ name: functionName });
      const sourceHint = (functionMetadata && functionMetadata.source_file) || functionFile || parameters?.function_file || '';
      if (sourceHint) params.append('file', sourceHint);
      const res = await fetch(`${API_BASE_URL}/api/function/source?${params.toString()}`);
      const data = await res.json();
      if (data && data.success) {
        setCode(data.source || '');
        setSourcePath(typeof data.file_path === 'string' ? data.file_path : sourceHint);
      } else {
        setCode('');
        setCodeError(data?.error || 'Failed to load source code');
      }
    } catch (err) {
      setCode('');
      setCodeError(err.message || 'Failed to load source code');
    } finally {
      setCodeLoading(false);
    }
  };

  const handleToggleCode = async () => {
    if (!showCode) {
      await loadCode();
    }
    setShowCode((v) => !v);
  };

  const handleCopyCode = () => {
    if (code) {
      navigator.clipboard.writeText(code).then(() => {
        alert('Code copied to clipboard!');
      }).catch(err => {
        console.error('Failed to copy code:', err);
        alert('Failed to copy code to clipboard');
      });
    }
  };

  const handleUploadCode = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.py')) {
      alert('Please upload a Python (.py) file');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('function_name', functionName);
      if (resolvedSourcePath) {
        formData.append('target_path', resolvedSourcePath);
      }

      const res = await fetch(`${API_BASE_URL}/api/function/upload`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();

      if (data.success) {
        alert(`Successfully uploaded ${file.name}!\n${data.message}`);
        // Update source path with the new file path
        if (data.file_path) {
          setSourcePath(data.file_path);
        }
        // Reload the code to show the uploaded version
        await loadCode();
      } else {
        alert(`Upload failed: ${data.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Upload error:', err);
      alert(`Upload failed: ${err.message}`);
    }

    // Reset file input
    event.target.value = '';
  };

  const handleEditCode = () => {
    setIsEditingCode(true);
    setEditedCode(code);
  };

  const handleCancelEdit = () => {
    setIsEditingCode(false);
    setEditedCode('');
  };

  const handleSaveCode = async () => {
    if (!resolvedSourcePath) {
      alert('Cannot save: No source file path available');
      return;
    }

    setIsSavingCode(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/function/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: resolvedSourcePath,
          source: editedCode,
          function_name: functionName
        })
      });

      const data = await res.json();

      if (data.success) {
        alert('Code saved successfully!');
        setCode(editedCode);
        setIsEditingCode(false);
      } else {
        alert(`Save failed: ${data.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Save error:', err);
      alert(`Save failed: ${err.message}`);
    } finally {
      setIsSavingCode(false);
    }
  };

  useEffect(() => {
    setParameters(node.data.parameters || {});
    setCustomName(node.data.customName || '');
    setFunctionName(node.data.functionName || '');
    setFunctionFile(node.data.functionFile || '');
    setDescription(node.data.description || '');
    setStepCount(node.data.stepCount || 1);
  }, [node]);

  useEffect(() => {
    // Reset code viewer when switching nodes
    setShowCode(false);
    setCode('');
    setCodeError('');
    setCodeLoading(false);
  }, [node]);


  // Ensure the code viewer scrolls to top whenever code is loaded/shown
  useEffect(() => {
    if (showCode && codeTextareaRef?.current) {
      try {
        codeTextareaRef.current.scrollTop = 0;
      } catch (_) {}
    }
  }, [showCode, code]);

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
    if (isParameterNode) {
      // For parameter nodes, save label and parameters
      onSave(parameters, customName);
    } else if (isCustomFunction) {
      // For custom functions, also save function name, file, description, and step_count
      onSave(parameters, customName, {
        functionName,
        functionFile,
        description,
        stepCount,
      });
    } else {
      // For standard functions, save parameters, custom name, and step_count
      onSave(parameters, customName, { stepCount });
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

  if (!functionMetadata && !isCustomFunction && !isParameterNode) {
    return null;
  }

  const displayName = isParameterNode
    ? (customName || 'Parameter Node')
    : (isCustomFunction
      ? node.data.functionName
      : functionMetadata.displayName);

  const resolvedSourcePath = sourcePath || ((functionMetadata && functionMetadata.source_file) || functionFile || parameters?.function_file || '');
  const displayCode = resolvedSourcePath ? `# File: ${resolvedSourcePath}\n\n${code}` : code;

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
          {isParameterNode && <span className="parameter-badge">Parameter Storage</span>}
          {isCustomFunction && <span className="custom-badge">Custom Function</span>}
          {!isParameterNode && (
            <button className="btn btn-secondary" onClick={handleToggleCode}>
              <Eye size={14} />
              {showCode ? 'Hide Code' : 'View Code'}
            </button>
          )}
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {isParameterNode && (
          <div className="editor-description">
            Store parameters that can be connected to function nodes
          </div>
        )}

        {!isCustomFunction && !isParameterNode && functionMetadata && (
          <div className="editor-description">{functionMetadata.description}</div>
        )}

        <div className="editor-content">
          {/* Parameter Node Editor - Simple key-value interface */}
          {isParameterNode && (
            <>
              <div className="parameter-field rename-field">
                <label className="param-label">
                  <Edit2 size={14} />
                  Parameter Node Name
                </label>
                <div className="param-description">
                  Give this parameter storage a descriptive name (e.g., "Oxygen Parameters", "Diffusion Settings")
                </div>
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="New Parameters"
                  className="param-input"
                />
              </div>

              <div className="section-divider">
                Parameters
                <button className="btn-add-param" onClick={handleAddParameter}>
                  <Plus size={14} />
                  Add Parameter
                </button>
              </div>

              {Object.keys(parameters).length === 0 ? (
                <div className="no-parameters">
                  No parameters defined. Click "Add Parameter" to add one.
                </div>
              ) : (
                Object.keys(parameters).map((paramName) => (
                  <div key={paramName} className="parameter-field">
                    <div className="param-header">
                      <input
                        type="text"
                        value={paramName}
                        onChange={(e) => handleRenameParameter(paramName, e.target.value)}
                        className="param-name-input"
                        placeholder="parameter_name"
                      />
                      <button
                        className="btn-remove-param"
                        onClick={() => handleRemoveParameter(paramName)}
                        title="Remove parameter"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <input
                      type="text"
                      value={parameters[paramName]}
                      onChange={(e) => handleChange(paramName, e.target.value)}
                      className="param-input"
                      placeholder="value"
                    />
                  </div>
                ))
              )}
            </>
          )}

          {/* Function Node Editor - Full interface with code viewer */}
          {!isParameterNode && showCode && (
            <div className="code-container">
              {codeLoading ? (
                <div className="loading">Loading source code...</div>
              ) : codeError ? (
                <div className="code-error">Error: {codeError}</div>
              ) : (
                <>
                  <div className="code-meta">
                    <div>
                      File: {resolvedSourcePath || '(from registry)'}
                      {code && (
                        <span> • Lines: {(isEditingCode ? editedCode : code).split('\n').length}</span>
                      )}
                    </div>
                    <div className="code-actions">
                      {isEditingCode ? (
                        <>
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={handleSaveCode}
                            disabled={isSavingCode}
                            title="Save changes"
                          >
                            <Check size={14} />
                            {isSavingCode ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={handleCancelEdit}
                            title="Cancel editing"
                          >
                            <X size={14} />
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={handleEditCode}
                            title="Edit code"
                          >
                            <Edit2 size={14} />
                            Edit
                          </button>
                          <button className="btn btn-secondary btn-sm" onClick={handleCopyCode} title="Copy to clipboard">
                            <Copy size={14} />
                            Copy
                          </button>
                          <label className="btn btn-secondary btn-sm" title="Upload custom function file">
                            <Upload size={14} />
                            Upload
                            <input
                              type="file"
                              accept=".py"
                              onChange={handleUploadCode}
                              style={{ display: 'none' }}
                            />
                          </label>
                        </>
                      )}
                    </div>
                  </div>
                  {isEditingCode ? (
                    <textarea
                      className="code-textarea code-textarea-editable"
                      value={editedCode}
                      onChange={(e) => setEditedCode(e.target.value)}
                      spellCheck={false}
                    />
                  ) : (
                    <SyntaxHighlighter
                      language="python"
                      style={vscDarkPlus}
                      showLineNumbers={true}
                      wrapLines={true}
                      customStyle={{
                        margin: 0,
                        borderRadius: '4px',
                        fontSize: '13px',
                        maxHeight: '500px',
                        overflow: 'auto'
                      }}
                    >
                      {displayCode}
                    </SyntaxHighlighter>
                  )}
                </>
              )}
            </div>
          )}

              {/* Custom Function Configuration */}
              {!isParameterNode && isCustomFunction && (
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
          {!isParameterNode && !isCustomFunction && (
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

          {/* Step Count Field for All Function Nodes */}
          {!isParameterNode && (
            <div className="parameter-field">
              <label className="param-label">
                Step Count
              </label>
              <div className="param-description">
                Number of times this function executes per macro-step (for macrostep stage)
              </div>
              <input
                type="number"
                value={stepCount}
                onChange={(e) => setStepCount(Math.max(1, parseInt(e.target.value, 10) || 1))}
                min={1}
                step={1}
                className="param-input"
              />
              <div className="param-hint">
                Default: 1. Increase for multi-scale simulations (e.g., fast processes run more often).
              </div>
            </div>
          )}

          {!isParameterNode && (
            <>
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
            </>
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

