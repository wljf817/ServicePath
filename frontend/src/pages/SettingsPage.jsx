import {Button, Card, Input, Spinner} from "@heroui/react";
import {useEffect, useState} from "react";

import {saveAppSettings} from "../api";
import {GlobeIcon, SettingsIcon} from "../components/Icons";

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
            <span className={ready ? "config-icon config-ready" : "config-icon"}><i /></span>
            <div><strong>{label}</strong><p>{description}</p></div>
            <span className={ready ? "config-state ready" : "config-state"}>
                {ready ? "Configured" : "Not configured"}
            </span>
        </div>
    );
}

export default function SettingsPage({appSettings, onSaved}) {
    const settings = appSettings?.settings;
    const [role, setRole] = useState("remote_server");
    const [remoteUrl, setRemoteUrl] = useState("");
    const [password, setPassword] = useState("");
    const [apiToken, setApiToken] = useState("");
    const [openaiKey, setOpenaiKey] = useState("");
    const [openaiModel, setOpenaiModel] = useState("gpt-5.6");
    const [newSettingsPassword, setNewSettingsPassword] = useState("");
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");

    useEffect(() => {
        if (settings) {
            setRole(settings.instance_role);
            setRemoteUrl(settings.remote_service_url);
            setOpenaiModel(appSettings.openai_model);
        }
    }, [appSettings, settings]);

    async function submit(event) {
        event.preventDefault();
        setSaving(true);
        setMessage("");
        setError("");

        try {
            const result = await saveAppSettings({
                instance_role: role,
                remote_service_url: remoteUrl,
                settings_password: password,
                servicepath_api_token: apiToken,
                openai_api_key: openaiKey,
                openai_model: openaiModel,
                new_settings_password: newSettingsPassword,
            });
            onSaved(result);
            setPassword("");
            setApiToken("");
            setOpenaiKey("");
            setNewSettingsPassword("");
            setMessage("Settings saved successfully.");
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setSaving(false);
        }
    }

    if (!appSettings) {
        return <div className="page-loading"><Spinner size="lg" /><p>Loading settings...</p></div>;
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

            <form className="settings-grid" onSubmit={submit}>
                <Card className="settings-panel" variant="secondary">
                    <Card.Header>
                        <div>
                            <span className="section-kicker">EXECUTION</span>
                            <Card.Title>Instance role</Card.Title>
                            <Card.Description>Define how this copy of ServicePath should behave.</Card.Description>
                        </div>
                    </Card.Header>
                    <Card.Content>
                        <div className="role-options">
                            {roles.map((item) => (
                                <button
                                    className={`role-option ${role === item.value ? "role-selected" : ""}`}
                                    key={item.value}
                                    onClick={() => setRole(item.value)}
                                    type="button"
                                >
                                    <span className="role-radio"><i /></span>
                                    <span><strong>{item.title}</strong><small>{item.description}</small></span>
                                </button>
                            ))}
                        </div>

                        <div className="settings-subheading">
                            <span className="settings-subheading-icon">01</span>
                            <div><strong>Remote connection</strong><small>Where remote requests should be sent.</small></div>
                        </div>

                        <label className="settings-field">
                            <span>Deployed ServicePath URL</span>
                            <div><GlobeIcon size={17} /><Input onChange={(event) => setRemoteUrl(event.target.value)} placeholder="https://servicepath.example" value={remoteUrl} variant="secondary" /></div>
                            <small>Required by a Local Device for Remote Test and Compare Both.</small>
                        </label>
                    </Card.Content>
                </Card>

                <Card className="configuration-panel" variant="secondary">
                    <Card.Header>
                        <div>
                            <span className="section-kicker">CONFIGURATION</span>
                            <Card.Title>Service status</Card.Title>
                        </div>
                    </Card.Header>
                    <Card.Content>
                        <ConfigurationStatus
                            description="Protects the remote diagnostic endpoint."
                            label="Remote API token"
                            ready={appSettings.api_token_configured}
                        />
                        <ConfigurationStatus
                            description="Enables generated diagnosis and repair advice."
                            label="OpenAI analysis"
                            ready={appSettings.ai_configured}
                        />
                        <ConfigurationStatus
                            description="Protects setting changes on a public server."
                            label="Settings password"
                            ready={appSettings.password_required}
                        />
                        <div className="secret-fields settings-secret-group">
                            <div className="settings-subheading">
                                <span className="settings-subheading-icon">02</span>
                                <div><strong>Remote service</strong><small>Authenticate calls between ServicePath instances.</small></div>
                            </div>
                            <label className="settings-field">
                                <span>Remote API token</span>
                                <Input
                                    onChange={(event) => setApiToken(event.target.value)}
                                    placeholder="Leave blank to keep the current token"
                                    type="password"
                                    value={apiToken}
                                    variant="secondary"
                                />
                            </label>
                        </div>
                        <div className="settings-secret-group">
                            <div className="settings-subheading">
                                <span className="settings-subheading-icon settings-ai-icon">AI</span>
                                <div><strong>AI analysis</strong><small>Generate explanations and practical next steps.</small></div>
                            </div>
                            <label className="settings-field">
                                <span>OpenAI API key</span>
                                <Input
                                    onChange={(event) => setOpenaiKey(event.target.value)}
                                    placeholder="Leave blank to keep the current key"
                                    type="password"
                                    value={openaiKey}
                                    variant="secondary"
                                />
                            </label>
                            <label className="settings-field">
                                <span>OpenAI model</span>
                                <Input
                                    onChange={(event) => setOpenaiModel(event.target.value)}
                                    placeholder="gpt-5.6"
                                    value={openaiModel}
                                    variant="secondary"
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
                                <Input
                                    onChange={(event) => setPassword(event.target.value)}
                                    placeholder={appSettings.password_required ? "Required to save changes" : "Not required from localhost"}
                                    type="password"
                                    value={password}
                                    variant="secondary"
                                />
                                <small>Authenticates this update when a password already exists.</small>
                            </label>
                            <label className="settings-field">
                                <span>New settings password</span>
                                <Input
                                    onChange={(event) => setNewSettingsPassword(event.target.value)}
                                    placeholder="Leave blank to keep the current password"
                                    type="password"
                                    value={newSettingsPassword}
                                    variant="secondary"
                                />
                            </label>
                        </div>
                        <p className="security-copy">
                            New secrets are written to the server <code>.env</code> file.
                            Existing values are never returned to this page or saved in SQLite.
                        </p>
                    </Card.Content>
                </Card>

                <div className="settings-save-bar">
                    <div aria-live="polite">
                        {message && <p className="success-message" role="status">{message}</p>}
                        {error && <p className="form-error" role="alert">{error}</p>}
                        {!message && !error && <p>Changes apply to the next diagnosis.</p>}
                    </div>
                    <Button className="save-button" isDisabled={saving} isPending={saving} type="submit" variant="primary">
                        {saving && <Spinner color="current" size="sm" />}
                        {saving ? "Saving settings" : "Save all settings"}
                    </Button>
                </div>
            </form>
        </>
    );
}
