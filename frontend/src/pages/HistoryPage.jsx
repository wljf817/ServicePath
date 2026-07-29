import {Button, Card} from "@heroui/react";
import {useEffect, useState} from "react";

import {getHistory} from "../api";
import {ArrowIcon, HistoryIcon} from "../components/Icons";
import StatusBadge from "../components/StatusBadge";

function formatDate(value) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

export default function HistoryPage({navigate}) {
    const [reports, setReports] = useState(null);
    const [error, setError] = useState("");

    useEffect(() => {
        getHistory()
            .then((data) => setReports(data.reports))
            .catch((requestError) => setError(requestError.message));
    }, []);

    const issueCount = reports?.filter((report) => report.status !== "passed").length || 0;

    return (
        <>
            <section className="page-heading">
                <div>
                    <span className="hero-pill"><HistoryIcon size={15} /> Saved reports</span>
                    <h1>Diagnostic history</h1>
                    <p>Every completed trace stays available with its raw returns and analysis.</p>
                </div>
                <Button className="page-action-button" onPress={() => navigate("/")} variant="primary">
                    New diagnosis <ArrowIcon size={16} />
                </Button>
            </section>

            {reports && (
                <section className="history-summary" aria-label="History summary">
                    <div><span>Total reports</span><strong>{reports.length}</strong></div>
                    <div><span>Needs attention</span><strong>{issueCount}</strong></div>
                    <div><span>Latest report</span><strong>{reports[0] ? formatDate(reports[0].created_at) : "No activity"}</strong></div>
                </section>
            )}

            <Card className="history-panel" variant="secondary">
                <Card.Header className="history-header">
                    <div>
                        <span className="section-kicker">RECENT ACTIVITY</span>
                        <Card.Title>Reports</Card.Title>
                    </div>
                    {reports && <span className="record-count">{reports.length} saved</span>}
                </Card.Header>
                <Card.Content className="history-content">
                    {!reports && !error && (
                        <div className="history-skeleton" aria-label="Loading history">
                            {[0, 1, 2, 3].map((item) => <span key={item} />)}
                        </div>
                    )}
                    {error && <p className="form-error" role="alert">{error}</p>}
                    {reports?.length === 0 && (
                        <div className="empty-state">
                            <HistoryIcon size={30} />
                            <h2>No reports yet</h2>
                            <p>Run your first diagnosis to create a saved report.</p>
                        </div>
                    )}
                    {reports?.length > 0 && (
                        <div className="history-table-head" aria-hidden="true">
                            <span>Report</span><span>Target</span><span>Mode</span><span>Result</span><span />
                        </div>
                    )}
                    {reports?.map((report) => (
                        <button
                            className={`history-row history-row-${report.status}`}
                            key={report.id}
                            onClick={() => navigate(`/reports/${report.id}`)}
                            type="button"
                        >
                            <div className="report-number">#{report.id}</div>
                            <div className="history-target">
                                <strong>{report.target}</strong>
                                <span>
                                    {formatDate(report.created_at)}
                                    {report.first_problem && ` · First issue: ${report.first_problem.toUpperCase()}`}
                                </span>
                            </div>
                            <span className="mode-label">{report.mode}</span>
                            <StatusBadge status={report.status} />
                            <ArrowIcon className="history-arrow" size={17} />
                        </button>
                    ))}
                </Card.Content>
            </Card>
        </>
    );
}
