import {useCallback, useEffect, useState} from "react";

import {getHistory} from "../api";
import AppLink from "../components/AppLink";
import {ArrowIcon, HistoryIcon} from "../components/Icons";
import StatusBadge from "../components/StatusBadge";
import Panel from "../components/ui/Panel";
import {formatDate} from "../domain/diagnostics";
import useAbortableTask from "../hooks/useAbortableTask";

export default function HistoryPage({navigate}) {
    const [reports, setReports] = useState(null);
    const [error, setError] = useState("");
    const {run: runHistoryRequest} = useAbortableTask();

    const loadHistory = useCallback(async () => {
        setReports(null);
        setError("");

        try {
            const result = await runHistoryRequest((signal) => getHistory({signal}));
            if (result.completed) {
                setReports(result.value.reports);
            }
        } catch (requestError) {
            setError(requestError.message);
        }
    }, [runHistoryRequest]);

    useEffect(() => {
        loadHistory();
    }, [loadHistory]);

    const issueCount = reports?.filter((report) => report.status !== "passed").length || 0;

    return (
        <>
            <section className="page-heading">
                <div>
                    <span className="hero-pill"><HistoryIcon size={15} /> Saved reports</span>
                    <h1>Diagnostic history</h1>
                    <p>Every investigation keeps its agent conclusion and supporting tool evidence.</p>
                </div>
                <AppLink className="page-action-button" href="/" navigate={navigate}>
                    New diagnosis <ArrowIcon size={16} />
                </AppLink>
            </section>

            {reports && (
                <section className="history-summary" aria-label="History summary">
                    <div><span>Total reports</span><strong>{reports.length}</strong></div>
                    <div><span>Needs attention</span><strong>{issueCount}</strong></div>
                    <div><span>Latest report</span><strong>{reports[0] ? formatDate(reports[0].created_at) : "No activity"}</strong></div>
                </section>
            )}

            <Panel className="history-panel">
                <Panel.Header className="history-header">
                    <div>
                        <span className="section-kicker">RECENT ACTIVITY</span>
                        <Panel.Title>Reports</Panel.Title>
                    </div>
                    {reports && <span className="record-count">{reports.length} saved</span>}
                </Panel.Header>
                <Panel.Content className="history-content">
                    {!reports && !error && (
                        <>
                            <p aria-atomic="true" className="sr-only" role="status">
                                Loading history...
                            </p>
                            <div aria-hidden="true" className="history-skeleton">
                                {[0, 1, 2, 3].map((item) => <span key={item} />)}
                            </div>
                        </>
                    )}
                    {error && (
                        <div className="form-error">
                            <span role="alert">{error}</span>
                            <button className="inline-action" onClick={loadHistory} type="button">
                                Try again
                            </button>
                        </div>
                    )}
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
                        <AppLink
                            className={`history-row history-row-${report.status}`}
                            href={`/reports/${report.id}`}
                            key={report.id}
                            navigate={navigate}
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
                        </AppLink>
                    ))}
                </Panel.Content>
            </Panel>
        </>
    );
}
