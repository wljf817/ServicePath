import {useEffect, useState} from "react";

import DiagnosticConsole from "../components/DiagnosticConsole";
import {ArrowIcon, GlobeIcon} from "../components/Icons";
import LayerList from "../components/LayerList";
import NetworkPathVisual from "../components/NetworkPathVisual";
import ScanProgress from "../components/ScanProgress";
import Panel from "../components/ui/Panel";
import Spinner from "../components/ui/Spinner";

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
    const [domain, setDomain] = useState(diagnosis.target || "");
    const [location, setLocation] = useState(diagnosis.location || "local");
    const runState = diagnosis.status === "complete" ? "idle" : diagnosis.status;
    const error = diagnosis.error;
    const loading = runState === "running";
    const providerConfigured = appSettings?.provider_type === "preset"
        ? appSettings.presets.some((preset) => preset.id === appSettings.preset_id)
        : Boolean(
            appSettings?.provider_type === "custom"
            && appSettings.openai_api_key
            && appSettings.openai_model
        );
    const customServerConfigured = Boolean(
        appSettings?.custom_server_url && appSettings?.custom_server_token
    );
    const selectedServer = location.startsWith("preset:")
        ? appSettings?.server_presets.find(
            (server) => server.id === location.slice(7)
        )
        : null;
    const locationConfigured = (
        location === "local"
        || (location === "custom" && customServerConfigured)
        || Boolean(selectedServer)
    );
    const unavailable = Boolean(
        settingsReady
        && (!providerConfigured || !locationConfigured)
    );

    useEffect(() => {
        if (["running", "error"].includes(diagnosis.status)) {
            setDomain(diagnosis.target);
            setLocation(diagnosis.location);
        }
    }, [diagnosis.location, diagnosis.status, diagnosis.target]);

    function submit(event) {
        event.preventDefault();
        if (
            loading
            || !settingsReady
            || unavailable
        ) {
            return;
        }
        onStartDiagnosis(domain, location);
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
                        </div>

                        <div className="domain-row">
                            <div>
                                <label className="field-label" htmlFor="domain">Target website</label>
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
                            </div>
                            <div>
                                <label className="field-label" htmlFor="run-location">Run from</label>
                                <select
                                    className="location-select"
                                    disabled={loading || !settingsReady}
                                    id="run-location"
                                    onChange={(event) => setLocation(event.target.value)}
                                    value={location}
                                >
                                    <option value="local">Current instance</option>
                                    {appSettings?.server_presets.map((server) => (
                                        <option key={server.id} value={`preset:${server.id}`}>
                                            {server.name}
                                        </option>
                                    ))}
                                    <option disabled={!customServerConfigured} value="custom">
                                        Custom server
                                    </option>
                                </select>
                            </div>
                            <button
                                aria-busy={loading}
                                className="start-button"
                                disabled={loading || unavailable || !settingsReady}
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
                        {unavailable && (
                            <p className="form-error" role="alert">
                                {!providerConfigured
                                    ? "Select a preset model or configure a custom API."
                                    : "Select an available server or configure a Custom Server in Settings."}
                            </p>
                        )}
                        {error && <p className="form-error" role="alert">{error}</p>}

                        <ScanProgress
                            locationLabel={selectedServer?.name || {
                                custom: "Custom server",
                                local: "Current instance",
                            }[location]}
                            state={runState}
                        />
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
