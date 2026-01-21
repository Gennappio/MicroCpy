import { useState, useEffect, useRef } from 'react';
import { X, Save, Edit2, Plus, Trash2, Eye, Copy, Upload, Check, ExternalLink, ChevronUp, ChevronDown, List, Braces } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { getFunction } from '../data/functionRegistry';
import useWorkflowStore from '../store/workflowStore';
import './ParameterEditor.css';
const API_BASE_URL = 'http://localhost:5001';


/**
 * Parameter Editor Modal - Edit function parameters or parameter node data
 */
const ParameterEditor = ({ node, onSave, onClose }) => {
  const workflow = useWorkflowStore((state) => state.workflow);
  const currentStage = useWorkflowStore((state) => state.currentStage);
  const setCurrentStage = useWorkflowStore((state) => state.setCurrentStage);

  const isParameterNode = node.type === 'parameterNode';
  const isListParameterNode = node.type === 'listParameterNode';
  const isDictParameterNode = node.type === 'dictParameterNode';
  const isSubWorkflowCall = node.type === 'subworkflowCall';
  const isFunctionNode = !isParameterNode && !isListParameterNode && !isDictParameterNode && !isSubWorkflowCall;
  const functionMetadata = isFunctionNode ? getFunction(node.data.functionName) : null;

  const [parameters, setParameters] = useState(node.data.parameters || {});
  const [customName, setCustomName] = useState(node.data.customName || node.data.label || '');
  const [functionName, setFunctionName] = useState(node.data.functionName || '');
  const [functionFile, setFunctionFile] = useState(node.data.functionFile || '');
  const [description, setDescription] = useState(node.data.description || '');
  const [stepCount, setStepCount] = useState(node.data.stepCount || 1);

  // SubWorkflowCall specific state
  const [subworkflowName, setSubworkflowName] = useState(node.data.subworkflowName || '');
  const [iterations, setIterations] = useState(node.data.iterations || 1);
  const [results, setResults] = useState(node.data.results || '');

  // List parameter node state
  const [listItems, setListItems] = useState(node.data.items || []);
  const [listType, setListType] = useState(node.data.listType || 'string');

  // Dict parameter node state
  const [dictEntries, setDictEntries] = useState(node.data.entries || []);

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
    setCustomName(node.data.customName || node.data.label || '');
    setFunctionName(node.data.functionName || '');
    setFunctionFile(node.data.functionFile || '');
    setDescription(node.data.description || '');
    setStepCount(node.data.stepCount || 1);
    setSubworkflowName(node.data.subworkflowName || '');
    setIterations(node.data.iterations || 1);
    setResults(node.data.results || '');
    // List node state
    setListItems(node.data.items || []);
    setListType(node.data.listType || 'string');
    // Dict node state
    setDictEntries(node.data.entries || []);
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

  const handleGoToWorkflow = () => {
    if (isSubWorkflowCall && node.data.subworkflowName) {
      setCurrentStage(node.data.subworkflowName);
      onClose(); // Close the editor after navigation
    }
  };

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

  // === List item handlers ===
  const handleAddListItem = () => {
    const defaultValue = listType === 'float' ? 0 : '';
    setListItems((prev) => [...prev, defaultValue]);
  };

  const handleRemoveListItem = (index) => {
    setListItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateListItem = (index, value) => {
    setListItems((prev) => {
      const newItems = [...prev];
      // Convert to proper type
      if (listType === 'float') {
        newItems[index] = parseFloat(value) || 0;
      } else {
        newItems[index] = value;
      }
      return newItems;
    });
  };

  const handleMoveListItem = (index, direction) => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= listItems.length) return;
    setListItems((prev) => {
      const newItems = [...prev];
      [newItems[index], newItems[newIndex]] = [newItems[newIndex], newItems[index]];
      return newItems;
    });
  };

  const handleAddNestedList = (index) => {
    setListItems((prev) => {
      const newItems = [...prev];
      newItems[index] = [];
      return newItems;
    });
  };

  const handleAddNestedDict = (index) => {
    setListItems((prev) => {
      const newItems = [...prev];
      newItems[index] = {};
      return newItems;
    });
  };

  // === Dict entry handlers ===
  const handleAddDictEntry = () => {
    const newKey = `key_${dictEntries.length + 1}`;
    setDictEntries((prev) => [...prev, { key: newKey, value: '', valueType: 'string' }]);
  };

  const handleRemoveDictEntry = (index) => {
    setDictEntries((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateDictKey = (index, newKey) => {
    setDictEntries((prev) => {
      const newEntries = [...prev];
      newEntries[index] = { ...newEntries[index], key: newKey };
      return newEntries;
    });
  };

  const handleUpdateDictValue = (index, value) => {
    setDictEntries((prev) => {
      const newEntries = [...prev];
      const entry = newEntries[index];
      // Convert to proper type based on valueType
      let convertedValue = value;
      switch (entry.valueType) {
        case 'float':
          convertedValue = parseFloat(value) || 0;
          break;
        case 'int':
          convertedValue = parseInt(value, 10) || 0;
          break;
        case 'bool':
          convertedValue = value === 'true' || value === true;
          break;
        default:
          convertedValue = value;
      }
      newEntries[index] = { ...entry, value: convertedValue };
      return newEntries;
    });
  };

  const handleUpdateDictValueType = (index, newType) => {
    setDictEntries((prev) => {
      const newEntries = [...prev];
      const entry = newEntries[index];
      // Reset value when type changes
      let newValue;
      switch (newType) {
        case 'float':
          newValue = 0;
          break;
        case 'int':
          newValue = 0;
          break;
        case 'bool':
          newValue = false;
          break;
        case 'list':
          newValue = [];
          break;
        case 'dict':
          newValue = {};
          break;
        default:
          newValue = '';
      }
      newEntries[index] = { ...entry, valueType: newType, value: newValue };
      return newEntries;
    });
  };

  const handleSave = () => {
    if (isParameterNode) {
      // For parameter nodes, save label and parameters
      onSave(parameters, customName);
    } else if (isListParameterNode) {
      // For list nodes, save items and label
      onSave({ items: listItems, listType }, customName);
    } else if (isDictParameterNode) {
      // For dict nodes, save entries and label
      onSave({ entries: dictEntries }, customName);
    } else if (isSubWorkflowCall) {
      // For sub-workflow calls, save all properties
      onSave(parameters, customName, {
        subworkflowName,
        iterations,
        description,
        results
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

	  // Return null only if this is a *function* node and we couldn't find metadata.
	  // Parameter nodes (simple, list, dict) and sub-workflow calls do not rely on
	  // registry metadata, so they should still render the editor even when
	  // functionMetadata is null.
	  if (isFunctionNode && !functionMetadata) {
	    return null;
	  }

	  // Determine the display name for the editor header based on node type
	  let displayName;
	  if (isParameterNode) {
	    displayName = customName || 'Parameter Node';
	  } else if (isListParameterNode) {
	    displayName = customName || (listType === 'float' ? 'Float List' : 'String List');
	  } else if (isDictParameterNode) {
	    displayName = customName || 'Dictionary';
	  } else if (isSubWorkflowCall) {
	    displayName = 'Sub-workflow Call';
	  } else {
	    // Function node: by this point functionMetadata should exist, but be defensive
	    displayName = (functionMetadata && functionMetadata.displayName) ||
	                  node.data.customName ||
	                  node.data.label ||
	                  node.data.functionName ||
	                  'Function';
	  }

  const resolvedSourcePath = sourcePath || ((functionMetadata && functionMetadata.source_file) || functionFile || parameters?.function_file || '');
  const displayCode = resolvedSourcePath ? `# File: ${resolvedSourcePath}\n\n${code}` : code;

  const parametersList = functionMetadata ? functionMetadata.parameters : [];

  return (
    <div className="parameter-editor-overlay" onClick={onClose}>
      <div className="parameter-editor" onClick={(e) => e.stopPropagation()}>
        <div className="editor-header">
          <h3>{displayName}</h3>
          {isParameterNode && <span className="parameter-badge">Parameter Storage</span>}
	        {isFunctionNode && (
            <button className="btn btn-secondary" onClick={handleToggleCode}>
              <Eye size={14} />
              {showCode ? 'Hide Code' : 'View Code'}
            </button>
          )}
          {isSubWorkflowCall && (
            <button className="btn btn-secondary" onClick={handleGoToWorkflow}>
              <ExternalLink size={14} />
              Go to Workflow
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

        {!isParameterNode && functionMetadata && (
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

          {/* List Parameter Node Editor */}
          {isListParameterNode && (
            <>
              <div className="parameter-field">
                <label className="param-label">
                  <List size={14} />
                  List Name
                </label>
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder={listType === 'float' ? 'Float List' : 'String List'}
                  className="param-input"
                />
              </div>

              <div className="section-divider">
                Items ({listType === 'float' ? 'Float' : 'String'})
                <button className="btn-add-param" onClick={handleAddListItem}>
                  <Plus size={14} />
                  Add Item
                </button>
              </div>

              {listItems.length === 0 ? (
                <div className="no-parameters">
                  No items in list. Click "Add Item" to add one.
                </div>
              ) : (
                listItems.map((item, index) => (
                  <div key={index} className="list-item-field">
                    <div className="list-item-controls">
                      <span className="list-item-index">[{index}]</span>
                      <button
                        className="btn-move"
                        onClick={() => handleMoveListItem(index, 'up')}
                        disabled={index === 0}
                        title="Move up"
                      >
                        <ChevronUp size={14} />
                      </button>
                      <button
                        className="btn-move"
                        onClick={() => handleMoveListItem(index, 'down')}
                        disabled={index === listItems.length - 1}
                        title="Move down"
                      >
                        <ChevronDown size={14} />
                      </button>
                      <button
                        className="btn-remove-param"
                        onClick={() => handleRemoveListItem(index)}
                        title="Remove item"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                    {Array.isArray(item) ? (
                      <div className="nested-value">
                        <span className="nested-label">Nested List [{item.length} items]</span>
                      </div>
                    ) : typeof item === 'object' && item !== null ? (
                      <div className="nested-value">
                        <span className="nested-label">Nested Dict [{Object.keys(item).length} keys]</span>
                      </div>
                    ) : (
                      <input
                        type={listType === 'float' ? 'number' : 'text'}
                        value={item}
                        onChange={(e) => handleUpdateListItem(index, e.target.value)}
                        className="param-input list-item-input"
                        placeholder={listType === 'float' ? '0.0' : 'value'}
                        step={listType === 'float' ? 'any' : undefined}
                      />
                    )}
                  </div>
                ))
              )}
            </>
          )}

          {/* Dict Parameter Node Editor */}
          {isDictParameterNode && (
            <>
              <div className="parameter-field">
                <label className="param-label">
                  <Braces size={14} />
                  Dictionary Name
                </label>
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="Dictionary"
                  className="param-input"
                />
              </div>

              <div className="section-divider">
                Entries
                <button className="btn-add-param" onClick={handleAddDictEntry}>
                  <Plus size={14} />
                  Add Entry
                </button>
              </div>

              {dictEntries.length === 0 ? (
                <div className="no-parameters">
                  No entries in dictionary. Click "Add Entry" to add one.
                </div>
              ) : (
                dictEntries.map((entry, index) => (
                  <div key={index} className="dict-entry-field">
                    <div className="dict-entry-header">
                      <input
                        type="text"
                        value={entry.key}
                        onChange={(e) => handleUpdateDictKey(index, e.target.value)}
                        className="dict-key-input"
                        placeholder="key"
                      />
                      <select
                        value={entry.valueType}
                        onChange={(e) => handleUpdateDictValueType(index, e.target.value)}
                        className="dict-type-select"
                      >
                        <option value="string">String</option>
                        <option value="float">Float</option>
                        <option value="int">Int</option>
                        <option value="bool">Bool</option>
                        <option value="list">List</option>
                        <option value="dict">Dict</option>
                      </select>
                      <button
                        className="btn-remove-param"
                        onClick={() => handleRemoveDictEntry(index)}
                        title="Remove entry"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <div className="dict-value-row">
                      {entry.valueType === 'bool' ? (
                        <select
                          value={entry.value ? 'true' : 'false'}
                          onChange={(e) => handleUpdateDictValue(index, e.target.value)}
                          className="param-input"
                        >
                          <option value="true">true</option>
                          <option value="false">false</option>
                        </select>
                      ) : entry.valueType === 'list' ? (
                        <div className="nested-value">
                          <span className="nested-label">
                            List [{Array.isArray(entry.value) ? entry.value.length : 0} items]
                          </span>
                        </div>
                      ) : entry.valueType === 'dict' ? (
                        <div className="nested-value">
                          <span className="nested-label">
                            Dict [{typeof entry.value === 'object' && entry.value ? Object.keys(entry.value).length : 0} keys]
                          </span>
                        </div>
                      ) : (
                        <input
                          type={entry.valueType === 'float' || entry.valueType === 'int' ? 'number' : 'text'}
                          value={entry.value}
                          onChange={(e) => handleUpdateDictValue(index, e.target.value)}
                          className="param-input"
                          placeholder="value"
                          step={entry.valueType === 'float' ? 'any' : entry.valueType === 'int' ? '1' : undefined}
                        />
                      )}
                    </div>
                  </div>
                ))
              )}
            </>
          )}

          {/* Sub-workflow Call Editor */}
          {isSubWorkflowCall && (() => {
            // Get available subworkflows based on call rules
            const currentKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage] ||
                               (currentStage === 'main' ? 'composer' : 'subworkflow');

            const availableSubworkflows = Object.keys(workflow.subworkflows || {}).filter(name => {
              if (name === currentStage) return false;
              const targetKind = workflow.metadata?.gui?.subworkflow_kinds?.[name] ||
                                (name === 'main' ? 'composer' : 'subworkflow');
              // Sub-workflows can only call other sub-workflows (not composers)
              if (currentKind === 'subworkflow' && targetKind === 'composer') return false;
              return true;
            });

            return (
              <>
                <div className="parameter-field">
                  <label className="param-label">
                    <Edit2 size={14} />
                    Target Sub-workflow
                  </label>
                  <div className="param-description">
                    Select which {currentKind === 'subworkflow' ? 'sub-workflow' : 'composer or sub-workflow'} to call
                  </div>
                  <select
                    value={subworkflowName}
                    onChange={(e) => setSubworkflowName(e.target.value)}
                    className="param-input"
                  >
                    {availableSubworkflows.map((name) => {
                      const kind = workflow.metadata?.gui?.subworkflow_kinds?.[name] ||
                                  (name === 'main' ? 'composer' : 'subworkflow');
                      return (
                        <option key={name} value={name}>
                          {name} ({kind})
                        </option>
                      );
                    })}
                  </select>
                  {currentKind === 'subworkflow' && (
                    <div className="param-hint">
                      Note: Sub-workflows cannot call composers
                    </div>
                  )}
                </div>

                <div className="parameter-field">
                  <label className="param-label">
                    Iterations
                  </label>
                  <div className="param-description">
                    Number of times to execute this sub-workflow
                  </div>
                  <input
                    type="number"
                    value={iterations}
                    onChange={(e) => setIterations(parseInt(e.target.value, 10) || 1)}
                    min={1}
                    className="param-input"
                  />
                </div>

                <div className="parameter-field">
                  <label className="param-label">
                    Description
                  </label>
                  <div className="param-description">
                    Optional description for this call
                  </div>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Optional description"
                    className="param-input"
                  />
                </div>

                <div className="parameter-field">
                  <label className="param-label">
                    Results
                  </label>
                  <div className="param-description">
                    Variable name to store the return value from this sub-workflow (e.g., "result", "output_data")
                  </div>
                  <input
                    type="text"
                    value={results}
                    onChange={(e) => setResults(e.target.value)}
                    placeholder="result"
                    className="param-input"
                  />
                  <div className="param-hint">
                    This variable will contain the data returned by the sub-workflow
                  </div>
                </div>
              </>
            );
          })()}

	          {/* Function Node Editor - Full interface with code viewer */}
	          {isFunctionNode && showCode && (
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

          {/* Custom Name Field for Function Nodes */}
          {!isParameterNode && functionMetadata && (
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
	          {isFunctionNode && (
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

          {isFunctionNode && (
            <>
              <div className="section-divider">
                Parameters
              </div>

              {parametersList.length === 0 ? (
                <div className="no-parameters">
                  This function has no parameters
                </div>
              ) : (
                parametersList.map((param) => (
                  <div key={param.name} className="parameter-field">
                    <div className="param-header">
                      <label className="param-label">
                        {param.name}
                        {param.required && <span className="required">*</span>}
                      </label>
                    </div>
                    {param.description && (
                      <div className="param-description">{param.description}</div>
                    )}
                    {renderParameterInput(param)}
                    {param.default !== undefined && (
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

