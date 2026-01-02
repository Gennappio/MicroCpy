import { useState, useEffect } from 'react';
import { Save, RotateCcw, Edit2, Eye, AlertCircle, CheckCircle } from 'lucide-react';
import './CodeViewer.css';

const API_BASE_URL = 'http://localhost:5001';

/**
 * Code Viewer Component - View and edit function source code
 * Uses a simple textarea instead of Monaco Editor to avoid CSP issues
 */
const CodeViewer = ({ functionName, sourceFile }) => {
  const [code, setCode] = useState('');
  const [originalCode, setOriginalCode] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load function source code
  useEffect(() => {
    const loadCode = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({ name: functionName });
        if (sourceFile) {
          params.append('file', sourceFile);
        }

        const response = await fetch(`${API_BASE_URL}/api/function/source?${params}`);
        const data = await response.json();

        if (data.success) {
          setCode(data.source);
          setOriginalCode(data.source);
        } else {
          setError(data.error || 'Failed to load function source');
        }
      } catch (err) {
        setError(`Failed to connect to backend: ${err.message}`);
      } finally {
        setIsLoading(false);
      }
    };

    if (functionName) {
      loadCode();
    }
  }, [functionName, sourceFile]);

  // Validate code (debounced)
  useEffect(() => {
    if (!isEditing || code === originalCode) {
      setValidationError(null);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/function/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code }),
        });
        const data = await response.json();

        if (!data.valid) {
          setValidationError(data.error);
        } else {
          setValidationError(null);
        }
      } catch (err) {
        console.error('Validation error:', err);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [code, isEditing, originalCode]);

  const handleSave = async () => {
    if (validationError) {
      return;
    }

    setIsSaving(true);
    setSaveSuccess(false);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/function/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: functionName,
          file: sourceFile,
          source: code,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setOriginalCode(code);
        setIsEditing(false);
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      } else {
        setError(data.error || 'Failed to save function');
      }
    } catch (err) {
      setError(`Failed to save: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRevert = () => {
    setCode(originalCode);
    setValidationError(null);
    setIsEditing(false);
  };

  const handleEdit = () => {
    setIsEditing(true);
    setSaveSuccess(false);
  };

  if (isLoading) {
    return (
      <div className="code-viewer">
        <div className="loading">Loading source code...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="code-viewer">
        <div className="error-banner">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  const hasChanges = code !== originalCode;

  return (
    <div className="code-viewer">
      {/* Toolbar */}
      <div className="code-toolbar">
        <div className="toolbar-left">
          <span className="file-path">{sourceFile}</span>
        </div>
        <div className="toolbar-right">
          {!isEditing ? (
            <button className="btn btn-secondary" onClick={handleEdit}>
              <Edit2 size={14} />
              Edit Code
            </button>
          ) : (
            <>
              <button
                className="btn btn-secondary"
                onClick={handleRevert}
                disabled={!hasChanges}
              >
                <RotateCcw size={14} />
                Revert
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={isSaving || !!validationError || !hasChanges}
              >
                <Save size={14} />
                {isSaving ? 'Saving...' : 'Save'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Success Banner */}
      {saveSuccess && (
        <div className="success-banner">
          <CheckCircle size={16} />
          <span>Code saved successfully!</span>
        </div>
      )}

      {/* Validation Error Banner */}
      {validationError && (
        <div className="error-banner">
          <AlertCircle size={16} />
          <span>Syntax Error: {validationError}</span>
        </div>
      )}

      {/* Warning Banner */}
      {isEditing && !validationError && hasChanges && (
        <div className="warning-banner">
          <AlertCircle size={16} />
          <span>You have unsaved changes</span>
        </div>
      )}

      {/* Code Editor (Simple Textarea) */}
      <div className="code-editor-container">
        <textarea
          className="code-editor"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          readOnly={!isEditing}
          spellCheck={false}
          style={{
            fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, monospace',
            fontSize: '13px',
            lineHeight: '1.6',
            tabSize: 4,
          }}
        />
      </div>

      {/* Read-only hint */}
      {!isEditing && (
        <div className="readonly-hint">
          <Eye size={14} />
          <span>Read-only mode. Click "Edit Code" to make changes.</span>
        </div>
      )}
    </div>
  );
};

export default CodeViewer;

