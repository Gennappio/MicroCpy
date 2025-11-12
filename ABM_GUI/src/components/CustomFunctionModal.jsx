import React, { useState } from 'react';
import { X, Code } from 'lucide-react';
import './CustomFunctionModal.css';

/**
 * Modal for creating custom workflow function template
 * Creates a draggable template - users customize parameters after dropping on canvas
 */
const CustomFunctionModal = ({ onSave, onClose }) => {
  const [functionName, setFunctionName] = useState('');
  const [description, setDescription] = useState('');
  const [functionFile, setFunctionFile] = useState('');

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

    const customFunction = {
      functionName: functionName.trim(),
      displayName: functionName.trim(),
      description: description.trim() || 'Custom function',
      functionFile: functionFile.trim(),
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
            <h2>Create Custom Function Template</h2>
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
              autoFocus
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

          <div className="info-box">
            <strong>💡 How it works:</strong>
            <p>This creates a draggable custom function template in the palette.</p>
            <p>Drag it to the canvas and customize parameters there.</p>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave}>
            Create Template
          </button>
        </div>
      </div>
    </div>
  );
};

export default CustomFunctionModal;

