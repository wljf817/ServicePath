import {useEffect, useState} from "react";

import {GlobeIcon, SettingsIcon} from "../components/Icons";
import Panel from "../components/ui/Panel";
import Spinner from "../components/ui/Spinner";

const roles = [
    {
        value: "remote_server",
        title: "Deployed Remote Server",
        description: "Remote Test runs on this Flask server.",
    },
    {
        value: "local_device",
        title: "Local Device",
        description: "Local Test runs here; Remote Test calls the configured server.",
    },
];

function ConfigurationStatus({ready, label, description}) {
    return (
        <div className="config-row">
            <span
                aria-hidden="true"
                className={ready ? "config-icon config-ready" : "config-icon"}
            >
                <i />
            </span>
            <div><strong>{label}</strong><p>{description}</p></div>
            <span className={ready ? "config-state ready" : "config-state"}>
                {ready ? "Configured" : "Not configured"}
            </span>
        </div>
    );
}

export default function SettingsPage({
    appSettings,
    diagnosisRunning,
    draft,
    error: loadError,
    onChange,
    onDraftChange,
    onReconcile,
    onRetry,
    onSave,
    saveBlocking,
    saveError,
    saveStatus,
    status,
}) {
    const settings = appSettings?.settings;
    const initialDraft = draft || {
        instance_role: settings?.instance_role || "remote_server",
        new_settings_password: "",
        openai_api_key: "",
        openai_api_mode: appSettings?.openai_api_mode || "auto",
        openai_base_url: appSettings?.openai_base_url || "",
        openai_model: appSettings?.openai_model || "gpt-5.6",
        remote_service_url: settings?.remote_service_url || "",
        servicepath_api_token: "",
        settings_password: "",
    };
    const [role, setRole] = useState(initialDraft.instance_role);
    const [remoteUrl, setRemoteUrl] = useState(initialDraft.remote_service_url);
    const [password, setPassword] = useState(initialDraft.settings_password);
    const [apiToken, setApiToken] = useState(initialDraft.servicepath_api_token);
    const [openaiKey, setOpenaiKey] = useState(initialDraft.openai_api_key);
    const [openaiBaseUrl, setOpenaiBaseUrl] = useState(initialDraft.openai_base_url);
    const [openaiApiMode, setOpenaiApiMode] = useState(initialDraft.openai_api_mode);
    const [openaiModel, setOpenaiModel] = useState(initialDraft.openai_model);
    const [newSettingsPassword, setNewSettingsPassword] = useState(initialDraft.new_settings_password);
    const saving = saveStatus === "saving";
    const locked = saving || diagnosisRunning || saveBlocking;
    const saveState = saving ? "running" : (saveStatus === "error" ? "error" : "idle");

    useEffect(() => {
        if (settings && !draft) {
            setRole(settings.instance_role);
            setRemoteUrl(settings.remote_service_url);
            setPassword("");
            setApiToken("");
            setOpenaiKey("");
            setOpenaiBaseUrl(appSettings.openai_base_url || "");
            setOpenaiApiMode(appSettings.openai_api_mode || "auto");
            setOpenaiModel(appSettings.openai_model);
            setNewSettingsPassword("");
        }
    }, [appSettings, draft, settings]);

    function updateDraft(setter, field, value) {
        setter(value);
        onDraftChange(field, value);
    }

    async function submit(event) {
        event.preventDefault();
        if (locked) {
            return;
        }

        try {
            // App owns the request so navigation does not discard saved settings.
            await onSave({
                instance_role: role,
                remote_service_url: remoteUrl,
                settings_password: password,
                servicepath_api_token: apiToken,
                openai_api_key: openaiKey,
                openai_base_url: openaiBaseUrl,
                openai_api_mode: openaiApiMode,
                openai_model: openaiModel,
                new_settings_password: newSettingsPassword,
            });
        } catch {
            // App keeps the error visible across navigation.
        }
    }

    if (status === "loading") {
        return (
            <div aria-atomic="true" className="page-loading" role="status">
                <Spinner size="lg" />
                <p>Loading settings...</p>
            </div>
        );
    }

    if (status === "error" || !appSettings) {
        return (
            <Panel className="state-card">
                <Panel.Content>
                    <h1>Settings unavailable</h1>
                    <p role="alert">{loadError || "Application settings could not be loaded."}</p>
                    <button className="secondary-button" onClick={onRetry} type="button">Try again</button>
                </Panel.Content>
            </Panel>
        );
    }

    return (
        <>
            <section className="page-heading">
                <div>
                    <span className="hero-pill"><SettingsIcon size={15} /> Application settings</span>
                    <h1>Configure your workspace</h1>
                    <p>Choose where tests run and connect the services used by this instance.</p>
                </div>
            </section>

            <form
                className="settings-grid"
                data-state={saveState}
                onChange={onChange}
                onSubmit={submit}
            >
                <Panel className="settings-panel">
                    <Panel.Header>
                        <div>
                            <span className="section-kicker">EXECUTION</span>
                            <Panel.Title>Instance role</Panel.Title>
                            <Panel.Description>Define how this copy of ServicePath should behave.</Panel.Description>
                        </div>
                    </Panel.Header>
                    <Panel.Content>
                        <fieldset>
                            <legend className="sr-only">Instance role</legend>
                            <div className="role-options">
                                {roles.map((item) => (
                                    <label
                                        className={`role-option ${role === item.value ? "role-selected" : ""}`}
                                        key={item.value}
                                    >
                                        <input
                                            checked={role === item.value}
                                            disabled={locked}
                                            name="instance-role"
                                            onChange={() => updateDraft(
                                                setRole,
                                                "instance_role",
                                                item.value,
                                            )}
                                            type="radio"
                                            value={item.value}
                                        />
                                        <span aria-hidden="true" className="role-radio"><i /></span>
                                        <span><strong>{item.title}</strong><small>{item.description}</small></span>
                                    </label>
                                ))}
                            </div>
                        </fieldset>

                        <div className="settings-subheading">
                            <span className="settings-subheading-icon">01</span>
                            <div><strong>Remote connection</strong><small>Where remote requests should be sent.</small></div>
                        </div>

                        <label className="settings-field">
                            <span>Deployed ServicePath URL</span>
                            <div>
                                <GlobeIcon size={17} />
                                <input
                                    disabled={locked}
                                    onChange={(event) => updateDraft(
                                        setRemoteUrl,
                                        "remote_service_url",
                                        event.target.value,
                                    )}
                                    placeholder="https://servicepath.example"
                                    type="url"
                                    value={remoteUrl}
                                />
                            </div>
                            <small>Required by a Local Device for Remote Test and Compare Both.</small>
                        </label>
                    </Panel.Content>
                </Panel>

                <Panel className="configuration-panel">
                    <Panel.Header>
                        <div>
                            <span className="section-kicker">CONFIGURATION</span>
                            <Panel.Title>Service status</Panel.Title>
                        </div>
                    </Panel.Header>
                    <Panel.Content>
                        <ConfigurationStatus
                            description="Protects the remote diagnostic endpoint."
                            label="Remote API token"
                            ready={appSettings.api_token_configured}
                        />
                        <ConfigurationStatus
                            description="Required for autonomous tool selection and diagnosis."
                            label="Diagnostic agent"
                            ready={appSettings.agent_configured}
                        />
                        <ConfigurationStatus
                            description="Protects setting changes on a public server."
                            label="Settings password"
                            ready={appSettings.password_required}
                        />
                        <div className="settings-secret-group">
                            <div className="settings-subheading">
                                <span className="settings-subheading-icon">02</span>
                                <div><strong>Remote service</strong><small>Authenticate calls between ServicePath instances.</small></div>
                            </div>
                            <label className="settings-field">
                                <span>Remote API token</span>
                                <input
                                    autoComplete="off"
                                    disabled={locked}
                                    onChange={(event) => updateDraft(
                                        setApiToken,
                                        "servicepath_api_token",
                                        event.target.value,
                                    )}
                                    placeholder="Leave blank to keep the current token"
                                    type="password"
                                    value={apiToken}
                                />
                            </label>
                        </div>
                        <div className="settings-secret-group">
                            <div className="settings-subheading">
                                <span className="settings-subheading-icon settings-ai-icon">AI</span>
                                <div><strong>Diagnostic agent</strong><small>Choose tools, evaluate evidence, and return next steps.</small></div>
                            </div>
                            <label className="settings-field">
                                <span>Agent API key</span>
                                <input
                                    autoComplete="off"
                                    disabled={locked}
                                    onChange={(event) => updateDraft(
                                        setOpenaiKey,
                                        "openai_api_key",
                                        event.target.value,
                                    )}
                                    placeholder="Leave blank to keep the current key"
                                    type="password"
                                    value={openaiKey}
                                />
                            </label>
                            <label className="settings-field">
                                <span>OpenAI-compatible API base URL</span>
                                <div>
                                    <GlobeIcon size={17} />
                                    <input
                                        disabled={locked}
                                        onChange={(event) => updateDraft(
                                            setOpenaiBaseUrl,
                                            "openai_base_url",
                                            event.target.value,
                                        )}
                                        placeholder="https://api.openai.com/v1"
                                        type="url"
                                        value={openaiBaseUrl}
                                    />
                                </div>
                                <small>Optional. Leave blank for the OpenAI default endpoint.</small>
                            </label>
                            <label className="settings-field">
                                <span>Agent API protocol</span>
                                <select
                                    className="settings-select"
                                    disabled={locked}
                                    onChange={(event) => updateDraft(
                                        setOpenaiApiMode,
                                        "openai_api_mode",
                                        event.target.value,
                                    )}
                                    value={openaiApiMode}
                                >
                                    <option value="auto">Auto (recommended)</option>
                                    <option value="responses">Responses API</option>
                                    <option value="chat_completions">Chat Completions</option>
                                </select>
                                <small>Auto uses Responses for OpenAI and Chat Completions for custom URLs such as DeepSeek.</small>
                            </label>
                            <label className="settings-field">
                                <span>Model name</span>
                                <input
                                    disabled={locked}
                                    onChange={(event) => updateDraft(
                                        setOpenaiModel,
                                        "openai_model",
                                        event.target.value,
                                    )}
                                    placeholder="gpt-5.6"
                                    type="text"
                                    value={openaiModel}
                                />
                            </label>
                        </div>
                        <div className="settings-secret-group">
                            <div className="settings-subheading">
                                <span className="settings-subheading-icon">03</span>
                                <div><strong>Settings access</strong><small>Protect configuration changes on this server.</small></div>
                            </div>
                            <label className="settings-field">
                                <span>Current settings password</span>
                                <input
                                    autoComplete="current-password"
                                    disabled={locked}
                                    onChange={(event) => updateDraft(
                                        setPassword,
                                        "settings_password",
                                        event.target.value,
                                    )}
                                    placeholder={appSettings.password_required ? "Required to save changes" : "Not required from localhost"}
                                    type="password"
                                    value={password}
                                />
                                <small>Authenticates this update when a password already exists.</small>
                            </label>
                            <label className="settings-field">
                                <span>New settings password</span>
                                <input
                                    autoComplete="new-password"
                                    disabled={locked}
                                    onChange={(event) => updateDraft(
                                        setNewSettingsPassword,
                                        "new_settings_password",
                                        event.target.value,
                                    )}
                                    placeholder="Leave blank to keep the current password"
                                    type="password"
                                    value={newSettingsPassword}
                                />
                            </label>
                        </div>
                        <p className="security-copy">
                            New secrets are written to the server <code>.env</code> file.
                            Existing secret values are never returned to this page or saved in SQLite.
                            The non-secret API base URL is shown so it can be edited or cleared.
                        </p>
                    </Panel.Content>
                </Panel>

                <div className="settings-save-bar">
                    <div>
                        <p
                            aria-atomic="true"
                            className={saveStatus === "success" ? "success-message" : "sr-only"}
                            role="status"
                        >
                            {saveStatus === "success" ? "Settings saved successfully." : ""}
                        </p>
                        <p
                            aria-atomic="true"
                            className={saveStatus === "error" ? "form-error" : "sr-only"}
                            role="alert"
                        >
                            {saveStatus === "error" ? saveError : ""}
                        </p>
                        {saveStatus === "error" && saveBlocking && (
                            <button
                                className="inline-action"
                                onClick={onReconcile}
                                type="button"
                            >
                                Reload saved configuration
                            </button>
                        )}
                        {diagnosisRunning ? (
                            <p>Wait for the current investigation before changing settings.</p>
                        ) : saveStatus !== "success" && saveStatus !== "error" && (
                            <p>
                                Changes apply to the next diagnosis in single-process development.
                                Restart every worker in multi-worker production.
                            </p>
                        )}
                    </div>
                    <button aria-busy={saving} className="save-button" disabled={locked} type="submit">
                        {saving && <Spinner size="sm" />}
                        {saving ? "Saving settings" : "Save all settings"}
                    </button>
                </div>
            </form>
        </>
    );
}
