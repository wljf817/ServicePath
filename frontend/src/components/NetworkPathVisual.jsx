const pathStages = [
    {name: "Device", description: "Client network"},
    {name: "DNS", description: "Name resolution"},
    {name: "Route", description: "Network path"},
    {name: "TCP", description: "Port connection"},
    {name: "TLS", description: "Secure handshake"},
    {name: "HTTP", description: "Application response"},
];

export default function NetworkPathVisual({loading = false}) {
    const visualClass = loading
        ? "network-path-visual network-path-visual-running"
        : "network-path-visual";

    return (
        <section className={visualClass} aria-labelledby="network-path-title">
            <div className="network-path-heading">
                <div>
                    <span className="network-path-kicker">AVAILABLE EVIDENCE</span>
                    <h2 id="network-path-title">The agent chooses what to inspect</h2>
                </div>
                <span className="network-path-state">
                    <i aria-hidden="true" />
                    {loading ? "Agent investigating" : "Tools ready"}
                </span>
            </div>

            <div className="network-path-canvas">
                <div className="network-path-line" aria-hidden="true">
                    <span className="network-path-packet" />
                </div>

                <ol className="network-path-list" aria-label="Diagnostic stages">
                    {pathStages.map((stage, index) => (
                        <li className="network-path-stage" key={stage.name}>
                            <span className="network-path-node" aria-hidden="true">
                                <span>{String(index + 1).padStart(2, "0")}</span>
                            </span>
                            <strong>{stage.name}</strong>
                            <small>{stage.description}</small>
                        </li>
                    ))}
                </ol>
            </div>
        </section>
    );
}
