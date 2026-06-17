import { useState, useEffect } from 'react';
import { Plus, X } from 'lucide-react';
import {
  FUNCTION_ROLE_OPTIONS,
  ROLE_TO_COMPATIBILITY_CATEGORY,
  defaultContractForKind,
} from '../store/subworkflowKinds';
import './NewFunctionDialog.css';

const PARAM_TYPES = ['INT', 'FLOAT', 'BOOL', 'STRING', 'DICT'];

const DEFAULT_ROLE = 'agent_behavior';

// Capability tokens a typed function can declare it reads from the kernel.
// These become `requires=[...]` and the typed env fails loudly if the active
// kernel doesn't provide them.
const CAPABILITIES = [
  { token: 'population', label: 'Cells / population', hint: 'loop env.cells, mark phenotypes' },
  { token: 'simulator', label: 'Substance levels', hint: "env.concentration('oxygen', cell)" },
  { token: 'gene_networks', label: 'Gene networks', hint: "cell.gene('X').is_on()" },
];

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

const isValidIdent = (s) => /^[a-zA-Z][a-zA-Z0-9_]*$/.test((s || '').trim());

/**
 * Dialog for defining a new function. Does NOT scaffold a file immediately —
 * the caller stages the function in metadata.gui.user_functions and the file
 * is written later when the user clicks "Export Behavior".
 *
 * The function's home is a plugin (an opencellcomms_adapters/<name> package) and
 * its file path is *derived* from plugin + role + name, so a scientist never
 * types a raw path.
 *
 * Props:
 *   behaviorName   : current canvas (used to default the role)
 *   onCreate(def)  : invoked with { name, file_path, parameters, category,
 *                    requires, typed_env_exempt }
 *   onCancel
 */
