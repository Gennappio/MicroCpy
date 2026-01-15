import { useState } from 'react';
import { Plus, X, AlertCircle } from 'lucide-react';
import useProjectStore, { validateKeyName } from '../store/projectStore';
import './CreateContextKeyDialog.css';

/**
 * Dialog for creating a new context key
 * Can be triggered from ContextKeyPicker or ContextRegistryPanel
 * 
 * Props:
 *   - onClose: Callback when dialog is closed
 *   - onCreated: Callback when key is successfully created (receives new key)
 *   - initialName: Optional initial name (e.g., from search query)
 */
const CreateContextKeyDialog = ({ onClose, onCreated, initialName = '' }) => {
  const { createContextKey } = useProjectStore();
  
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState('');
  const [typeName, setTypeName] = useState('any');
  const [writePolicy, setWritePolicy] = useState('read_write');
  const [deletePolicy, setDeletePolicy] = useState('allowed');
  const [visibility, setVisibility] = useState('normal');
  const [tags, setTags] = useState('');
  const [aliases, setAliases] = useState('');
  const [example, setExample] = useState('');
  const [error, setError] = useState(null);

  // Validate name as user types
  const isNameValid = name === '' || validateKeyName(name);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(null);

    // Validate name
    if (!name) {
      setError('Key name is required');
      return;
    }

    if (!validateKeyName(name)) {
      setError('Invalid key name format. Use lowercase letters, numbers, underscores. Dots for namespacing.');
      return;
    }

    // Build key data
    const keyData = {
      name,
      description,
      type: { kind: 'primitive', name: typeName },
      write_policy: writePolicy,
      delete_policy: deletePolicy,
      visibility,
      tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      aliases: aliases.split(',').map(a => a.trim()).filter(Boolean),
      example: example || undefined
    };

    // Create the key
    const result = createContextKey(keyData);

    if (result.success) {
      if (onCreated) {
        onCreated(result.key);
      }
      onClose();
    } else {
      setError(result.error);
    }
  };

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog create-context-key-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h3><Plus size={18} /> Create Context Key</h3>
          <button className="close-btn" onClick={onClose}><X size={18} /></button>
        </div>

        {error && (
          <div className="error-message">
            <AlertCircle size={14} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Key Name <span className="required">*</span></label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value.toLowerCase())}
              placeholder="e.g., simulation.cell_count"
              className={!isNameValid ? 'invalid' : ''}
              autoFocus
            />
            {!isNameValid && (
              <small className="error">
                Must start with lowercase letter, use only a-z, 0-9, underscore. Dots for namespacing.
              </small>
            )}
            <small>Use dots to create namespaces (e.g., "metabolism.glucose_level")</small>
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this key represent? How should it be used?"
              rows={3}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Type</label>
              <select value={typeName} onChange={(e) => setTypeName(e.target.value)}>
                <option value="any">Any</option>
                <option value="string">String</option>
                <option value="int">Integer</option>
                <option value="float">Float</option>
                <option value="bool">Boolean</option>
                <option value="list">List</option>
                <option value="dict">Dictionary</option>
                <option value="ndarray">NumPy Array</option>
                <option value="dataframe">DataFrame</option>
              </select>
            </div>
            <div className="form-group">
              <label>Write Policy</label>
              <select value={writePolicy} onChange={(e) => setWritePolicy(e.target.value)}>
                <option value="read_write">Read/Write</option>
                <option value="read_only">Read Only</option>
                <option value="write_once">Write Once</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Delete Policy</label>
              <select value={deletePolicy} onChange={(e) => setDeletePolicy(e.target.value)}>
                <option value="allowed">Allowed</option>
                <option value="forbidden">Forbidden</option>
              </select>
            </div>
            <div className="form-group">
              <label>Visibility</label>
              <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
                <option value="normal">Normal</option>
                <option value="advanced">Advanced</option>
                <option value="hidden">Hidden</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Aliases (comma-separated)</label>
            <input
              type="text"
              value={aliases}
              onChange={(e) => setAliases(e.target.value)}
              placeholder="e.g., cell_count, num_cells"
            />
            <small>Alternative names that can be used to reference this key</small>
          </div>

          <div className="form-group">
            <label>Tags (comma-separated)</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g., simulation, metrics, output"
            />
          </div>

          <div className="form-group">
            <label>Example Value</label>
            <input
              type="text"
              value={example}
              onChange={(e) => setExample(e.target.value)}
              placeholder="e.g., 1000"
            />
            <small>An example value to help users understand the expected format</small>
          </div>

          <div className="dialog-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={!isNameValid || !name}>
              Create Key
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateContextKeyDialog;

