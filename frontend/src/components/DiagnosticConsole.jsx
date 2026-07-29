import {Card} from "@heroui/react";

import {TerminalIcon} from "./Icons";

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

export default function DiagnosticConsole({report, label = "Diagnostic Console", loading = false}) {
    return (
        <Card className="console-panel" variant="secondary">
            <Card.Header className="panel-header">
                <div>
                    <span className="section-kicker">LIVE OUTPUT</span>
                    <Card.Title className="panel-title"><TerminalIcon size={18} /> {label}</Card.Title>
                </div>
                <span className={loading ? "live-dot live-dot-loading" : "live-dot"} />
            </Card.Header>
            <Card.Content className="terminal-window">
                {loading && (
                    <>
                        <p><span className="term-info">[INFO]</span> Starting diagnostics...</p>
                        <p><span className="term-run">[RUN]</span> Waiting for the five-layer report</p>
                    </>
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
                        {report.layers.map((layer) => (
                            <div className="terminal-group" key={layer.key}>
                                <p><span className="term-check">[CHECK]</span> {layer.name}</p>
                                <p className="terminal-indent">
                                    <span className={`term-${layer.status}`}>
                                        [{statusLabels[layer.status]}]
                                    </span> {layer.summary}
                                </p>
                                <p className="terminal-indent"><span className="term-info">[TIME]</span> {layer.duration_ms} ms</p>
                                {detailLines(layer.details).map((detail) => (
                                    <p className="terminal-indent" key={detail.label}>
                                        <span className="term-return">[RETURN]</span> {detail.label}: {detail.display}
                                    </p>
                                ))}
                                <p className="terminal-indent raw-title"><span className="term-raw">[RAW RETURN]</span> {layer.name} function result</p>
                                <pre>{JSON.stringify(layer, null, 2)}</pre>
                            </div>
                        ))}
                        <p className="terminal-done"><span className="term-info">[DONE]</span> Finished in {report.duration_ms} ms · {report.status.toUpperCase()}</p>
                    </>
                )}
            </Card.Content>
        </Card>
    );
}
