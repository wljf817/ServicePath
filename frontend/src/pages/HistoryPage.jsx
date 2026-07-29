import {Button, Card, Spinner} from "@heroui/react";
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

    return (
        <>
            <section className="page-heading">
                <div>
                    <span className="hero-pill"><HistoryIcon size={15} /> Saved reports</span>
                    <h1>Diagnostic history</h1>
                    <p>Review previous tests, compare outcomes, and reopen full raw results.</p>
                </div>
                <Button onPress={() => navigate("/")} variant="primary">
                    New diagnosis <ArrowIcon size={16} />
                </Button>
            </section>

            <Card className="history-panel" variant="secondary">
                <Card.Header className="history-header">
                    <div>
                        <span className="section-kicker">RECENT ACTIVITY</span>
                        <Card.Title>Reports</Card.Title>
                    </div>
                    {reports && <span className="record-count">{reports.length} saved</span>}
                </Card.Header>
                <Card.Content className="history-content">
                    {!reports && !error && <div className="inline-loading"><Spinner /><span>Loading history...</span></div>}
                    {error && <p className="form-error">{error}</p>}
                    {reports?.length === 0 && (
                        <div className="empty-state">
                            <HistoryIcon size={30} />
                            <h2>No reports yet</h2>
                            <p>Run your first diagnosis to create a saved report.</p>
                        </div>
                    )}
                    {reports?.map((report) => (
                        <button
                            className="history-row"
                            key={report.id}
                            onClick={() => navigate(`/reports/${report.id}`)}
                            type="button"
                        >
                            <div className="report-number">#{report.id}</div>
                            <div className="history-target">
                                <strong>{report.target}</strong>
                                <span>{formatDate(report.created_at)}</span>
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
