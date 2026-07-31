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

function SettingsCard({children, description, icon, iconClass = "", ready, title}) {
    return (
        <Panel className="configuration-panel settings-card">
            <Panel.Header className="settings-card-header">
                <div className="settings-card-title">
                    <span className={`settings-subheading-icon ${iconClass}`}>{icon}</span>
                    <div>
                        <Panel.Title>{title}</Panel.Title>
                        <Panel.Description>{description}</Panel.Description>
                    </div>
                </div>
                <StatusBadge ready={ready} />
            </Panel.Header>
            <Panel.Content>{children}</Panel.Content>
        </Panel>
    );
}

function SettingsField({children, hint, label, ...props}) {
    return (
        <label className="settings-field" {...props}>
            <span>{label}</span>
            {children}
            {hint && <small>{hint}</small>}
        </label>
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
    }

    function fieldProps(field) {
        return {
            disabled: locked,
            onChange: (event) => update(field, event.target.value),
            value: draft[field],
        };
    }

    function selectProvider(event) {
        const value = event.target.value;
        setDraft((current) => ({
            ...current,
            provider_type: value === "custom" ? "custom" : "preset",
            preset_id: value.startsWith("preset:") ? value.slice(7) : "",
        }));
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
    const serverDescription = draft.server_presets.length
        ? `${draft.server_presets.length} server preset${draft.server_presets.length === 1 ? "" : "s"} available.`
        : "Add a private Custom Server if needed.";

    return (
        <>
            <section className="page-heading settings-heading"><div>
                <span className="hero-pill"><SettingsIcon size={15} /> Browser settings</span>
                <h1>Configure this browser</h1>
                <p>Personal settings stay in this browser. Preset secrets stay on the server.</p>
            </div></section>

            <form className="settings-grid" onChange={onChange} onSubmit={submit}>
                <div className="settings-columns">
                    <SettingsCard
                        description="Choose a server preset or your own API."
                        icon="AI"
                        iconClass="settings-ai-icon"
                        ready={providerReady}
                        title="Model provider"
                    >
                        <SettingsField htmlFor="provider-select" label="Provider">
                            <select
                                className="settings-select"
                                disabled={locked}
                                id="provider-select"
                                onChange={selectProvider}
                                value={providerValue}
                            >
                                <option value="custom">Custom OpenAI-compatible API</option>
                                {draft.presets.map((preset) => (
                                    <option key={preset.id} value={`preset:${preset.id}`}>
                                        {preset.name} · {preset.model}
                                    </option>
                                ))}
                            </select>
                        </SettingsField>

                        {draft.provider_type === "custom" && (
                            <>
                                <SettingsField label="API key">
                                    <input autoComplete="off" type="password" {...fieldProps("openai_api_key")} />
                                </SettingsField>
                                <SettingsField
                                    hint="Leave blank for OpenAI."
                                    label="OpenAI-compatible API Base URL"
                                >
                                    <div><GlobeIcon size={17} /><input
                                        placeholder="https://api.deepseek.com"
                                        type="url"
                                        {...fieldProps("openai_base_url")}
                                    /></div>
                                </SettingsField>
                                <SettingsField label="API protocol">
                                    <select className="settings-select" {...fieldProps("openai_api_mode")}>
                                        <option value="responses">Responses API</option>
                                        <option value="chat_completions">Chat Completions</option>
                                    </select>
                                </SettingsField>
                                <SettingsField label="Model name">
                                    <input {...fieldProps("openai_model")} />
                                </SettingsField>
                            </>
                        )}
                    </SettingsCard>

                    <SettingsCard
                        description={serverDescription}
                        icon="SV"
                        ready={serverReady}
                        title="Remote servers"
                    >
                        {draft.server_presets.length > 0 && (
                            <div className="settings-preset-list">
                                {draft.server_presets.map((server) => (
                                    <p key={server.id}><strong>{server.name}</strong><span>{server.url}</span></p>
                                ))}
                            </div>
                        )}
                        <SettingsField label="Custom Server URL">
                            <div><GlobeIcon size={17} /><input
                                placeholder="https://servicepath.example.com"
                                type="url"
                                {...fieldProps("custom_server_url")}
                            /></div>
                        </SettingsField>
                        <SettingsField label="Custom Server token">
                            <input autoComplete="off" type="password" {...fieldProps("custom_server_token")} />
                        </SettingsField>
                    </SettingsCard>
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
