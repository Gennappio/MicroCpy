import { useState, useEffect } from 'react';
import { 
  Database, Search, Plus, Edit2, Trash2, Eye, EyeOff, 
  AlertTriangle, ChevronDown, ChevronRight, Save, RefreshCw,
  Tag, Lock, Unlock, X
} from 'lucide-react';
import useProjectStore from '../store/projectStore';
import './ContextRegistryPanel.css';

/**
 * Context Registry Panel - View and manage context keys
 * Per CONTEXT_MANAGEMENT.md specification
 */
const ContextRegistryPanel = ({ onClose }) => {
  const {
    contextRegistry,
    isProjectLoaded,
    registrySearchQuery,
    registryFilter,
    setRegistrySearchQuery,
    setRegistryFilter,
    getContextKeys,
    createContextKey,
    updateContextKey,
    deleteContextKey,
    deprecateContextKey,
    saveContextRegistry,
    reloadContextRegistry,
    lastError,
    clearError
  } = useProjectStore();

  const [expandedKeys, setExpandedKeys] = useState({});
  const [editingKey, setEditingKey] = useState(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);

  // Get filtered keys
  const keys = getContextKeys(registryFilter);

  // Group keys by namespace (first part before dot)
  const groupedKeys = keys.reduce((acc, key) => {
    const parts = key.name.split('.');
    const namespace = parts.length > 1 ? parts[0] : '_root';
    if (!acc[namespace]) acc[namespace] = [];
    acc[namespace].push(key);
    return acc;
  }, {});

  const handleSave = async () => {
    setIsSaving(true);
    setSaveMessage(null);
    const result = await saveContextRegistry();
    setIsSaving(false);
    
    if (result.success) {
      setSaveMessage({ type: 'success', text: 'Registry saved successfully' });
    } else if (result.revision_conflict) {
      setSaveMessage({ 
        type: 'error', 
        text: 'Conflict: Registry was modified externally. Please reload.' 
      });
    } else {
      setSaveMessage({ type: 'error', text: result.error || 'Failed to save' });
    }
    
    setTimeout(() => setSaveMessage(null), 3000);
  };

  const handleReload = async () => {
    const result = await reloadContextRegistry();
    if (result.success) {
      setSaveMessage({ type: 'success', text: 'Registry reloaded' });
      setTimeout(() => setSaveMessage(null), 2000);
    }
  };

  const toggleKeyExpanded = (keyId) => {
    setExpandedKeys(prev => ({ ...prev, [keyId]: !prev[keyId] }));
  };

  const handleDeleteKey = (key) => {
    if (key.delete_policy === 'forbidden') {
      alert('This key cannot be deleted (engine-provided)');
      return;
    }
    if (confirm(`Delete key "${key.name}"? This cannot be undone.`)) {
      deleteContextKey(key.id);
    }
  };

  const handleDeprecateKey = (key) => {
    const replacement = prompt('Enter replacement key name (optional):');
    deprecateContextKey(key.id, replacement || null);
  };

  const getVisibilityIcon = (visibility) => {
    switch (visibility) {
      case 'hidden': return <EyeOff size={14} className="visibility-icon hidden" />;
      case 'advanced': return <Eye size={14} className="visibility-icon advanced" />;
      default: return null;
    }
  };

  const getWritePolicyIcon = (policy) => {
    if (policy === 'read_only') {
      return <Lock size={14} className="policy-icon read-only" title="Read-only" />;
    }
    return null;
  };

  if (!isProjectLoaded) {
    return (
      <div className="context-registry-panel">
        <div className="panel-header">
          <h3><Database size={18} /> Context Registry</h3>
          <button className="close-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="no-project-message">
          <AlertTriangle size={24} />
          <p>No project loaded. Open a project to view the context registry.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="context-registry-panel">
      <div className="panel-header">
        <h3><Database size={18} /> Context Registry</h3>
        <div className="header-actions">
          <button 
            className="action-btn save" 
            onClick={handleSave}
            disabled={isSaving}
            title="Save registry"
          >
            <Save size={16} />
          </button>
          <button 
            className="action-btn reload" 
            onClick={handleReload}
            title="Reload from disk"
          >
            <RefreshCw size={16} />
          </button>
          <button className="close-btn" onClick={onClose}><X size={18} /></button>
        </div>
      </div>

      {saveMessage && (
        <div className={`save-message ${saveMessage.type}`}>
          {saveMessage.text}
        </div>
      )}

      {lastError && (
        <div className="error-banner">
          <AlertTriangle size={14} />
          <span>{lastError}</span>
          <button onClick={clearError}><X size={14} /></button>
        </div>
      )}

      <div className="search-filter-bar">
        <div className="search-input">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search keys..."
            value={registrySearchQuery}
            onChange={(e) => setRegistrySearchQuery(e.target.value)}
          />
        </div>
        <select
          className="filter-select"
          value={registryFilter}
          onChange={(e) => setRegistryFilter(e.target.value)}
        >
          <option value="all">All Keys</option>
          <option value="normal">Normal</option>
          <option value="advanced">Advanced</option>
          <option value="hidden">Hidden</option>
          <option value="deprecated">Deprecated</option>
        </select>
      </div>

      <div className="toolbar">
        <button
          className="add-key-btn"
          onClick={() => setShowCreateDialog(true)}
        >
          <Plus size={16} /> Add Key
        </button>
        <span className="key-count">{keys.length} keys</span>
      </div>

      <div className="keys-list">
        {Object.entries(groupedKeys).sort().map(([namespace, nsKeys]) => (
          <div key={namespace} className="namespace-group">
            <div
              className="namespace-header"
              onClick={() => toggleKeyExpanded(`ns_${namespace}`)}
            >
              {expandedKeys[`ns_${namespace}`] !== false ?
                <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <span className="namespace-name">
                {namespace === '_root' ? '(root)' : namespace}
              </span>
              <span className="namespace-count">{nsKeys.length}</span>
            </div>

            {expandedKeys[`ns_${namespace}`] !== false && (
              <div className="namespace-keys">
                {nsKeys.map(key => (
                  <div
                    key={key.id}
                    className={`key-item ${key.deprecated ? 'deprecated' : ''} ${key.owner === 'engine' ? 'engine' : ''}`}
                  >
                    <div
                      className="key-header"
                      onClick={() => toggleKeyExpanded(key.id)}
                    >
                      {expandedKeys[key.id] ?
                        <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      <span className="key-name">{key.name}</span>
                      {getVisibilityIcon(key.visibility)}
                      {getWritePolicyIcon(key.write_policy)}
                      {key.deprecated && (
                        <span className="deprecated-badge">deprecated</span>
                      )}
                      {key.owner === 'engine' && (
                        <span className="engine-badge">engine</span>
                      )}
                    </div>

                    {expandedKeys[key.id] && (
                      <div className="key-details">
                        {key.description && (
                          <p className="key-description">{key.description}</p>
                        )}
                        <div className="key-meta">
                          <span className="meta-item">
                            <strong>Type:</strong> {key.type?.name || key.type?.kind || 'any'}
                          </span>
                          <span className="meta-item">
                            <strong>Write:</strong> {key.write_policy}
                          </span>
                          {key.aliases?.length > 0 && (
                            <span className="meta-item">
                              <strong>Aliases:</strong> {key.aliases.join(', ')}
                            </span>
                          )}
                          {key.tags?.length > 0 && (
                            <div className="key-tags">
                              {key.tags.map(tag => (
                                <span key={tag} className="tag"><Tag size={10} /> {tag}</span>
                              ))}
                            </div>
                          )}
                        </div>

                        {key.owner !== 'engine' && (
                          <div className="key-actions">
                            <button
                              className="action-btn edit"
                              onClick={() => setEditingKey(key)}
                              title="Edit key"
                            >
                              <Edit2 size={14} />
                            </button>
                            {!key.deprecated && (
                              <button
                                className="action-btn deprecate"
                                onClick={() => handleDeprecateKey(key)}
                                title="Deprecate key"
                              >
                                <AlertTriangle size={14} />
                              </button>
                            )}
                            {key.delete_policy !== 'forbidden' && (
                              <button
                                className="action-btn delete"
                                onClick={() => handleDeleteKey(key)}
                                title="Delete key"
                              >
                                <Trash2 size={14} />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {keys.length === 0 && (
          <div className="no-keys-message">
            <Database size={24} />
            <p>No context keys found</p>
          </div>
        )}
      </div>

      {showCreateDialog && (
        <CreateContextKeyDialog
          onClose={() => setShowCreateDialog(false)}
          onCreate={(keyData) => {
            const result = createContextKey(keyData);
            if (result.success) {
              setShowCreateDialog(false);
            } else {
              alert(result.error);
            }
          }}
        />
      )}

      {editingKey && (
        <EditContextKeyDialog
          keyData={editingKey}
          onClose={() => setEditingKey(null)}
          onSave={(updates) => {
            const result = updateContextKey(editingKey.id, updates);
            if (result.success) {
              setEditingKey(null);
            } else {
              alert(result.error);
            }
          }}
        />
      )}
    </div>
  );
};

/**
 * Dialog for creating a new context key
 */
const CreateContextKeyDialog = ({ onClose, onCreate }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [typeName, setTypeName] = useState('any');
  const [writePolicy, setWritePolicy] = useState('read_write');
  const [visibility, setVisibility] = useState('normal');
  const [tags, setTags] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onCreate({
      name,
      description,
      type: { kind: 'primitive', name: typeName },
      write_policy: writePolicy,
      visibility,
      tags: tags.split(',').map(t => t.trim()).filter(Boolean)
    });
  };

  return (
    <div className="dialog-overlay">
      <div className="dialog create-key-dialog">
        <div className="dialog-header">
          <h3><Plus size={18} /> Create Context Key</h3>
          <button className="close-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Key Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., simulation.cell_count"
              pattern="^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$"
              required
            />
            <small>Lowercase letters, numbers, underscores. Use dots for namespacing.</small>
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this key represent?"
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
              <label>Visibility</label>
              <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
                <option value="normal">Normal</option>
                <option value="advanced">Advanced</option>
                <option value="hidden">Hidden</option>
              </select>
            </div>
            <div className="form-group">
              <label>Tags (comma-separated)</label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="e.g., simulation, metrics"
              />
            </div>
          </div>
          <div className="dialog-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary">Create Key</button>
          </div>
        </form>
      </div>
    </div>
  );
};

/**
 * Dialog for editing an existing context key
 */
const EditContextKeyDialog = ({ keyData, onClose, onSave }) => {
  const [description, setDescription] = useState(keyData.description || '');
  const [visibility, setVisibility] = useState(keyData.visibility || 'normal');
  const [tags, setTags] = useState((keyData.tags || []).join(', '));

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      description,
      visibility,
      tags: tags.split(',').map(t => t.trim()).filter(Boolean)
    });
  };

  return (
    <div className="dialog-overlay">
      <div className="dialog edit-key-dialog">
        <div className="dialog-header">
          <h3><Edit2 size={18} /> Edit: {keyData.name}</h3>
          <button className="close-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Visibility</label>
              <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
                <option value="normal">Normal</option>
                <option value="advanced">Advanced</option>
                <option value="hidden">Hidden</option>
              </select>
            </div>
            <div className="form-group">
              <label>Tags</label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
              />
            </div>
          </div>
          <div className="dialog-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary">Save Changes</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ContextRegistryPanel;

