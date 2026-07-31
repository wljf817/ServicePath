import {safeText, safeTextList} from "../domain/diagnostics";
import StatusBadge from "./StatusBadge";
import Panel from "./ui/Panel";

function AnalysisList({empty, items}) {
    const safeItems = safeTextList(items);
    if (!safeItems.length) {
        return <p className="empty-copy">{empty}</p>;
    }

    return (
        <ul className="analysis-list">
            {safeItems.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
        </ul>
    );
}

function AnalysisHeader({kicker, mark, title}) {
    return (
        <Panel.Header className="analysis-header">
            <span className="ai-mark">{mark}</span>
            <div>
                <span className="section-kicker">{kicker}</span>
                <Panel.Title>{safeText(title, "Saved analysis")}</Panel.Title>
            </div>
        </Panel.Header>
    );
}

function StructuredAnalysis({analysis}) {
    const isComparison = analysis.source === "comparison";
    const model = safeText(analysis.model);
    const confidence = safeText(analysis.confidence);
    const failureStage = safeText(analysis.failure_stage);

    return (
        <Panel className="analysis-panel">
            <AnalysisHeader
                kicker={isComparison ? "COMPARISON CONCLUSION" : "AGENT CONCLUSION"}
                mark={isComparison ? "CMP" : "AI"}
                title={analysis.headline}
            />
            <Panel.Content className="analysis-content">
                <div className="analysis-meta">
                    {model && <span>Model · {model}</span>}
                    {analysis.completion === "fallback" && <span>Partial conclusion</span>}
                    {confidence && <span>Confidence · {confidence}</span>}
                    {failureStage && <span>Observed break · {failureStage}</span>}
                </div>
                <div className="analysis-text">
                    {safeText(analysis.text, "No explanation was saved.")}
                </div>
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
            </Panel.Content>
        </Panel>
    );
}

function RulesAnalysis({analysis}) {
    return (
        <Panel className="analysis-panel">
            <AnalysisHeader kicker="SAVED RULE SUMMARY" mark="RULE" title={analysis.title} />
            <Panel.Content className="analysis-content">
                <div className="analysis-text">
                    {safeText(analysis.explanation, "No explanation was saved.")}
                </div>
                <div className="analysis-grid analysis-grid-two">
                    <section>
                        <h3>Possible causes</h3>
                        <AnalysisList empty="No likely cause was listed." items={analysis.causes} />
                    </section>
                    <section>
                        <h3>Next actions</h3>
                        <AnalysisList empty="No further action was listed." items={analysis.actions} />
                    </section>
                </div>
            </Panel.Content>
        </Panel>
    );
}

function OpenAIAnalysis({analysis}) {
    const model = safeText(analysis.model);

    return (
        <Panel className="analysis-panel">
            <AnalysisHeader
                kicker="AI ANALYSIS"
                mark="AI"
                title="AI explanation and recommended actions"
            />
            <Panel.Content className="analysis-content">
                {model && <div className="analysis-meta"><span>Model · {model}</span></div>}
                <div className="analysis-text">
                    {safeText(analysis.text, "No AI explanation was saved.")}
                </div>
            </Panel.Content>
        </Panel>
    );
}

function safeIssues(value) {
    if (!Array.isArray(value)) {
        return [];
    }

    return value.flatMap((issue) => {
        if (!issue || typeof issue !== "object" || Array.isArray(issue)) {
            return [];
        }
        const suppliedStatus = safeText(issue.status).toLowerCase();
        return [{
            layer: safeText(issue.layer, "Unknown check"),
            location: safeText(issue.location),
            status: ["warning", "error"].includes(suppliedStatus) ? suppliedStatus : "warning",
            summary: safeText(issue.summary, "No issue details were saved."),
        }];
    });
}

function LegacyStatusAnalysis({analysis}) {
    const source = safeText(analysis.source);
    const issues = safeIssues(analysis.issues);
    const note = source === "not_configured"
        ? "This report was created before agent diagnostics were configured."
        : source === "unavailable"
            ? "The analysis service was unavailable when this report was created."
            : "This saved report uses a legacy analysis format.";

    return (
        <Panel className="analysis-panel">
            <AnalysisHeader
                kicker="SAVED ANALYSIS STATUS"
                mark="OLD"
                title={safeText(analysis.message, "Analysis was unavailable")}
            />
            <Panel.Content className="analysis-content">
                <p className="analysis-note">{note}</p>
                <h3>Detected warnings and errors</h3>
                {issues.length ? (
                    <div className="issue-stack">
                        {issues.map((issue, index) => (
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
            </Panel.Content>
        </Panel>
    );
}

export default function AnalysisPanel({analysis}) {
    // Keep old saved reports readable while new reports use the structured schema.
    if (!analysis || typeof analysis !== "object" || Array.isArray(analysis)) {
        return null;
    }
    if (analysis.source === "agent" || analysis.source === "comparison") {
        return <StructuredAnalysis analysis={analysis} />;
    }
    if (analysis.source === "rules") {
        return <RulesAnalysis analysis={analysis} />;
    }
    if (analysis.source === "openai") {
        return <OpenAIAnalysis analysis={analysis} />;
    }
    return <LegacyStatusAnalysis analysis={analysis} />;
}
