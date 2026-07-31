import {useEffect, useRef, useState} from "react";

import {
    detailLines,
    reportLayers,
    runtimeState,
    statusLabel,
} from "../domain/diagnostics";
import {CopyIcon, TerminalIcon} from "./Icons";
import Panel from "./ui/Panel";

export default function DiagnosticConsole({
    report,
    label = "Agent Tool Evidence",
    loading = false,
    state,
}) {
    const [showRaw, setShowRaw] = useState(true);
    const [copyState, setCopyState] = useState("Copy JSON");
    const [copyAnnouncement, setCopyAnnouncement] = useState("");
    const copyOperationRef = useRef(0);
    const copyResetTimerRef = useRef(null);
    const currentState = runtimeState(state, loading);
    const running = currentState === "running";
    const liveDotClass = currentState === "running"
        ? "live-dot live-dot-loading"
        : (currentState === "error" ? "live-dot live-dot-error" : "live-dot");
    const checks = reportLayers(report);

    useEffect(() => {
        copyOperationRef.current += 1;
        if (copyResetTimerRef.current !== null) {
            window.clearTimeout(copyResetTimerRef.current);
            copyResetTimerRef.current = null;
        }
        setCopyState("Copy JSON");
        setCopyAnnouncement("");
    }, [report]);

    useEffect(() => () => {
        copyOperationRef.current += 1;
        if (copyResetTimerRef.current !== null) {
            window.clearTimeout(copyResetTimerRef.current);
        }
    }, []);

    async function copyReport() {
        if (!report) {
            return;
        }

        const operation = copyOperationRef.current + 1;
        copyOperationRef.current = operation;
        if (copyResetTimerRef.current !== null) {
            window.clearTimeout(copyResetTimerRef.current);
            copyResetTimerRef.current = null;
        }
        setCopyState("Copying");
        setCopyAnnouncement("");

        let nextState;
        let announcement;
        try {
            await navigator.clipboard.writeText(JSON.stringify(report, null, 2));
            nextState = "Copied";
            announcement = "Report JSON copied.";
        } catch {
            nextState = "Copy failed";
            announcement = "Report JSON could not be copied.";
        }

        if (copyOperationRef.current !== operation) {
            return;
        }

        setCopyState(nextState);
        setCopyAnnouncement(announcement);
        copyResetTimerRef.current = window.setTimeout(() => {
            if (copyOperationRef.current === operation) {
                setCopyState("Copy JSON");
            }
            copyResetTimerRef.current = null;
        }, 1800);
    }

    return (
        <Panel aria-busy={running} className="console-panel" data-state={currentState}>
            <Panel.Header className="panel-header">
                <div>
                    <span className="section-kicker">AGENT EVIDENCE</span>
                    <Panel.Title className="panel-title"><TerminalIcon size={18} /> {label}</Panel.Title>
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
                            <button
                                aria-busy={copyState === "Copying"}
                                className="console-action"
                                onClick={copyReport}
                                type="button"
                            >
                                <CopyIcon size={13} /> {copyState}
                            </button>
                        </>
                    )}
                    <span
                        aria-hidden="true"
                        className={liveDotClass}
                    />
                </div>
            </Panel.Header>
            <span aria-atomic="true" className="sr-only" role="status">
                {copyAnnouncement}
            </span>
            <Panel.Content className="terminal-window">
                <div className="terminal-chrome" aria-hidden="true">
                    <span /><span /><span />
                    <small>servicepath://diagnostics</small>
                </div>
                {running && (
                    <div className="terminal-loading">
                        <p><span className="term-info">[INFO]</span> Starting the diagnostic agent...</p>
                        <p><span className="term-run">[AGENT]</span> Selecting bounded network tools from returned evidence</p>
                        <p className="terminal-prompt"><span>servicepath</span> investigation in progress <i aria-hidden="true" /></p>
                        <div className="terminal-scan-line" aria-hidden="true" />
                    </div>
                )}

                {currentState === "idle" && !report && (
                    <>
                        <p><span className="term-ready">[READY]</span> Waiting for a website to test...</p>
                        <p className="term-muted">Enter a domain above to begin.</p>
                    </>
                )}

                {currentState === "error" && !report && (
                    <>
                        <p><span className="term-error">[ERROR]</span> Investigation stopped.</p>
                        <p className="term-muted">Review the error above and try again.</p>
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
                                    <p
                                        className="terminal-indent"
                                        key={`request-${entry.tool}-${index}`}
                                        style={{"--motion-index": index}}
                                    >
                                        <span className="term-return">[SELECT {String(index + 1).padStart(2, "0")}]</span> {entry.tool} · {entry.status}
                                    </p>
                                ))}
                                {report.agent.tool_log?.map((entry, index) => (
                                    <p
                                        className="terminal-indent"
                                        key={`${entry.tool}-${index}`}
                                        style={{"--motion-index": index}}
                                    >
                                        <span className="term-run">[CHECK {String(index + 1).padStart(2, "0")}]</span> {entry.tool} · {entry.status} · {entry.duration_ms} ms
                                    </p>
                                ))}
                            </>
                        )}
                        {checks.map((layer, index) => (
                            <div
                                className="terminal-group"
                                key={`${layer.key}-${index}`}
                                style={{"--motion-index": index}}
                            >
                                <p><span className="term-check">[CHECK]</span> {layer.name}</p>
                                <p className="terminal-indent">
                                    <span className={`term-${layer.status}`}>
                                        [{statusLabel(layer.status)}]
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
            </Panel.Content>
        </Panel>
    );
}
