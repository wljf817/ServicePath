import Panel from "./ui/Panel";

function AnalysisList({empty, items}) {
    if (!items.length) {
        return <p className="empty-copy">{empty}</p>;
    }

    return (
        <ul className="analysis-list">
            {items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
        </ul>
    );
}

function AnalysisHeader({kicker, mark, title}) {
    return (
        <Panel.Header className="analysis-header">
            <span className="ai-mark">{mark}</span>
            <div>
                <span className="section-kicker">{kicker}</span>
                <Panel.Title>{title}</Panel.Title>
            </div>
        </Panel.Header>
    );
}

function StructuredAnalysis({analysis}) {
    const {model, confidence, failure_stage: failureStage} = analysis;

    return (
        <Panel className="analysis-panel">
            <AnalysisHeader
                kicker="AGENT CONCLUSION"
                mark="AI"
                title={analysis.headline}
            />
            <Panel.Content className="analysis-content">
                <div className="analysis-meta">
                    {model && <span>Model · {model}</span>}
                    {confidence && <span>Confidence · {confidence}</span>}
                    {failureStage && <span>Observed break · {failureStage}</span>}
                </div>
                <div className="analysis-text">
                    {analysis.text}
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

export default function AnalysisPanel({analysis}) {
    if (
        !analysis
        || typeof analysis !== "object"
        || Array.isArray(analysis)
        || analysis.source !== "agent"
    ) {
        throw new TypeError("Invalid report analysis.");
    }
    return <StructuredAnalysis analysis={analysis} />;
}
