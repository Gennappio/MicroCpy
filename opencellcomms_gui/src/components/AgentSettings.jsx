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
  // Anthropic
  'anthropic/claude-opus-4.8',
  'anthropic/claude-sonnet-4.6',
  'anthropic/claude-sonnet-4.5',
  'anthropic/claude-haiku-4.5',
  'anthropic/claude-3.5-haiku',
  // OpenAI
  'openai/gpt-5.2',
  'openai/gpt-5.1',
  'openai/gpt-4.1',
  'openai/gpt-4o',
  'openai/gpt-4o-mini',
  'openai/o3-mini',
  // Google
  'google/gemini-3.1-pro-preview',
  'google/gemini-2.5-pro',
  'google/gemini-2.5-flash',
  // Meta
  'meta-llama/llama-3.3-70b-instruct',
  'meta-llama/llama-3.1-70b-instruct',
  // DeepSeek
  'deepseek/deepseek-chat',
  'deepseek/deepseek-r1',
  // Mistral / Qwen / xAI
  'mistralai/mistral-large',
  'qwen/qwen3-coder',
  'x-ai/grok-4.3',
];
const DEFAULT_MODEL = { anthropic: 'claude-sonnet-4-6', openrouter: 'anthropic/claude-sonnet-4.6' };

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
  const [customModel, setCustomModel] = useState(false); // OpenRouter: type a model id not in the list
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
        if (data.model) {
          setModel(data.model);
          // If a saved OpenRouter model isn't in our suggestion list, show the custom field.
          if (data.provider === 'openrouter' && !OPENROUTER_SUGGESTIONS.includes(data.model)) {
            setCustomModel(true);
          }
        }
      }
    } catch (err) {
      setStatus({ type: 'error', message: 'Could not reach the backend server.' });
    }
  };

  const handleProviderChange = (newProvider) => {
    setProvider(newProvider);
    setModel(DEFAULT_MODEL[newProvider] || '');
    setCustomModel(false);
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
              <select
                className="agent-settings-input"
                value={customModel ? '__custom__' : model}
                onChange={(e) => {
                  if (e.target.value === '__custom__') {
                    setCustomModel(true);
                    setModel('');
                  } else {
                    setCustomModel(false);
                    setModel(e.target.value);
                  }
                }}
              >
                {OPENROUTER_SUGGESTIONS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
                <option value="__custom__">Custom model…</option>
              </select>
              {customModel && (
                <input
                  type="text"
                  className="agent-settings-input"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="e.g. cohere/command-r-plus"
                  autoFocus
                />
              )}
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
