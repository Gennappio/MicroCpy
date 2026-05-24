import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import './NewFunctionDialog.css';

const PARAM_TYPES = ['INT', 'FLOAT', 'BOOL', 'STRING', 'DICT'];
const CATEGORIES = ['initialization', 'intracellular', 'diffusion', 'intercellular', 'finalization', 'output'];

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

const NewFunctionDialog = ({ defaultCategory = 'intracellular', defaultAdapter = 'jayatilake', behaviorName = '', onCreate, onCancel }) => {
  const [name, setName] = useState('');
  const [category, setCategory] = useState(defaultCategory);
  const [adapter, setAdapter] = useState(defaultAdapter);
  const [parameters, setParameters] = useState([]);
  const [submitting, setSubmitting] = useState(false);

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

  const canSubmit = name.trim() &&
    /^[a-zA-Z][a-zA-Z0-9_]*$/.test(name.trim()) &&
    parameters.every((p) => p.name.trim() && /^[a-zA-Z][a-zA-Z0-9_]*$/.test(p.name.trim()));

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      // Coerce defaults to right type for JSON
      const coerced = parameters.map((p) => {
        let def = p.default;
        if (p.type === 'INT') def = parseInt(def, 10) || 0;
        else if (p.type === 'FLOAT') def = parseFloat(def) || 0;
        else if (p.type === 'BOOL') def = def === true || def === 'true';
        else if (p.type === 'DICT') def = typeof def === 'object' ? def : {};
        return { name: p.name.trim(), type: p.type, default: def };
      });
      await onCreate({
        name: name.trim(),
        category,
        adapter: adapter.trim() || null,
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

        <div className="nf-row nf-two-col">
          <div>
            <label>Category</label>
            <select className="dialog-input" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label>Adapter (blank = engine generic)</label>
            <input className="dialog-input" placeholder="e.g. jayatilake" value={adapter} onChange={(e) => setAdapter(e.target.value)} />
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
                <input
                  className="dialog-input nf-param-default"
                  value="{}"
                  disabled
                  title="Dictionary defaults are empty {}"
                />
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

        <div className="dialog-actions">
          <button className="btn btn-secondary" onClick={onCancel} disabled={submitting}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={!canSubmit || submitting}>
            {submitting ? 'Creating…' : 'Create Function'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default NewFunctionDialog;
