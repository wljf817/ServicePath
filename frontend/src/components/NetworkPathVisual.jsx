import {DIAGNOSTIC_TOOLS, runtimeState} from "../domain/diagnostics";

export default function NetworkPathVisual({loading = false, state}) {
    const currentState = runtimeState(state, loading);
    const running = currentState === "running";
    const visualClass = running
        ? "network-path-visual network-path-visual-running"
        : "network-path-visual";
    const stateLabel = running
        ? "Agent investigating"
        : (currentState === "error" ? "Investigation stopped" : "Tools ready");

    return (
        <section
            aria-busy={running}
            aria-labelledby="network-path-title"
            className={visualClass}
            data-state={currentState}
        >
            <div className="network-path-heading">
                <div>
                    <span className="network-path-kicker">AVAILABLE EVIDENCE</span>
                    <h2 id="network-path-title">The agent chooses what to inspect</h2>
                </div>
                <span className="network-path-state">
                    <i aria-hidden="true" />
                    {stateLabel}
                </span>
            </div>

            <div className="network-path-canvas">
                <div className="network-path-line" aria-hidden="true">
                    <span className="network-path-packet" />
                </div>

                <ol className="network-path-list" aria-label="Diagnostic stages">
                    {DIAGNOSTIC_TOOLS.map((stage, index) => (
                        <li
                            className="network-path-stage"
                            key={stage.key}
                            style={{"--motion-index": index}}
                        >
                            <span className="network-path-node" aria-hidden="true">
                                <span>{String(index + 1).padStart(2, "0")}</span>
                            </span>
                            <strong>{stage.pathName}</strong>
                            <small>{stage.description}</small>
                        </li>
                    ))}
                </ol>
            </div>
        </section>
    );
}
