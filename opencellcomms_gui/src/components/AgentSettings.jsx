import { useState, useEffect } from 'react';
import { X, Save, KeyRound, CheckCircle, AlertCircle } from 'lucide-react';
import './AgentSettings.css';

const API_BASE_URL = 'http://localhost:5001';

const MODEL_OPTIONS = [
  { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (fast, cheaper)' },
  { value: 'claude-opus-4-8', label: 'Claude Opus 4.8 (most capable)' },
];

/**
 * AI Coding Agent settings modal.
 * Lets the user store their Claude API token (server-side in a gitignored .env)
 * and pick the model used for in-node code generation. The raw key is never
 * returned to the browser — only a masked preview and a "configured" flag.
 */
const AgentSettings = ({ onClose }) => {
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('claude-sonnet-4-6');
  const [config, setConfig] = useState({ configured: false, key_masked: '' });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null); // { type: 'success'|'error', message }

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/agent/config`);
      const data = await res.json();
      if (data.success) {
        setConfig({ configured: data.configured, key_masked: data.key_masked });
        if (data.model) setModel(data.model);
      }
    } catch (err) {
      setStatus({ type: 'error', message: 'Could not reach the backend server.' });
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      const body = { model };
      if (apiKey.trim()) body.api_key = apiKey.trim();
      const res = await fetch(`${API_BASE_URL}/api/agent/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.success) {
        setConfig({ configured: data.configured, key_masked: data.key_masked });
        setApiKey('');
        setStatus({ type: 'success', message: 'Settings saved.' });
      } else {
        setStatus({ type: 'error', message: data.error || 'Failed to save settings.' });
      }
    } catch (err) {
      setStatus({ type: 'error', message: err.message || 'Failed to save settings.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="agent-settings-overlay" onClick={onClose}>
      <div className="agent-settings" onClick={(e) => e.stopPropagation()}>
        <div className="agent-settings-header">
          <h3><KeyRound size={18} /> AI Coding Agent</h3>
          <button className="close-btn" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="agent-settings-body">
          <p className="agent-settings-desc">
            Paste your Claude API key to generate function code from a prompt at any node.
            The key is stored on your machine in the server's <code>.env</code> file
            (gitignored) and never leaves your computer except to call the Claude API.
          </p>

          <div className="agent-settings-status-line">
            {config.configured ? (
              <span className="configured"><CheckCircle size={14} /> Key configured ({config.key_masked})</span>
            ) : (
              <span className="not-configured"><AlertCircle size={14} /> No key configured yet</span>
            )}
          </div>

          <label className="agent-settings-label">Claude API key</label>
          <input
            type="password"
            className="agent-settings-input"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={config.configured ? 'Enter a new key to replace the current one' : 'sk-ant-...'}
            autoComplete="off"
          />

          <label className="agent-settings-label">Model</label>
          <select
            className="agent-settings-input"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          {status && (
            <div className={`agent-settings-message ${status.type}`}>
              {status.type === 'success' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
              {status.message}
            </div>
          )}
        </div>

        <div className="agent-settings-footer">
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            <Save size={16} />
            {saving ? 'Saving…' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AgentSettings;
