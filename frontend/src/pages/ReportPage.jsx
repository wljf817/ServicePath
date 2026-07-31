import {useCallback, useEffect, useState} from "react";

import {getReport} from "../api";
import AnalysisPanel from "../components/AnalysisPanel";
import AppLink from "../components/AppLink";
import DiagnosticConsole from "../components/DiagnosticConsole";
import {ArrowIcon} from "../components/Icons";
import LayerList from "../components/LayerList";
import StatusBadge from "../components/StatusBadge";
import Panel from "../components/ui/Panel";
import Spinner from "../components/ui/Spinner";
import {formatDate} from "../domain/diagnostics";
import useAbortableTask from "../hooks/useAbortableTask";

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
        <Panel className="comparison-panel">
            <Panel.Header>
                <div>
                    <span className="section-kicker">SIDE BY SIDE</span>
                    <Panel.Title>Evidence comparison</Panel.Title>
                </div>
            </Panel.Header>
            <Panel.Content>
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
            </Panel.Content>
        </Panel>
    );
}

export default function ReportPage({reportId, navigate}) {
    const [report, setReport] = useState(null);
    const [error, setError] = useState("");
    const {run: runReportRequest} = useAbortableTask();

    const loadReport = useCallback(async () => {
        setReport(null);
        setError("");

        try {
            const result = await runReportRequest((signal) => getReport(reportId, {signal}));
            if (result.completed) {
                setReport(result.value);
            }
        } catch (requestError) {
            setError(requestError.message);
        }
    }, [reportId, runReportRequest]);

    useEffect(() => {
        loadReport();
    }, [loadReport]);

    if (error) {
        return (
            <Panel className="state-card">
                <Panel.Content>
                    <h1>Report unavailable</h1>
                    <p role="alert">{error}</p>
                    <button className="secondary-button" onClick={loadReport} type="button">
                        Try again
                    </button>
                    <AppLink className="secondary-button" href="/" navigate={navigate}>New diagnosis</AppLink>
                </Panel.Content>
            </Panel>
        );
    }

    if (!report) {
        return (
            <div aria-atomic="true" className="page-loading" role="status">
                <Spinner size="lg" />
                <p>Loading report...</p>
            </div>
        );
    }

    const compare = report.mode === "compare";

    return (
        <div className="report-flow">
            <section className={`report-hero report-${report.status}`}>
                <div className="report-hero-main">
                    <div>
                        <span className="section-kicker">DIAGNOSTIC REPORT · #{report.id}</span>
                        <h1>{compare ? report.comparison.title : report.analysis?.headline || report.target.hostname}</h1>
                        <p>{compare ? report.comparison.summary : report.target.url}</p>
                    </div>
                    <div className="report-actions">
                        <StatusBadge status={report.status} />
                        <AppLink className="secondary-button" href="/" navigate={navigate}>
                            New test <ArrowIcon size={15} />
                        </AppLink>
                    </div>
                </div>
                <div className="report-metrics" aria-label="Report summary">
                    <ReportMetric label="Duration" value={`${report.duration_ms} ms`} />
                    <ReportMetric label="Observed break" value={report.first_problem?.toUpperCase() || "None found"} />
                    <ReportMetric label="Run location" value={compare ? "Local + remote" : report.mode} />
                    <ReportMetric label="Completed" value={formatDate(report.created_at)} />
                </div>
            </section>

            <AnalysisPanel analysis={report.analysis} />

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

        </div>
    );
}
