import { useState, useEffect } from 'react';
import { Plus, X, FolderOpen } from 'lucide-react';
import './NewFunctionDialog.css';

const PARAM_TYPES = ['INT', 'FLOAT', 'BOOL', 'STRING', 'DICT'];

const defaultForType = (t) => {
  switch (t) {
    case 'INT': return 0;
    case 'FLOAT': return 0.0;
    case 'BOOL': return false;
    case 'STRING': return '';
    case 'DICT': return {};
    default: return null;
  }
};

/**
 * Dialog for defining a new function. Does NOT scaffold a file immediately —
 * the caller stages the function in metadata.gui.user_functions and the file
 * is written later when the user clicks "Export Behavior".
 *
 * Props:
 *   behaviorName        : current canvas (used as default basename for the .py file)
 *   defaultPath         : suggested file path (relative or absolute)
 *   onCreate(def)       : invoked with { name, file_path, parameters }
 *   onCancel
 */
const NewFunctionDialog = ({ behaviorName = '', defaultPath = '', onCreate, onCancel }) => {
  const [name, setName] = useState('');
  const [filePath, setFilePath] = useState(defaultPath);
  const [parameters, setParameters] = useState([]);
  const [browsing, setBrowsing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [browseError, setBrowseError] = useState(null);

  // When the user types a function name, auto-suggest the file basename
  useEffect(() => {
    if (!filePath && name) {
      setFilePath(name + '.py');
    }
    // Only auto-fill once on first name entry; user can change after
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  const addParam = () => setParameters([...parameters, { name: '', type: 'FLOAT', default: 0.0 }]);
  const removeParam = (i) => setParameters(parameters.filter((_, idx) => idx !== i));
  const updateParam = (i, field, value) => {
    const next = [...parameters];
    next[i] = { ...next[i], [field]: value };
    if (field === 'type') {
      next[i].default = defaultForType(value);
    }
    setParameters(next);
  };

  const isValidIdent = (s) => /^[a-zA-Z][a-zA-Z0-9_]*$/.test((s || '').trim());

  // Explain exactly why submit is blocked (empty = ok to submit).
  const validationError = (() => {
    if (!name.trim()) return 'Enter a function name.';
    if (!isValidIdent(name)) return 'Function name must start with a letter and use only letters, numbers, or underscores.';
    if (!filePath.trim().endsWith('.py')) return 'File path must end with .py';
    const badParam = parameters.findIndex((p) => !isValidIdent(p.name));
    if (badParam !== -1) {
      return parameters[badParam].name.trim()
        ? `Parameter ${badParam + 1} ("${parameters[badParam].name}") has an invalid name — use letters, numbers, or underscores.`
        : `Parameter ${badParam + 1} needs a name.`;
    }
    return '';
  })();

  const canSubmit = !validationError;

  const handleBrowse = async () => {
    setBrowsing(true);
    setBrowseError(null);
    try {
      const res = await fetch('http://localhost:5001/api/filesystem/save-dialog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ default_path: filePath || (name && `${name}.py`) || `${behaviorName || 'new_behavior'}.py` }),
      });
      const data = await res.json();
      if (data.cancelled) {
        // user cancelled; do nothing
      } else if (data.path) {
        // Prefer the repo-relative path; the system imports functions from
        // inside the repo, so an absolute path elsewhere won't work.
        const chosen = data.relative_path || data.path;
        setFilePath(chosen);
        if (!/^opencellcomms_adapters\/|^opencellcomms_engine\/src\//.test(chosen)) {
          setBrowseError(
            'That location is outside opencellcomms_adapters/ or opencellcomms_engine/src/, ' +
            'so the function can’t be imported. Choose a folder inside one of those.'
          );
        }
      } else if (data.error) {
        setBrowseError(data.error);
      }
    } catch (err) {
      setBrowseError('Browse failed: ' + err.message + ' — type the path manually');
    } finally {
      setBrowsing(false);
    }
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      const coerced = parameters.map((p) => {
        let def = p.default;
        if (p.type === 'INT') def = parseInt(def, 10) || 0;
        else if (p.type === 'FLOAT') def = parseFloat(def) || 0;
        else if (p.type === 'BOOL') def = def === true || def === 'true';
        else if (p.type === 'DICT') def = typeof def === 'object' ? def : {};
        return { name: p.name.trim(), type: p.type, default: def };
      });
      onCreate({
        name: name.trim(),
        file_path: filePath.trim(),
        parameters: coerced,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="dialog new-func-dialog" onClick={(e) => e.stopPropagation()}>
        <h3>Create New Function {behaviorName && <span className="dialog-sub">(for behavior: {behaviorName})</span>}</h3>

        <div className="nf-row">
          <label>Name</label>
          <input
            className="dialog-input"
            placeholder="e.g. evaluate_de_inputs"
            value={name}
            autoFocus
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="nf-row">
          <label>File path (where the Python file will be written)</label>
          <div className="nf-path-row">
            <input
              className="dialog-input nf-path-input"
              placeholder="e.g. opencellcomms_adapters/MyAdapter/functions/intracellular/my_behavior.py"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
            />
            <button className="nf-browse-btn" onClick={handleBrowse} disabled={browsing} title="Open a save dialog">
              <FolderOpen size={14} />
              {browsing ? '...' : 'Browse'}
            </button>
          </div>
          {browseError && <div className="nf-browse-error">{browseError}</div>}
          <div className="nf-path-hint">
            Must end with <code>.py</code> and be inside <code>opencellcomms_adapters/</code> or <code>opencellcomms_engine/src/</code>.
            The file isn't written until you click <em>Export Behavior</em> on the canvas.
          </div>
        </div>

        <div className="nf-params">
          <div className="nf-params-header">
            <span>Parameters</span>
            <button className="nf-add-param" onClick={addParam}><Plus size={12} /> Add Parameter</button>
          </div>
          {parameters.length === 0 && <div className="nf-params-empty">No parameters yet — click "Add Parameter" to define one.</div>}
          {parameters.map((p, i) => (
            <div className="nf-param-row" key={i}>
              <input
                className="dialog-input nf-param-name"
                placeholder="param_name"
                value={p.name}
                onChange={(e) => updateParam(i, 'name', e.target.value)}
              />
              <select
                className="dialog-input nf-param-type"
                value={p.type}
                onChange={(e) => updateParam(i, 'type', e.target.value)}
              >
                {PARAM_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              {p.type === 'BOOL' ? (
                <select
                  className="dialog-input nf-param-default"
                  value={String(p.default)}
                  onChange={(e) => updateParam(i, 'default', e.target.value === 'true')}
                >
                  <option value="false">false</option>
                  <option value="true">true</option>
                </select>
              ) : p.type === 'DICT' ? (
                <input className="dialog-input nf-param-default" value="{}" disabled title="Dict defaults are empty {}" />
              ) : (
                <input
                  className="dialog-input nf-param-default"
                  placeholder="default"
                  value={p.default}
                  onChange={(e) => updateParam(i, 'default', e.target.value)}
                />
              )}
              <button className="nf-del-param" onClick={() => removeParam(i)} title="Remove parameter">
                <X size={14} />
              </button>
            </div>
          ))}
        </div>

        {validationError && <div className="nf-validation-error">{validationError}</div>}

        <div className="dialog-actions">
          <button className="btn btn-secondary" onClick={onCancel} disabled={submitting}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={!canSubmit || submitting}>
            {submitting ? 'Adding…' : 'Add to Project'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default NewFunctionDialog;
