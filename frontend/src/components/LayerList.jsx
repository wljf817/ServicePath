import {detailLines, DIAGNOSTIC_TOOLS, reportLayers, toolNumber} from "../domain/diagnostics";
import {ChevronIcon, ClockIcon} from "./Icons";
import StatusBadge from "./StatusBadge";
import Panel from "./ui/Panel";

export default function LayerList({report}) {
    const layers = report
        ? reportLayers(report)
        : DIAGNOSTIC_TOOLS.map((layer) => ({
            ...layer,
            status: "waiting",
            summary: "Available to the diagnostic agent",
            duration_ms: 0,
        }));
    const firstIssueIndex = layers.findIndex((layer) => (
        layer.status === "warning" || layer.status === "error"
    ));

    return (
        <Panel className="layers-panel">
            <Panel.Header className="panel-header">
                <div>
                    <span className="section-kicker">ADAPTIVE TOOL SELECTION</span>
                    <Panel.Title className="panel-title">Collected evidence</Panel.Title>
                </div>
            </Panel.Header>
            <Panel.Content className="layer-stack">
                {layers.map((layer, index) => {
                    const details = detailLines(layer.details);
                    return (
                        <div
                            className={`layer-block layer-block-${layer.status}`}
                            key={layer.key}
                            style={{"--motion-index": index}}
                        >
                            <span className="layer-connector" aria-hidden="true" />
                            <div className="layer-row">
                                <div className="layer-index">
                                    {toolNumber(layer.key)}
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
                                <details className="layer-details" defaultOpen={index === firstIssueIndex}>
                                    <summary>
                                        <span>{details.length} returned fields</span>
                                        <ChevronIcon size={15} />
                                    </summary>
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
                                </details>
                            )}
                        </div>
                    );
                })}
            </Panel.Content>
        </Panel>
    );
}
