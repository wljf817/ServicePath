import {useEffect, useState} from "react";

import {getReport} from "../storage";
import AnalysisPanel from "../components/AnalysisPanel";
import AppLink from "../components/AppLink";
import DiagnosticConsole from "../components/DiagnosticConsole";
import {ArrowIcon} from "../components/Icons";
import LayerList from "../components/LayerList";
import StatusBadge from "../components/StatusBadge";
import Panel from "../components/ui/Panel";
import Spinner from "../components/ui/Spinner";
import {formatDate} from "../domain/diagnostics";

function ReportMetric({label, value}) {
    return (
        <div className="report-metric">
            <span>{label}</span>
            <strong>{value}</strong>
        </div>
    );
}

export default function ReportPage({reportId, navigate}) {
    const [report, setReport] = useState(null);
    const [error, setError] = useState("");
    useEffect(() => {
        let active = true;
        getReport(reportId).then(
            (savedReport) => active && setReport(savedReport),
            (requestError) => active && setError(requestError.message),
        );
        return () => { active = false; };
    }, [reportId]);

    if (error) {
        return (
            <Panel className="state-card">
                <Panel.Content>
                    <h1>Report unavailable</h1>
                    <p role="alert">{error}</p>
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

    return (
        <div className="report-flow">
            <section className={`report-hero report-${report.status}`}>
                <div className="report-hero-main">
                    <div>
                        <span className="section-kicker">DIAGNOSTIC REPORT · #{report.id}</span>
                        <h1>{report.analysis.headline}</h1>
                        <p>{report.target.url}</p>
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
                    <ReportMetric label="Completed" value={formatDate(report.created_at)} />
                </div>
            </section>

            <AnalysisPanel analysis={report.analysis} />

            <section className="dashboard-grid report-grid">
                <DiagnosticConsole report={report} />
                <LayerList report={report} />
            </section>

        </div>
    );
}
