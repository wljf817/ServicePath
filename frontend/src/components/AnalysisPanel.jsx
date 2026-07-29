import {Card} from "@heroui/react";

import StatusBadge from "./StatusBadge";

export default function AnalysisPanel({analysis}) {
    if (!analysis) {
        return null;
    }

    const isOpenAI = analysis.source === "openai";

    return (
        <Card className="analysis-panel" variant="secondary">
            <Card.Header>
                <span className="ai-mark">AI</span>
                <div>
                    <span className="section-kicker">ANALYSIS</span>
                    <Card.Title>{isOpenAI ? "AI explanation and next actions" : analysis.message}</Card.Title>
                </div>
            </Card.Header>
            <Card.Content>
                {isOpenAI ? (
                    <>
                        <p className="analysis-model">Generated with {analysis.model}</p>
                        <div className="analysis-text">{analysis.text}</div>
                    </>
                ) : (
                    <>
                        <p className="analysis-note">
                            {analysis.source === "not_configured"
                                ? "Add OPENAI_API_KEY to the server .env file to enable AI analysis."
                                : "Check the API configuration and run another diagnosis."}
                        </p>
                        <h3>Detected warnings and errors</h3>
                        {analysis.issues.length ? (
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
