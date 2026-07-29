import {Button, Card, Input, Spinner} from "@heroui/react";
import {useEffect, useState} from "react";

import {startDiagnosis} from "../api";
import DiagnosticConsole from "../components/DiagnosticConsole";
import {ArrowIcon, GlobeIcon} from "../components/Icons";
import LayerList from "../components/LayerList";
import NetworkPathVisual from "../components/NetworkPathVisual";
import ScanProgress from "../components/ScanProgress";

const modes = [
    {value: "local", title: "Local Test", description: "This device and network"},
    {value: "remote", title: "Remote Test", description: "Deployed ServicePath server"},
    {value: "compare", title: "Compare Both", description: "Local and remote side by side"},
];

export default function DashboardPage({appSettings, navigate}) {
    const role = appSettings?.settings.instance_role || "remote_server";
    const [domain, setDomain] = useState("");
    const [mode, setMode] = useState("remote");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        setMode(role === "remote_server" ? "remote" : "local");
    }, [role]);

    function modeDisabled(value) {
        return role === "remote_server" && value !== "remote";
    }

    async function submit(event) {
        event.preventDefault();
        setError("");
        setLoading(true);

        try {
            const result = await startDiagnosis(domain, mode);
            navigate(result.report_url, {preserveScroll: true});
        } catch (requestError) {
            setError(requestError.message);
            setLoading(false);
        }
    }

    return (
        <>
            <section className="hero-section dashboard-hero">
                <div className="hero-copy">
                    <span className="hero-pill"><i /> Network observability, simplified</span>
                    <h1>See exactly where a <span>connection breaks.</span></h1>
                    <p>
                        Trace a request from the client to the application. ServicePath
                        captures every return, identifies the first unhealthy layer, and
                        prepares the evidence for AI analysis.
                    </p>
                    <div className="hero-facts" aria-label="ServicePath capabilities">
                        <span><strong>05</strong> diagnostic layers</span>
                        <span><strong>RAW</strong> return data</span>
                        <span><strong>AI</strong> guided analysis</span>
                    </div>
                </div>
                <NetworkPathVisual loading={loading} />
            </section>

            <Card className="diagnostic-card">
                <Card.Content>
                    <form onSubmit={submit}>
                        <div className="form-heading">
                            <div>
                                <span className="section-kicker">NEW TRACE</span>
                                <h2>Start a website diagnosis</h2>
                                <p>Enter a public website or domain. The scan runs from the selected location.</p>
                            </div>
                            <span className="role-chip">
                                {role === "remote_server" ? "Remote server" : "Local device"}
                            </span>
                        </div>

                        <label className="field-label" htmlFor="domain">Target website</label>
                        <div className="domain-row">
                            <div className="domain-input-wrap">
                                <GlobeIcon size={19} />
                                <Input
                                    autoComplete="off"
                                    className="domain-input"
                                    id="domain"
                                    onChange={(event) => setDomain(event.target.value)}
                                    placeholder="example.com"
                                    required
                                    value={domain}
                                    variant="secondary"
                                />
                            </div>
                            <Button
                                className="start-button"
                                isDisabled={loading}
                                isPending={loading}
                                size="lg"
                                type="submit"
                                variant="primary"
                            >
                                {loading ? <Spinner color="current" size="sm" /> : <ArrowIcon size={19} />}
                                {loading ? "Running checks" : "Start diagnosis"}
                            </Button>
                        </div>

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
                                            {disabled ? (
                                                <span className="mode-unavailable">Unavailable</span>
                                            ) : (
                                                <span className="mode-radio"><i /></span>
                                            )}
                                        </label>
                                    );
                                })}
                            </div>
                        </fieldset>

                        <ScanProgress loading={loading} mode={mode} />
                    </form>
                </Card.Content>
            </Card>

            <section className="dashboard-grid">
                <DiagnosticConsole loading={loading} />
                <LayerList />
            </section>
        </>
    );
}
