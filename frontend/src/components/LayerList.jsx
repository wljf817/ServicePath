import {Card} from "@heroui/react";

import {ClockIcon} from "./Icons";
import StatusBadge from "./StatusBadge";

const waitingLayers = ["Client Network", "DNS", "TCP", "TLS", "HTTP"];

export default function LayerList({report}) {
    const layers = report?.layers || waitingLayers.map((name, index) => ({
        key: String(index),
        name,
        status: "waiting",
        summary: "Waiting to run",
        duration_ms: 0,
    }));

    return (
        <Card className="layers-panel" variant="secondary">
            <Card.Header className="panel-header">
                <div>
                    <span className="section-kicker">FIVE LAYERS</span>
                    <Card.Title className="panel-title">Path overview</Card.Title>
                </div>
            </Card.Header>
            <Card.Content className="layer-stack">
                {layers.map((layer, index) => (
                    <div className="layer-row" key={layer.key}>
                        <div className="layer-index">{String(index + 1).padStart(2, "0")}</div>
                        <div className="layer-copy">
                            <div>
                                <strong>{layer.name}</strong>
                                {layer.duration_ms > 0 && <span><ClockIcon size={13} /> {layer.duration_ms} ms</span>}
                            </div>
                            <p>{layer.summary}</p>
                        </div>
                        <StatusBadge status={layer.status} />
                    </div>
                ))}
            </Card.Content>
        </Card>
    );
}
