import { useState } from 'react';
import { AlertTriangle, FileCode } from 'lucide-react';
import './LibraryConflictDialog.css';

/**
 * LibraryConflictDialog - Resolve conflicts when importing function libraries
 * 
 * Shows conflicts and allows user to choose:
 * - Overwrite: Replace existing function globally
 * - Variant: Create new variant with (filename) suffix
 * - Skip: Don't import this function
 */
function LibraryConflictDialog({ conflicts, libraryName, onResolve, onCancel }) {
  const [resolutions, setResolutions] = useState(() => {
    // Default all to 'variant' (safest option)
    const initial = {};
    conflicts.forEach(conflict => {
      initial[conflict.functionName] = 'variant';
    });
    return initial;
  });

  const handleResolutionChange = (functionName, resolution) => {
    setResolutions(prev => ({
      ...prev,
      [functionName]: resolution
    }));
  };

  const handleApply = () => {
    onResolve(resolutions);
  };

  return (
    <div className="dialog-overlay">
      <div className="library-conflict-dialog">
        <div className="dialog-header">
          <AlertTriangle size={20} className="warning-icon" />
          <h2>Function Conflicts Detected</h2>
        </div>

        <div className="dialog-body">
          <p className="conflict-message">
            The library <strong>{libraryName}</strong> contains {conflicts.length} function(s) 
            that already exist in the palette. Choose how to resolve each conflict:
          </p>

          <div className="conflicts-list">
            {conflicts.map(conflict => (
              <div key={conflict.functionName} className="conflict-item">
                <div className="conflict-header">
                  <FileCode size={16} />
                  <span className="function-name">{conflict.functionName}</span>
                </div>

                <div className="conflict-info">
                  <div className="existing-source">
                    Existing: <span className="source-label">{conflict.existingSource || 'Built-in'}</span>
                  </div>
                  <div className="new-source">
                    New: <span className="source-label">{libraryName}</span>
                  </div>
                </div>

                <div className="resolution-options">
                  <label className="resolution-option">
                    <input
                      type="radio"
                      name={`resolution-${conflict.functionName}`}
                      value="overwrite"
                      checked={resolutions[conflict.functionName] === 'overwrite'}
                      onChange={() => handleResolutionChange(conflict.functionName, 'overwrite')}
                    />
                    <div className="option-content">
                      <strong>Overwrite</strong>
                      <span className="option-desc">Replace existing function globally</span>
                    </div>
                  </label>

                  <label className="resolution-option">
                    <input
                      type="radio"
                      name={`resolution-${conflict.functionName}`}
                      value="variant"
                      checked={resolutions[conflict.functionName] === 'variant'}
                      onChange={() => handleResolutionChange(conflict.functionName, 'variant')}
                    />
                    <div className="option-content">
                      <strong>Create Variant</strong>
                      <span className="option-desc">
                        Add as "{conflict.functionName} ({libraryName})"
                      </span>
                    </div>
                  </label>

                  <label className="resolution-option">
                    <input
                      type="radio"
                      name={`resolution-${conflict.functionName}`}
                      value="skip"
                      checked={resolutions[conflict.functionName] === 'skip'}
                      onChange={() => handleResolutionChange(conflict.functionName, 'skip')}
                    />
                    <div className="option-content">
                      <strong>Skip</strong>
                      <span className="option-desc">Don't import this function</span>
                    </div>
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="dialog-footer">
          <button className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleApply}>
            Apply Resolutions
          </button>
        </div>
      </div>
    </div>
  );
}

export default LibraryConflictDialog;

