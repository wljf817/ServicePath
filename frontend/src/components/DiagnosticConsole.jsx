import {useEffect, useRef, useState} from "react";

import {
    detailLines,
    reportLayers,
    runtimeState,
    statusLabel,
} from "../domain/diagnostics";
import {CopyIcon, TerminalIcon} from "./Icons";
import Panel from "./ui/Panel";

function ToolResult({index, live = false, result}) {
    const label = live ? "RESULT" : "CHECK";
    const labelClass = live ? "term-return" : "term-check";
    const className = live
        ? `terminal-group terminal-live-result term-${result.status}`
        : "terminal-group";

    return (
        <div className={className} style={{"--motion-index": index}}>
            <p><span className={labelClass}>[{label}]</span> {result.name}</p>
            <p className="terminal-indent">
                <span className={`term-${result.status}`}>
                    [{statusLabel(result.status)}]
                </span> {result.summary}
            </p>
            <p className="terminal-indent">
                <span className="term-info">[TIME]</span> {result.duration_ms} ms
            </p>
            {detailLines(result.details).map(({label: field, display}) => (
                <p className="terminal-indent" key={field}>
                    <span className="term-return">[RETURN]</span> {field}: {display}
                </p>
            ))}
        </div>
    );
}

function LiveToolEvent({callNumber, event, index}) {
    if (event.type === "tool_started") {
        return (
            <p className="terminal-indent" style={{"--motion-index": index}}>
                <span className="term-run">[CALL {callNumber}]</span> Agent called {event.tool}
            </p>
        );
    }

    if (event.type === "tool_failed") {
        return (
            <p className="terminal-indent" style={{"--motion-index": index}}>
                <span className="term-error">[ERROR]</span> {event.tool}: {event.error}
            </p>
        );
    }

    return <ToolResult index={index} live result={event.result} />;
}

export default function DiagnosticConsole({
    events = [],
    report,
    label = "Agent Tool Evidence",
    state = "idle",
}) {
    const [copyState, setCopyState] = useState("Copy JSON");
    const [copyAnnouncement, setCopyAnnouncement] = useState("");
    const copyOperationRef = useRef(0);
    const copyResetTimerRef = useRef(null);
    const terminalRef = useRef(null);
    const currentState = runtimeState(state);
    const running = currentState === "running";
    const liveDotClass = currentState === "running"
        ? "live-dot live-dot-loading"
        : (currentState === "error" ? "live-dot live-dot-error" : "live-dot");
    const checks = report ? reportLayers(report) : [];
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

    useEffect(() => {
        if (terminalRef.current && events.length) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        }
    }, [events.length]);

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
                        <button
                            aria-busy={copyState === "Copying"}
                            className="console-action"
                            onClick={copyReport}
                            type="button"
                        >
                            <CopyIcon size={13} /> {copyState}
                        </button>
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
            <Panel.Content
                aria-live="polite"
                className="terminal-window"
                ref={terminalRef}
            >
                <div className="terminal-chrome" aria-hidden="true">
                    <span /><span /><span />
                    <small>servicepath://diagnostics</small>
                </div>
                {running && (
                    <div className="terminal-loading">
                        <p><span className="term-info">[INFO]</span> Starting the diagnostic agent...</p>
                        <p><span className="term-run">[AGENT]</span> Waiting for the model's next tool call</p>
                        <p className="terminal-prompt"><span>servicepath</span> investigation in progress <i aria-hidden="true" /></p>
                        <div className="terminal-scan-line" aria-hidden="true" />
                    </div>
                )}

                {events.map((event, index) => (
                    <LiveToolEvent
                        callNumber={String(
                            events
                                .slice(0, index + 1)
                                .filter((item) => item.type === "tool_started")
                                .length
                        ).padStart(2, "0")}
                        event={event}
                        index={index}
                        key={`${event.type}-${event.tool}-${index}`}
                    />
                ))}

                {currentState === "idle" && !report && (
                    <>
                        <p><span className="term-ready">[READY]</span> Waiting for a website to test...</p>
                        <p className="term-muted">Enter a domain above to begin.</p>
                    </>
                )}

                {currentState === "error" && !report && (
                    <>
                        <p><span className="term-error">[ERROR]</span> Investigation stopped.</p>
                        <p className="term-muted">Review the reported error.</p>
                    </>
                )}

                {report && (
                    <>
                        <p><span className="term-info">[INFO]</span> Target: {report.target.url}</p>
                        {report.agent && (
                            <>
                                <p><span className="term-return">[AGENT]</span> Model: {report.agent.model}</p>
                                <p><span className="term-return">[CHECKS]</span> {report.agent.checks_used} tools used</p>
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
                        {checks.map((result, index) => (
                            <ToolResult
                                index={index}
                                key={`${result.key}-${index}`}
                                result={result}
                            />
                        ))}
                        <p className="terminal-done"><span className="term-info">[DONE]</span> Finished in {report.duration_ms} ms · {report.status.toUpperCase()}</p>
                    </>
                )}
            </Panel.Content>
        </Panel>
    );
}
