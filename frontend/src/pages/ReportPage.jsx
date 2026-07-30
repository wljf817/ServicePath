import {Button, Card, Spinner} from "@heroui/react";
import {useEffect, useState} from "react";

import {getReport} from "../api";
import AnalysisPanel from "../components/AnalysisPanel";
import DiagnosticConsole from "../components/DiagnosticConsole";
import {ArrowIcon} from "../components/Icons";
import LayerList from "../components/LayerList";
import StatusBadge from "../components/StatusBadge";

function formatDate(value) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function ReportMetric({label, value}) {
    return (
        <div className="report-metric">
            <span>{label}</span>
            <strong>{value}</strong>
        </div>
    );
}

function CompareTable({report}) {
    return (
        <Card className="comparison-panel" variant="secondary">
            <Card.Header>
                <div>
                    <span className="section-kicker">SIDE BY SIDE</span>
                    <Card.Title>Evidence comparison</Card.Title>
                </div>
            </Card.Header>
            <Card.Content>
                <div className="comparison-table">
                    <div className="comparison-head"><span>Check</span><span>Local</span><span>Remote</span></div>
                    {report.comparison.layers.map((row) => (
                        <div className="comparison-row" key={row.key}>
                            <strong>{row.name}</strong>
                            <div><StatusBadge status={row.local.status} /><p>{row.local.summary}</p></div>
                            <div><StatusBadge status={row.remote.status} /><p>{row.remote.summary}</p></div>
                        </div>
                    ))}
                </div>
            </Card.Content>
        </Card>
    );
}

export default function ReportPage({reportId, navigate}) {
    const [report, setReport] = useState(null);
    const [error, setError] = useState("");

    useEffect(() => {
        setReport(null);
        setError("");
        getReport(reportId).then(setReport).catch((requestError) => setError(requestError.message));
    }, [reportId]);

    if (error) {
        return <Card className="state-card"><Card.Content><h1>Report unavailable</h1><p>{error}</p><Button onPress={() => navigate("/")}>New diagnosis</Button></Card.Content></Card>;
    }

    if (!report) {
        return <div className="page-loading"><Spinner size="lg" /><p>Loading report...</p></div>;
    }

    const compare = report.mode === "compare";

    return (
        <>
            <section className={`report-hero report-${report.status}`}>
                <div className="report-hero-main">
                    <div>
                        <span className="section-kicker">DIAGNOSTIC REPORT · #{report.id}</span>
                        <h1>{compare ? report.comparison.title : report.analysis?.headline || report.target.hostname}</h1>
                        <p>{compare ? report.comparison.summary : report.target.url}</p>
                    </div>
                    <div className="report-actions">
                        <StatusBadge status={report.status} />
                        <Button onPress={() => navigate("/")} size="sm" variant="secondary">
                            New test <ArrowIcon size={15} />
                        </Button>
                    </div>
                </div>
                <div className="report-metrics" aria-label="Report summary">
                    <ReportMetric label="Duration" value={`${report.duration_ms} ms`} />
                    <ReportMetric label="Observed break" value={report.first_problem?.toUpperCase() || "None found"} />
                    <ReportMetric label="Run location" value={compare ? "Local + remote" : report.mode} />
                    <ReportMetric label="Completed" value={formatDate(report.created_at)} />
                </div>
            </section>

            {compare ? (
                <>
                    <section className="compare-console-grid">
                        <DiagnosticConsole label="Local Agent Evidence" report={report.local_report} />
                        <DiagnosticConsole label="Remote Agent Evidence" report={report.remote_report} />
                    </section>
                    <CompareTable report={report} />
                </>
            ) : (
                <section className="dashboard-grid report-grid">
                    <DiagnosticConsole report={report} />
                    <LayerList report={report} />
                </section>
            )}

            <AnalysisPanel analysis={report.analysis} />
        </>
    );
}
