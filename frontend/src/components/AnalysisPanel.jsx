import {Card} from "@heroui/react";

import StatusBadge from "./StatusBadge";

function AnalysisList({empty, items}) {
    if (!items?.length) {
        return <p className="empty-copy">{empty}</p>;
    }

    return (
        <ul className="analysis-list">
            {items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
        </ul>
    );
}

export default function AnalysisPanel({analysis}) {
    if (!analysis) {
        return null;
    }

    const isStructured = analysis.source === "agent" || analysis.source === "comparison";
    const isOpenAI = analysis.source === "openai";

    if (isStructured) {
        const isComparison = analysis.source === "comparison";
        return (
            <Card className="analysis-panel" variant="secondary">
                <Card.Header className="analysis-header">
                    <span className="ai-mark">{isComparison ? "CMP" : "AI"}</span>
                    <div>
                        <span className="section-kicker">
                            {isComparison ? "COMPARISON CONCLUSION" : "AGENT CONCLUSION"}
                        </span>
                        <Card.Title>{analysis.headline}</Card.Title>
                    </div>
                </Card.Header>
                <Card.Content className="analysis-content">
                    <div className="analysis-meta">
                        {analysis.model && <span>Model · {analysis.model}</span>}
                        {analysis.completion === "fallback" && <span>Partial conclusion</span>}
                        <span>Confidence · {analysis.confidence}</span>
                        {analysis.failure_stage && <span>Observed break · {analysis.failure_stage}</span>}
                    </div>
                    <div className="analysis-text">{analysis.text}</div>
                    <div className="analysis-grid">
                        <section>
                            <h3>Evidence used</h3>
                            <AnalysisList empty="No supporting evidence was listed." items={analysis.evidence} />
                        </section>
                        <section>
                            <h3>Likely causes</h3>
                            <AnalysisList empty="No likely cause was established." items={analysis.causes} />
                        </section>
                        <section>
                            <h3>Next actions</h3>
                            <AnalysisList empty="No further action is recommended." items={analysis.actions} />
                        </section>
                    </div>
                </Card.Content>
            </Card>
        );
    }

    return (
        <Card className="analysis-panel" variant="secondary">
            <Card.Header className="analysis-header">
                <span className="ai-mark">AI</span>
                <div>
                    <span className="section-kicker">ANALYSIS</span>
                    <Card.Title>{isOpenAI ? "AI explanation and next actions" : analysis.message}</Card.Title>
                </div>
            </Card.Header>
            <Card.Content className="analysis-content">
                {isOpenAI ? (
                    <>
                        <p className="analysis-model">Generated with {analysis.model}</p>
                        <div className="analysis-text">{analysis.text}</div>
                    </>
                ) : (
                    <>
                        <p className="analysis-note">
                            {analysis.source === "not_configured"
                                ? "Add an Agent API key in Settings to enable the diagnostic agent."
                                : "Check the API configuration and run another diagnosis."}
                        </p>
                        <h3>Detected warnings and errors</h3>
                        {analysis.issues?.length ? (
                            <div className="issue-stack">
                                {analysis.issues.map((issue, index) => (
                                    <div className="issue-row" key={`${issue.layer}-${index}`}>
                                        <StatusBadge status={issue.status} />
                                        <div>
                                            <strong>{issue.location ? `${issue.location} · ` : ""}{issue.layer}</strong>
                                            <p>{issue.summary}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : <p className="empty-copy">No warnings or errors were detected.</p>}
                    </>
                )}
            </Card.Content>
        </Card>
    );
}
