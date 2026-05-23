"use client";
import React, { useEffect, useState } from 'react';
import { getLLMSettings, updateLLMSettings, LLMSettings } from '../../lib/api';

export default function SettingsPage() {
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [provider, setProvider] = useState<'none' | 'openai'>('none');
  const [model, setModel] = useState('gpt-3.5-turbo');
  const [apiKey, setApiKey] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getLLMSettings()
      .then((loaded) => {
        setSettings(loaded);
        setProvider(loaded.provider);
        setModel(loaded.model);
      })
      .catch(() => setError('Failed to load settings'));
  }, []);

  async function saveSettings(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setStatus(null);
    setError(null);
    try {
      const saved = await updateLLMSettings({
        provider,
        model,
        api_key: apiKey || undefined,
      });
      setSettings(saved);
      setProvider(saved.provider);
      setModel(saved.model);
      setApiKey('');
      setStatus('Settings saved.');
    } catch (err) {
      setError('Failed to save settings');
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="page-narrow">
      <section className="settings-panel">
        <div className="panel-heading">
          <h2>LLM Provider</h2>
          <p>Configure the provider used for generated answers.</p>
        </div>

        <form className="settings-form" onSubmit={saveSettings}>
          <label>
            <span>Provider</span>
            <select value={provider} onChange={(event) => setProvider(event.target.value as 'none' | 'openai')}>
              <option value="none">Local fallback</option>
              <option value="openai">OpenAI</option>
            </select>
          </label>

          <label>
            <span>Model</span>
            <input
              value={model}
              onChange={(event) => setModel(event.target.value)}
              disabled={provider === 'none'}
              placeholder="gpt-3.5-turbo"
            />
          </label>

          <label>
            <span>API key</span>
            <input
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              disabled={provider === 'none'}
              placeholder={settings?.has_api_key ? 'Existing key configured' : 'Paste API key'}
              type="password"
            />
          </label>

          <div className="settings-actions">
            <button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
            {settings?.has_api_key && provider === 'openai' && <span>API key configured</span>}
          </div>

          {status && <p className="form-success">{status}</p>}
          {error && <p className="form-error">{error}</p>}
        </form>
      </section>
    </main>
  );
}
