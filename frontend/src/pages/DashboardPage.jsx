import {useEffect, useRef, useState} from "react";

import DiagnosticConsole from "../components/DiagnosticConsole";
import {ArrowIcon, GlobeIcon} from "../components/Icons";
import LayerList from "../components/LayerList";
import NetworkPathVisual from "../components/NetworkPathVisual";
import ScanProgress from "../components/ScanProgress";
import Panel from "../components/ui/Panel";
import Spinner from "../components/ui/Spinner";

const modes = [
    {value: "client", title: "Client Test", description: "This device and network"},
    {value: "server", title: "Server Test", description: "Connected ServicePath server"},
];

export default function DashboardPage({
    appSettings,
    diagnosis,
    onChange,
    onStartDiagnosis,
    settingsError,
    settingsSaveError,
    settingsSaveStatus,
    settingsStatus,
}) {
    const settingsSaving = settingsSaveStatus === "saving";
    const settingsReady = (
        settingsStatus === "ready"
        && settingsSaveStatus !== "saving"
    );
    const role = appSettings?.settings.instance_role;
    const configuredRoleRef = useRef(null);
    const [domain, setDomain] = useState(diagnosis.target || "");
    const [mode, setMode] = useState(diagnosis.mode || "server");
    const runState = diagnosis.status === "complete" ? "idle" : diagnosis.status;
    const error = diagnosis.error;
    const loading = runState === "running";
    const requiresLocalAgent = role === "server" || mode === "client";
    const agentConfigured = appSettings?.agent_configured;
    const agentUnavailable = Boolean(
        settingsReady && requiresLocalAgent && !agentConfigured,
    );

    useEffect(() => {
        if (!settingsReady || configuredRoleRef.current === role) {
            return;
        }

        configuredRoleRef.current = role;
        if (["complete", "idle"].includes(diagnosis.status)) {
            setMode(role === "server" ? "server" : "client");
        }
    }, [diagnosis.status, role, settingsReady]);

    useEffect(() => {
        if (diagnosis.status === "running") {
            setDomain(diagnosis.target);
            setMode(diagnosis.mode);
        } else if (diagnosis.status === "error" && settingsReady) {
            const nextMode = modeDisabled(diagnosis.mode)
                ? (role === "server" ? "server" : "client")
                : diagnosis.mode;
            setDomain(diagnosis.target);
            setMode(nextMode);
            if (nextMode !== diagnosis.mode) {
                onChange();
            }
        }
    }, [diagnosis.mode, diagnosis.status, diagnosis.target, onChange, role, settingsReady]);

    function modeDisabled(value) {
        return !settingsReady || (role === "server" && value !== "server");
    }

    function submit(event) {
        event.preventDefault();
        if (
            loading
            || !settingsReady
            || agentUnavailable
            || modeDisabled(mode)
        ) {
            return;
        }
        onStartDiagnosis(domain, mode);
    }

    return (
        <>
            <section className="dashboard-hero" data-state={runState}>
                <div className="hero-copy">
                    <span className="hero-pill"><i aria-hidden="true" /> Agent-guided website diagnostics</span>
                    <h1>Let one agent investigate <span>what actually failed.</span></h1>
                    <p>
                        Give ServicePath a public website. Its bounded diagnostic agent
                        chooses the useful network tools, follows the returned evidence,
                        and explains what the results support.
                    </p>
                    <div className="hero-facts" aria-label="ServicePath capabilities">
                        <span><strong>01</strong> diagnostic agent</span>
                        <span><strong>06</strong> bounded tools</span>
                        <span><strong>RAW</strong> evidence retained</span>
                    </div>
                </div>
                <NetworkPathVisual state={runState} />
            </section>

            <Panel className="diagnostic-card" data-state={runState}>
                <Panel.Content>
                    <form onChange={onChange} onSubmit={submit}>
                        <div className="form-heading">
                            <div>
                                <span className="section-kicker">NEW TRACE</span>
                                <h2>Start a website diagnosis</h2>
                                <p>Enter a public website. The agent decides which checks are worth running.</p>
                            </div>
                            <span className="role-chip">
                                {settingsReady
                                    ? (role === "server" ? "Server" : "Client")
                                    : "Configuration pending"}
                            </span>
                        </div>

                        <label className="field-label" htmlFor="domain">Target website</label>
                        <div className="domain-row">
                            <div className="domain-input-wrap">
                                <GlobeIcon size={19} />
                                <input
                                    autoComplete="off"
                                    className="domain-input"
                                    disabled={loading || !settingsReady}
                                    id="domain"
                                    onChange={(event) => setDomain(event.target.value)}
                                    placeholder="example.com"
                                    required
                                    spellCheck="false"
                                    type="text"
                                    value={domain}
                                />
                            </div>
                            <button
                                aria-busy={loading}
                                className="start-button"
                                disabled={loading || agentUnavailable || !settingsReady || modeDisabled(mode)}
                                type="submit"
                            >
                                {loading ? <Spinner size="sm" /> : <ArrowIcon size={19} />}
                                {loading ? "Agent investigating" : "Start investigation"}
                            </button>
                        </div>

                        {settingsStatus === "loading" && (
                            <p className="configuration-message" role="status">
                                Loading application settings...
                            </p>
                        )}
                        {settingsSaving && (
                            <p className="configuration-message" role="status">
                                Applying application settings...
                            </p>
                        )}
                        {settingsSaveStatus === "error" && (
                            <p className="form-error" role="alert">
                                {settingsSaveError || "Application settings were not saved."}
                            </p>
                        )}
                        {settingsStatus === "error" && (
                            <p className="form-error" role="alert">
                                {settingsError || "Application settings could not be loaded."}
                            </p>
                        )}
                        {agentUnavailable && (
                            <p className="form-error" role="alert">
                                The diagnostic agent needs an API key. Configure it in Settings before running this location.
                            </p>
                        )}
                        {error && <p className="form-error" role="alert">{error}</p>}

                        <fieldset className="mode-fieldset">
                            <legend className="field-label">Run test from</legend>
                            <div className="mode-grid">
                                {modes.map((item, index) => {
                                    const disabled = modeDisabled(item.value);
                                    return (
                                        <label
                                            className={`mode-option ${mode === item.value ? "mode-selected" : ""}`}
                                            key={item.value}
                                        >
                                            <input
                                                checked={mode === item.value}
                                                disabled={disabled || loading}
                                                name="diagnostic-mode"
                                                onChange={() => setMode(item.value)}
                                                type="radio"
                                                value={item.value}
                                            />
                                            <span className="mode-number">0{index + 1}</span>
                                            <span className="mode-copy">
                                                <strong>{item.title}</strong>
                                                <small>{item.description}</small>
                                            </span>
                                            {settingsReady && disabled ? (
                                                <span className="mode-unavailable">Unavailable</span>
                                            ) : (
                                                <span aria-hidden="true" className="mode-radio"><i /></span>
                                            )}
                                        </label>
                                    );
                                })}
                            </div>
                        </fieldset>

                        <ScanProgress mode={mode} state={runState} />
                    </form>
                </Panel.Content>
            </Panel>

            <section aria-busy={loading} className="dashboard-grid" data-state={runState}>
                <DiagnosticConsole events={diagnosis.events} state={runState} />
                <LayerList />
            </section>
        </>
    );
}
