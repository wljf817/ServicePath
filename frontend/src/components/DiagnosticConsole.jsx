import {Card} from "@heroui/react";
import {useState} from "react";

import {CopyIcon, TerminalIcon} from "./Icons";

const statusLabels = {
    passed: "PASS",
    warning: "WARN",
    error: "ERROR",
    skipped: "SKIP",
};

function detailLines(value, prefix = "") {
    const lines = [];

    Object.entries(value || {}).forEach(([key, item]) => {
        const label = prefix ? `${prefix} > ${key}` : key;
        if (item && typeof item === "object" && !Array.isArray(item)) {
            lines.push(...detailLines(item, label));
        } else {
            const display = Array.isArray(item) ? item.join(", ") || "None" : String(item);
            lines.push({label, display});
        }
    });

    return lines;
}

export default function DiagnosticConsole({report, label = "Agent Tool Evidence", loading = false}) {
    const [showRaw, setShowRaw] = useState(true);
    const [copyState, setCopyState] = useState("Copy JSON");
    const checks = report
        ? (report.layers || []).flatMap((layer) => (
            layer.key === "dns" && report.traceroute
                ? [layer, report.traceroute]
                : [layer]
        ))
        : [];

    async function copyReport() {
        if (!report) {
            return;
        }

        try {
            await navigator.clipboard.writeText(JSON.stringify(report, null, 2));
            setCopyState("Copied");
        } catch {
            setCopyState("Copy failed");
        }

        window.setTimeout(() => setCopyState("Copy JSON"), 1800);
    }

    return (
        <Card className="console-panel" variant="secondary">
            <Card.Header className="panel-header">
                <div>
                    <span className="section-kicker">AGENT EVIDENCE</span>
                    <Card.Title className="panel-title"><TerminalIcon size={18} /> {label}</Card.Title>
                </div>
                <div className="console-actions">
                    {report && (
                        <>
                            <button
                                aria-pressed={showRaw}
                                className={showRaw ? "console-action console-action-active" : "console-action"}
                                onClick={() => setShowRaw((visible) => !visible)}
                                type="button"
                            >
                                Raw {showRaw ? "on" : "off"}
                            </button>
                            <button className="console-action" onClick={copyReport} type="button">
                                <CopyIcon size={13} /> {copyState}
                            </button>
                        </>
                    )}
                    <span className={loading ? "live-dot live-dot-loading" : "live-dot"} />
                </div>
            </Card.Header>
            <Card.Content className="terminal-window">
                <div className="terminal-chrome" aria-hidden="true">
                    <span /><span /><span />
                    <small>servicepath://diagnostics</small>
                </div>
                {loading && (
                    <div className="terminal-loading" aria-live="polite">
                        <p><span className="term-info">[INFO]</span> Starting the diagnostic agent...</p>
                        <p><span className="term-run">[AGENT]</span> Selecting bounded network tools from returned evidence</p>
                        <p className="terminal-prompt"><span>servicepath</span> investigation in progress <i /></p>
                        <div className="terminal-scan-line" aria-hidden="true" />
                    </div>
                )}

                {!loading && !report && (
                    <>
                        <p><span className="term-ready">[READY]</span> Waiting for a website to test...</p>
                        <p className="term-muted">Enter a domain above to begin.</p>
                    </>
                )}

                {report && (
                    <>
                        <p><span className="term-info">[INFO]</span> Target: {report.target.url}</p>
                        <p><span className="term-info">[INFO]</span> Mode: {report.mode}</p>
                        {report.agent && (
                            <>
                                <p><span className="term-return">[AGENT]</span> Model: {report.agent.model}</p>
                                <p><span className="term-return">[BUDGET]</span> {report.agent.checks_used} / {report.agent.max_checks} checks used</p>
                                {report.agent.model_calls > 0 && (
                                    <p>
                                        <span className="term-return">[USAGE]</span> {report.agent.model_calls} model calls · {report.agent.token_usage?.total || 0} tokens
                                    </p>
                                )}
                                {report.agent.requested_tools?.map((entry, index) => (
                                    <p className="terminal-indent" key={`request-${entry.tool}-${index}`}>
                                        <span className="term-return">[SELECT {String(index + 1).padStart(2, "0")}]</span> {entry.tool} · {entry.status}
                                    </p>
                                ))}
                                {report.agent.tool_log?.map((entry, index) => (
                                    <p className="terminal-indent" key={`${entry.tool}-${index}`}>
                                        <span className="term-run">[CHECK {String(index + 1).padStart(2, "0")}]</span> {entry.tool} · {entry.status} · {entry.duration_ms} ms
                                    </p>
                                ))}
                            </>
                        )}
                        {checks.map((layer, index) => (
                            <div className="terminal-group" key={`${layer.key}-${index}`}>
                                <p><span className="term-check">[CHECK]</span> {layer.name}</p>
                                <p className="terminal-indent">
                                    <span className={`term-${layer.status}`}>
                                        [{statusLabels[layer.status] || layer.status.toUpperCase()}]
                                    </span> {layer.summary}
                                </p>
                                <p className="terminal-indent"><span className="term-info">[TIME]</span> {layer.duration_ms} ms</p>
                                {detailLines(layer.details).map((detail) => (
                                    <p className="terminal-indent" key={detail.label}>
                                        <span className="term-return">[RETURN]</span> {detail.label}: {detail.display}
                                    </p>
                                ))}
                                {showRaw && (
                                    <div className="terminal-raw-block">
                                        <p className="terminal-indent raw-title"><span className="term-raw">[RAW RETURN]</span> {layer.name} tool result</p>
                                        <pre>{JSON.stringify(layer, null, 2)}</pre>
                                    </div>
                                )}
                            </div>
                        ))}
                        <p className="terminal-done"><span className="term-info">[DONE]</span> Finished in {report.duration_ms} ms · {report.status.toUpperCase()}</p>
                    </>
                )}
            </Card.Content>
        </Card>
    );
}
