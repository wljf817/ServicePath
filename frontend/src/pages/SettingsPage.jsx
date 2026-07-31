import {useEffect, useState} from "react";

import {GlobeIcon, SettingsIcon} from "../components/Icons";
import Panel from "../components/ui/Panel";
import Spinner from "../components/ui/Spinner";


function StatusBadge({ready}) {
    return (
        <span className={ready ? "settings-status ready" : "settings-status"}>
            <i aria-hidden="true" />
            {ready ? "Configured" : "Not configured"}
        </span>
    );
}


export default function SettingsPage({
    appSettings,
    diagnosisRunning,
    error: loadError,
    onChange,
    onSave,
    saveError,
    saveStatus,
    status,
}) {
    const [draft, setDraft] = useState(appSettings);
    const saving = saveStatus === "saving";
    const locked = saving || diagnosisRunning;

    useEffect(() => {
        if (appSettings) {
            setDraft(appSettings);
        }
    }, [appSettings]);

    function update(field, value) {
        setDraft((current) => ({...current, [field]: value}));
        onChange();
    }

    async function submit(event) {
        event.preventDefault();
        if (!locked) {
            try {
                await onSave(draft);
            } catch {
                // App keeps the storage error visible.
            }
        }
    }

    if (status === "loading") {
        return <div className="page-loading" role="status"><Spinner size="lg" /><p>Loading settings...</p></div>;
    }
    if (status === "error" || !draft) {
        return (
            <Panel className="state-card"><Panel.Content>
                <h1>Settings unavailable</h1>
                <p role="alert">{loadError || "Browser settings could not be loaded."}</p>
            </Panel.Content></Panel>
        );
    }

    const providerReady = draft.provider_type === "preset"
        ? draft.presets.some((preset) => preset.id === draft.preset_id)
        : Boolean(draft.openai_api_key && draft.openai_model);
    const serverReady = Boolean(
        draft.server_presets.length
        || (draft.custom_server_url && draft.custom_server_token)
    );
    const providerValue = draft.provider_type === "preset"
        ? `preset:${draft.preset_id}`
        : "custom";

    return (
        <>
            <section className="page-heading settings-heading"><div>
                <span className="hero-pill"><SettingsIcon size={15} /> Browser settings</span>
                <h1>Configure this browser</h1>
                <p>Personal settings stay in this browser. Preset secrets stay on the server.</p>
            </div></section>

            <form className="settings-grid" onChange={onChange} onSubmit={submit}>
                <div className="settings-columns">
                    <Panel className="configuration-panel settings-card">
                        <Panel.Header className="settings-card-header">
                            <div className="settings-card-title">
                                <span className="settings-subheading-icon settings-ai-icon">AI</span>
                                <div>
                                    <Panel.Title>Model provider</Panel.Title>
                                    <Panel.Description>Choose a server preset or your own API.</Panel.Description>
                                </div>
                            </div>
                            <StatusBadge ready={providerReady} />
                        </Panel.Header>
                        <Panel.Content>
                            <label className="settings-field" htmlFor="provider-select">
                                <span>Provider</span>
                                <select
                                    className="settings-select"
                                    disabled={locked}
                                    id="provider-select"
                                    onChange={(event) => {
                                        const value = event.target.value;
                                        update("provider_type", value === "custom" ? "custom" : "preset");
                                        update("preset_id", value.startsWith("preset:") ? value.slice(7) : "");
                                    }}
                                    value={providerValue}
                                >
                                    <option value="custom">Custom OpenAI-compatible API</option>
                                    {draft.presets.map((preset) => (
                                        <option key={preset.id} value={`preset:${preset.id}`}>
                                            {preset.name} · {preset.model}
                                        </option>
                                    ))}
                                </select>
                            </label>

                            {draft.provider_type === "custom" && (
                                <>
                                    <label className="settings-field">
                                        <span>API key</span>
                                        <input
                                            autoComplete="off"
                                            disabled={locked}
                                            onChange={(event) => update("openai_api_key", event.target.value)}
                                            type="password"
                                            value={draft.openai_api_key}
                                        />
                                    </label>
                                    <label className="settings-field">
                                        <span>OpenAI-compatible API Base URL</span>
                                        <div><GlobeIcon size={17} /><input
                                            disabled={locked}
                                            onChange={(event) => update("openai_base_url", event.target.value)}
                                            placeholder="https://api.deepseek.com"
                                            type="url"
                                            value={draft.openai_base_url}
                                        /></div>
                                        <small>Leave blank for OpenAI.</small>
                                    </label>
                                    <label className="settings-field">
                                        <span>API protocol</span>
                                        <select
                                            className="settings-select"
                                            disabled={locked}
                                            onChange={(event) => update("openai_api_mode", event.target.value)}
                                            value={draft.openai_api_mode}
                                        >
                                            <option value="responses">Responses API</option>
                                            <option value="chat_completions">Chat Completions</option>
                                        </select>
                                    </label>
                                    <label className="settings-field">
                                        <span>Model name</span>
                                        <input
                                            disabled={locked}
                                            onChange={(event) => update("openai_model", event.target.value)}
                                            value={draft.openai_model}
                                        />
                                    </label>
                                </>
                            )}
                        </Panel.Content>
                    </Panel>

                    <Panel className="configuration-panel settings-card">
                        <Panel.Header className="settings-card-header">
                            <div className="settings-card-title">
                                <span className="settings-subheading-icon">SV</span>
                                <div>
                                    <Panel.Title>Remote servers</Panel.Title>
                                    <Panel.Description>
                                        {draft.server_presets.length
                                            ? `${draft.server_presets.length} server preset${draft.server_presets.length === 1 ? "" : "s"} available.`
                                            : "Add a private Custom Server if needed."}
                                    </Panel.Description>
                                </div>
                            </div>
                            <StatusBadge ready={serverReady} />
                        </Panel.Header>
                        <Panel.Content>
                            {draft.server_presets.length > 0 && (
                                <div className="settings-preset-list">
                                    {draft.server_presets.map((server) => (
                                        <p key={server.id}><strong>{server.name}</strong><span>{server.url}</span></p>
                                    ))}
                                </div>
                            )}
                            <label className="settings-field">
                                <span>Custom Server URL</span>
                                <div><GlobeIcon size={17} /><input
                                    disabled={locked}
                                    onChange={(event) => update("custom_server_url", event.target.value)}
                                    placeholder="https://servicepath.example.com"
                                    type="url"
                                    value={draft.custom_server_url}
                                /></div>
                            </label>
                            <label className="settings-field">
                                <span>Custom Server token</span>
                                <input
                                    autoComplete="off"
                                    disabled={locked}
                                    onChange={(event) => update("custom_server_token", event.target.value)}
                                    type="password"
                                    value={draft.custom_server_token}
                                />
                            </label>
                        </Panel.Content>
                    </Panel>
                </div>

                <div className="settings-save-bar">
                    <div>
                        <strong className="settings-save-title">Private by default</strong>
                        <p className="settings-save-description">
                            Custom values stay in this browser. Preset secrets stay on the server.
                        </p>
                        <p className={saveStatus === "success" ? "success-message" : "sr-only"} role="status">
                            {saveStatus === "success" ? "Browser settings saved." : ""}
                        </p>
                        <p className={saveStatus === "error" ? "form-error" : "sr-only"} role="alert">
                            {saveStatus === "error" ? saveError : ""}
                        </p>
                        {diagnosisRunning && <p>Wait for the current investigation before changing settings.</p>}
                    </div>
                    <button className="save-button" disabled={locked} type="submit">
                        {saving && <Spinner size="sm" />}{saving ? "Saving" : "Save in this browser"}
                    </button>
                </div>
            </form>
        </>
    );
}
