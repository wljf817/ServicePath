import {Card} from "@heroui/react";

import {ClockIcon} from "./Icons";
import StatusBadge from "./StatusBadge";

const waitingLayers = [
    {key: "client", name: "Client Network"},
    {key: "dns", name: "DNS"},
    {key: "traceroute", name: "Traceroute"},
    {key: "tcp", name: "TCP"},
    {key: "tls", name: "TLS"},
    {key: "http", name: "HTTP"},
];

const layerNumbers = {
    client: "01",
    dns: "02",
    traceroute: "TR",
    tcp: "03",
    tls: "04",
    http: "05",
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

export default function LayerList({report}) {
    const layers = report
        ? report.layers.flatMap((layer) => (
            layer.key === "dns" && report.traceroute
                ? [layer, report.traceroute]
                : [layer]
        ))
        : waitingLayers.map((layer) => ({
            ...layer,
            status: "waiting",
            summary: "Waiting to run",
            duration_ms: 0,
        }));

    return (
        <Card className="layers-panel" variant="secondary">
            <Card.Header className="panel-header">
                <div>
                    <span className="section-kicker">FIVE LAYERS + ROUTE TRACE</span>
                    <Card.Title className="panel-title">Path overview</Card.Title>
                </div>
            </Card.Header>
            <Card.Content className="layer-stack">
                {layers.map((layer, index) => {
                    const details = detailLines(layer.details);
                    return (
                        <div className={`layer-block layer-block-${layer.status}`} key={layer.key}>
                            <div className="layer-row">
                                <div className="layer-index">
                                    {layerNumbers[layer.key] || String(index + 1).padStart(2, "0")}
                                </div>
                                <div className="layer-copy">
                                    <div>
                                        <strong>{layer.name}</strong>
                                        {layer.duration_ms > 0 && (
                                            <span>
                                                <ClockIcon size={13} /> {layer.duration_ms} ms
                                            </span>
                                        )}
                                    </div>
                                    <p>{layer.summary}</p>
                                </div>
                                <StatusBadge status={layer.status} />
                            </div>
                            {details.length > 0 && (
                                <div className="layer-return-list">
                                    {details.map((detail) => (
                                        <div className="layer-return" key={detail.label}>
                                            <span>{detail.label}</span>
                                            <code className={detail.display.includes("\n") ? "layer-multiline" : ""}>
                                                {detail.display}
                                            </code>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </Card.Content>
        </Card>
    );
}
