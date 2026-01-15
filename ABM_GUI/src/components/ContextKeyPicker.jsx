import { useState, useRef, useEffect } from 'react';
import { Search, ChevronDown, Plus, X, Database, Lock, AlertTriangle } from 'lucide-react';
import useProjectStore from '../store/projectStore';
import './ContextKeyPicker.css';

/**
 * Context Key Picker - Dropdown for selecting context keys from registry
 * Per CONTEXT_MANAGEMENT.md: No free-text input, only registry keys
 * 
 * Props:
 *   - value: Current selected key ID (or null)
 *   - onChange: Callback when key is selected (receives key ID)
 *   - placeholder: Placeholder text
 *   - filter: Optional filter function (key) => boolean
 *   - allowCreate: Whether to show "Create new key" option
 *   - onCreateKey: Callback when user wants to create a new key
 *   - disabled: Whether the picker is disabled
 *   - showKeyDetails: Whether to show key type/description in dropdown
 */
const ContextKeyPicker = ({
  value,
  onChange,
  placeholder = 'Select a context key...',
  filter = null,
  allowCreate = true,
  onCreateKey = null,
  disabled = false,
  showKeyDetails = true
}) => {
  const { contextRegistry, isProjectLoaded, getContextKeyById } = useProjectStore();
  
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);

  // Get the selected key object
  const selectedKey = value ? getContextKeyById(value) : null;

  // Get all available keys (filtered)
  const getAvailableKeys = () => {
    if (!contextRegistry) return [];
    
    let keys = contextRegistry.keys || [];
    
    // Apply custom filter
    if (filter) {
      keys = keys.filter(filter);
    }
    
    // Filter out deprecated keys by default (unless explicitly searching for them)
    if (!searchQuery.toLowerCase().includes('deprecated')) {
      keys = keys.filter(k => !k.deprecated);
    }
    
    // Filter by visibility (hide 'hidden' keys unless searching)
    if (!searchQuery) {
      keys = keys.filter(k => k.visibility !== 'hidden');
    }
    
    // Apply search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      keys = keys.filter(k =>
        k.name.toLowerCase().includes(query) ||
        (k.description && k.description.toLowerCase().includes(query)) ||
        (k.aliases && k.aliases.some(a => a.toLowerCase().includes(query)))
      );
    }
    
    return keys;
  };

  const availableKeys = getAvailableKeys();

  // Group keys by namespace
  const groupedKeys = availableKeys.reduce((acc, key) => {
    const parts = key.name.split('.');
    const namespace = parts.length > 1 ? parts[0] : '_root';
    if (!acc[namespace]) acc[namespace] = [];
    acc[namespace].push(key);
    return acc;
  }, {});

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSelect = (key) => {
    onChange(key.id);
    setIsOpen(false);
    setSearchQuery('');
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange(null);
  };

  const handleCreateNew = () => {
    setIsOpen(false);
    if (onCreateKey) {
      onCreateKey(searchQuery);
    }
  };

  if (!isProjectLoaded) {
    return (
      <div className="context-key-picker disabled">
        <div className="picker-display">
          <AlertTriangle size={14} />
          <span className="no-project">No project loaded</span>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`context-key-picker ${disabled ? 'disabled' : ''} ${isOpen ? 'open' : ''}`}
      ref={dropdownRef}
    >
      <div 
        className="picker-display"
        onClick={() => !disabled && setIsOpen(!isOpen)}
      >
        {selectedKey ? (
          <>
            <Database size={14} className="key-icon" />
            <span className="selected-key-name">{selectedKey.name}</span>
            {selectedKey.write_policy === 'read_only' && (
              <Lock size={12} className="read-only-icon" title="Read-only" />
            )}
            <button className="clear-btn" onClick={handleClear}>
              <X size={14} />
            </button>
          </>
        ) : (
          <span className="placeholder">{placeholder}</span>
        )}
        <ChevronDown size={16} className="chevron" />
      </div>

      {isOpen && (
        <div className="picker-dropdown">
          <div className="search-box">
            <Search size={14} />
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search keys..."
              onClick={(e) => e.stopPropagation()}
            />
          </div>

          <div className="keys-list">
            {Object.entries(groupedKeys).sort().map(([namespace, nsKeys]) => (
              <div key={namespace} className="namespace-group">
                <div className="namespace-label">
                  {namespace === '_root' ? 'Root' : namespace}
                </div>
                {nsKeys.map(key => (
                  <div
                    key={key.id}
                    className={`key-option ${key.id === value ? 'selected' : ''} ${key.owner === 'engine' ? 'engine' : ''}`}
                    onClick={() => handleSelect(key)}
                  >
                    <span className="key-name">{key.name}</span>
                    {key.write_policy === 'read_only' && (
                      <Lock size={12} className="read-only-icon" />
                    )}
                    {showKeyDetails && key.type && (
                      <span className="key-type">{key.type.name || key.type.kind}</span>
                    )}
                  </div>
                ))}
              </div>
            ))}

            {availableKeys.length === 0 && (
              <div className="no-keys">
                {searchQuery ? `No keys matching "${searchQuery}"` : 'No keys available'}
              </div>
            )}

            {allowCreate && onCreateKey && (
              <div className="create-option" onClick={handleCreateNew}>
                <Plus size={14} />
                <span>Create new key{searchQuery ? `: "${searchQuery}"` : ''}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ContextKeyPicker;

