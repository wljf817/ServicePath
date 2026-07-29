import {Button, Card, Input, Spinner} from "@heroui/react";
import {useEffect, useState} from "react";

import {startDiagnosis} from "../api";
import DiagnosticConsole from "../components/DiagnosticConsole";
import {ArrowIcon, GlobeIcon} from "../components/Icons";
import LayerList from "../components/LayerList";

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
            <section className="hero-section">
                <div>
                    <span className="hero-pill"><i /> Five-layer diagnostics</span>
                    <h1>Trace the failure.<br /><span>Fix the right layer.</span></h1>
                    <p>
                        Inspect client network, DNS, TCP, TLS, and HTTP from one clean
                        diagnostic path—then send the evidence to AI when configured.
                    </p>
                </div>
                <div className="hero-orbit" aria-hidden="true">
                    <span className="orbit-ring orbit-one" />
                    <span className="orbit-ring orbit-two" />
                    <span className="orbit-core"><GlobeIcon size={34} /></span>
                    <i className="orbit-node node-one" />
                    <i className="orbit-node node-two" />
                    <i className="orbit-node node-three" />
                </div>
            </section>

            <Card className="diagnostic-card">
                <Card.Content>
                    <form onSubmit={submit}>
                        <div className="form-heading">
                            <div>
                                <span className="section-kicker">NEW DIAGNOSIS</span>
                                <h2>Which website should we inspect?</h2>
                            </div>
                            <span className="role-chip">
                                {role === "remote_server" ? "Remote server" : "Local device"}
                            </span>
                        </div>

                        <label className="field-label" htmlFor="domain">Website or domain</label>
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

                        {error && <p className="form-error">{error}</p>}

                        <div className="mode-grid" role="radiogroup" aria-label="Run test from">
                            {modes.map((item) => {
                                const disabled = modeDisabled(item.value);
                                return (
                                    <button
                                        aria-checked={mode === item.value}
                                        className={`mode-option ${mode === item.value ? "mode-selected" : ""}`}
                                        disabled={disabled || loading}
                                        key={item.value}
                                        onClick={() => setMode(item.value)}
                                        role="radio"
                                        type="button"
                                    >
                                        <span className="mode-radio"><i /></span>
                                        <span><strong>{item.title}</strong><small>{item.description}</small></span>
                                        {disabled && <em>Unavailable here</em>}
                                    </button>
                                );
                            })}
                        </div>
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
