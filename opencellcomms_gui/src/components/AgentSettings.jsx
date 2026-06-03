import { useState, useEffect } from 'react';
import { X, Save, KeyRound, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react';
import './AgentSettings.css';

const API_BASE_URL = 'http://localhost:5001';

const PROVIDERS = [
  { value: 'anthropic', label: 'Anthropic (direct)' },
  { value: 'openrouter', label: 'OpenRouter (many LLMs)' },
];

// Suggested models per provider. Anthropic is a fixed list; OpenRouter is an
// open text field with a few common suggestions (any openrouter.ai model id works).
const ANTHROPIC_MODELS = [
  { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (fast, cheaper)' },
  { value: 'claude-opus-4-8', label: 'Claude Opus 4.8 (most capable)' },
];
const OPENROUTER_SUGGESTIONS = [
  'anthropic/claude-3.5-sonnet',
  'openai/gpt-4o',
  'openai/gpt-4o-mini',
  'google/gemini-2.0-flash-001',
  'meta-llama/llama-3.3-70b-instruct',
  'deepseek/deepseek-chat',
];
const DEFAULT_MODEL = { anthropic: 'claude-sonnet-4-6', openrouter: 'anthropic/claude-3.5-sonnet' };

/**
 * AI Coding Agent settings modal.
 * Stores the user's API key(s) server-side in a gitignored .env (never returned
 * to the browser) and lets them pick a provider + model for in-node code
 * generation. Keys are kept per-provider so switching providers does not require
 * re-entering credentials.
 */
const AgentSettings = ({ onClose }) => {
  const [provider, setProvider] = useState('anthropic');
  const [model, setModel] = useState(DEFAULT_MODEL.anthropic);
  const [apiKey, setApiKey] = useState('');
  const [config, setConfig] = useState({
    anthropic_configured: false,
    openrouter_configured: false,
  });
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
        setConfig({
          anthropic_configured: data.anthropic_configured,
          openrouter_configured: data.openrouter_configured,
        });
        if (data.provider) setProvider(data.provider);
        if (data.model) setModel(data.model);
      }
    } catch (err) {
      setStatus({ type: 'error', message: 'Could not reach the backend server.' });
    }
  };

  const handleProviderChange = (newProvider) => {
    setProvider(newProvider);
    setModel(DEFAULT_MODEL[newProvider] || '');
    setApiKey(''); // key field is per-provider; clear the input on switch
    setStatus(null);
  };

  const isCurrentConfigured =
    provider === 'anthropic' ? config.anthropic_configured : config.openrouter_configured;

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      const body = { provider, model };
      if (apiKey.trim()) {
        if (provider === 'anthropic') body.anthropic_key = apiKey.trim();
        else body.openrouter_key = apiKey.trim();
      }
      const res = await fetch(`${API_BASE_URL}/api/agent/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.success) {
        setConfig({
          anthropic_configured: data.anthropic_configured,
          openrouter_configured: data.openrouter_configured,
        });
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

  const keyLabel = provider === 'anthropic' ? 'Anthropic API key' : 'OpenRouter API key';
  const keyPlaceholder =
    (provider === 'anthropic' ? 'sk-ant-...' : 'sk-or-...') +
    (isCurrentConfigured ? '  (enter a new key to replace the current one)' : '');

  return (
    <div className="agent-settings-overlay" onClick={onClose}>
      <div className="agent-settings" onClick={(e) => e.stopPropagation()}>
        <div className="agent-settings-header">
          <h3><KeyRound size={18} /> AI Coding Agent</h3>
          <button className="close-btn" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="agent-settings-body">
          <p className="agent-settings-desc">
            Generate function code from a prompt at any node. Choose a provider and model.
            Keys are stored on your machine in the server's <code>.env</code> file (gitignored)
            and never leave your computer except to call the chosen provider.
          </p>

          <label className="agent-settings-label">Provider</label>
          <select
            className="agent-settings-input"
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value)}
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>

          <div className="agent-settings-status-line">
            {isCurrentConfigured ? (
              <span className="configured"><CheckCircle size={14} /> Key configured for this provider</span>
            ) : (
              <span className="not-configured"><AlertCircle size={14} /> No key configured for this provider</span>
            )}
          </div>

          <label className="agent-settings-label">{keyLabel}</label>
          <input
            type="password"
            className="agent-settings-input"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={keyPlaceholder}
            autoComplete="off"
          />

          <label className="agent-settings-label">Model</label>
          {provider === 'anthropic' ? (
            <select
              className="agent-settings-input"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              {ANTHROPIC_MODELS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          ) : (
            <>
              <input
                type="text"
                className="agent-settings-input"
                list="openrouter-models"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="e.g. anthropic/claude-3.5-sonnet"
              />
              <datalist id="openrouter-models">
                {OPENROUTER_SUGGESTIONS.map((m) => <option key={m} value={m} />)}
              </datalist>
              <a
                className="agent-settings-link"
                href="https://openrouter.ai/models"
                target="_blank"
                rel="noreferrer"
              >
                Browse all OpenRouter models <ExternalLink size={12} />
              </a>
            </>
          )}

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