const NewFunctionDialog = ({ behaviorName = '', currentKind = '', currentContract = null, onCreate, onCancel }) => {
  const [name, setName] = useState('');
  const [parameters, setParameters] = useState([]);
  // The function's "role" is the v2 canvas kind (Agent / Environment /
  // Processing). Default to the current canvas's kind when it's a valid
  // authoring role, so a function lands where the biologist is working.
  const [role, setRole] = useState(() =>
    FUNCTION_ROLE_OPTIONS.some((o) => o.kind === currentKind) ? currentKind : DEFAULT_ROLE
  );
  const [requires, setRequires] = useState([]);
  // Setup functions (create population / load cells) keep the raw context dict.
  const [typedEnvExempt, setTypedEnvExempt] = useState(false);
  // Capabilities / setup are developer concerns — hidden by default so the
  // biologist sees only Name / Role / Plugin / Parameters.
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Plugin selection. The function lives in a plugin; the file path is derived.
  const [plugins, setPlugins] = useState([]);
  const [loadingPlugins, setLoadingPlugins] = useState(true);
  const [selectedPlugin, setSelectedPlugin] = useState('');
  const [creatingNewPlugin, setCreatingNewPlugin] = useState(false);
  const [newPluginName, setNewPluginName] = useState('');

  const [submitting, setSubmitting] = useState(false);

  // Load installed plugins. `common` is shared infrastructure, not a target for
  // experiment-specific functions, so it's excluded from the picker.
  useEffect(() => {
    let active = true;
    fetch('http://localhost:5001/api/plugins')
      .then((r) => r.json())
      .then((d) => {
        if (!active || !d.success) return;
        const list = (d.plugins || []).filter((p) => p.name !== 'common');
        setPlugins(list);
        if (list.length) setSelectedPlugin(list[0].name);
      })
      .catch(() => {})
      .finally(() => { if (active) setLoadingPlugins(false); });
    return () => { active = false; };
  }, []);

  const pluginName = (creatingNewPlugin ? newPluginName : selectedPlugin).trim();
  const derivedPath = (pluginName && name.trim() && role)
    ? `opencellcomms_adapters/${pluginName}/functions/${role}/${name.trim()}.py`
    : '';

  const toggleRequire = (token) =>
    setRequires((r) => (r.includes(token) ? r.filter((t) => t !== token) : [...r, token]));

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

  // Explain exactly why submit is blocked (empty = ok to submit).
  const validationError = (() => {
    if (!name.trim()) return 'Enter a function name.';
    if (!isValidIdent(name)) return 'Function name must start with a letter and use only letters, numbers, or underscores.';
    if (!pluginName) return creatingNewPlugin ? 'Enter a name for the new plugin.' : 'Choose a plugin or create a new one.';
    if (!isValidIdent(pluginName)) return 'Plugin name must start with a letter and use only letters, numbers, or underscores.';
    const badParam = parameters.findIndex((p) => !isValidIdent(p.name));
    if (badParam !== -1) {
      return parameters[badParam].name.trim()
        ? `Parameter ${badParam + 1} ("${parameters[badParam].name}") has an invalid name — use letters, numbers, or underscores.`
        : `Parameter ${badParam + 1} needs a name.`;
    }
    return '';
  })();

  const canSubmit = !validationError;

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
        file_path: derivedPath,
        parameters: coerced,
        // Compatibility category is legacy registry metadata. Execution order
        // comes from the workflow graph, not this tag.
        category: ROLE_TO_COMPATIBILITY_CATEGORY[role] || 'UTILITY',
        kind: role,
        contract: role === currentKind && currentContract
          ? { ...currentContract }
          : defaultContractForKind(role),
        // Exempt (setup) functions use the raw context dict, so capability
        // tokens don't apply.
        requires: typedEnvExempt ? [] : requires,
        typed_env_exempt: typedEnvExempt,
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
          <label>Role (what it belongs to)</label>
          <select
            className="dialog-input"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            {FUNCTION_ROLE_OPTIONS.map((o) => <option key={o.kind} value={o.kind}>{o.label}</option>)}
          </select>
        </div>

        <div className="nf-row">
          <label>Plugin (where this function lives)</label>
          {creatingNewPlugin ? (
            <div className="nf-path-row">
              <input
                className="dialog-input nf-path-input"
                placeholder="new_plugin_name"
                value={newPluginName}
                onChange={(e) => setNewPluginName(e.target.value)}
                autoFocus
              />
              <button
                className="nf-browse-btn"
                onClick={() => { setCreatingNewPlugin(false); setNewPluginName(''); }}
                title="Pick an existing plugin instead"
              >
                Existing
              </button>
            </div>
          ) : (
            <select
              className="dialog-input"
              value={selectedPlugin}
              onChange={(e) => {
                if (e.target.value === '__new__') {
                  setCreatingNewPlugin(true);
                } else {
                  setSelectedPlugin(e.target.value);
                }
              }}
            >
              {loadingPlugins && <option value="">Loading plugins…</option>}
              {!loadingPlugins && plugins.length === 0 && <option value="">(no plugins yet — create one)</option>}
              {plugins.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}{p.manifest?.version ? ` (v${p.manifest.version})` : ''}
                </option>
              ))}
              <option value="__new__">➕ New plugin…</option>
            </select>
          )}
          <div className="nf-path-hint">
            File: <code>{derivedPath || '…fill in name, role, and plugin'}</code>
            <br />
            Nothing is written until you click <em>Export Behavior</em> on the canvas.
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

        <button
          type="button"
          className="nf-advanced-toggle"
          onClick={() => setShowAdvanced((s) => !s)}
        >
          {showAdvanced ? '▾' : '▸'} Advanced
        </button>

        {showAdvanced && (
          <div className="nf-caps">
            <label className="nf-exempt">
              <input
                type="checkbox"
                checked={typedEnvExempt}
                onChange={(e) => setTypedEnvExempt(e.target.checked)}
              />
              This function <strong>creates or loads the cells</strong> (a setup step that runs once at the start)
            </label>

            {!typedEnvExempt && (
              <div className="nf-caps-list">
                <div className="nf-caps-title">What does this function need to look at?</div>
                <div className="nf-caps-subtitle">
                  Tick what it uses. The simulation gives it access to these and warns you early if a chosen
                  kernel can't provide one.
                </div>
                {CAPABILITIES.map((c) => (
                  <label className="nf-cap-row" key={c.token} title={c.hint}>
                    <input
                      type="checkbox"
                      checked={requires.includes(c.token)}
                      onChange={() => toggleRequire(c.token)}
                    />
                    <span className="nf-cap-label">{c.label}</span>
                    <code className="nf-cap-hint">{c.hint}</code>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}

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
