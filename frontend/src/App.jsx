import {useCallback, useEffect, useRef, useState} from "react";

import {getAppSettings, startDiagnosis} from "./api";
import Shell from "./components/Shell";
import useAbortableTask from "./hooks/useAbortableTask";
import DashboardPage from "./pages/DashboardPage";
import HistoryPage from "./pages/HistoryPage";
import ReportPage from "./pages/ReportPage";
import SettingsPage from "./pages/SettingsPage";
import {
    getBrowserSettings,
    saveBrowserSettings,
    saveReport,
} from "./storage";

function currentPath() {
    return window.location.pathname;
}

export default function App() {
    const [path, setPath] = useState(currentPath());
    const [navigationCount, setNavigationCount] = useState(0);
    const reduceMotionRef = useRef(
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
    const [settingsState, setSettingsState] = useState({
        data: null,
        error: "",
        status: "loading",
    });
    const [settingsSaveState, setSettingsSaveState] = useState({
        error: "",
        status: "idle",
    });
    const [diagnosisState, setDiagnosisState] = useState({
        error: "",
        events: [],
        location: "local",
        reportUrl: "",
        status: "idle",
        target: "",
    });
    const diagnosisRequestRef = useRef(null);
    const {run: runDiagnosisRequest} = useAbortableTask();

    useEffect(() => {
        let active = true;
        Promise.all([getAppSettings(), getBrowserSettings()]).then(
            ([server, browser]) => {
                if (active) {
                    setSettingsState({
                        data: {
                            ...browser,
                            presets: server.presets,
                            server_presets: server.server_presets,
                        },
                        error: "",
                        status: "ready",
                    });
                    setDiagnosisState((current) => ({
                        ...current,
                        location: browser.location,
                    }));
                }
            },
            (error) => active && setSettingsState({
                data: null,
                error: error.message,
                status: "error",
            }),
        );
        return () => { active = false; };
    }, []);

    useEffect(() => {
        function updatePath() {
            setPath(currentPath());
            setNavigationCount((count) => count + 1);
        }
        window.addEventListener("popstate", updatePath);
        return () => window.removeEventListener("popstate", updatePath);
    }, []);

    useEffect(() => {
        const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
        const update = (event) => { reduceMotionRef.current = event.matches; };
        motionQuery.addEventListener("change", update);
        return () => motionQuery.removeEventListener("change", update);
    }, []);

    useEffect(() => {
        const titles = {
            "/": "Diagnostics · ServicePath",
            "/history": "History · ServicePath",
            "/settings": "Settings · ServicePath",
        };
        document.title = path.startsWith("/reports/")
            ? "Diagnostic report · ServicePath"
            : titles[path] || "ServicePath";
        if (navigationCount > 0) {
            const frame = window.requestAnimationFrame(() => {
                document.getElementById("main-content")?.focus({preventScroll: true});
            });
            return () => window.cancelAnimationFrame(frame);
        }
        return undefined;
    }, [navigationCount, path]);

    const navigate = useCallback((nextPath) => {
        window.history.pushState({}, "", nextPath);
        setPath(nextPath);
        setNavigationCount((count) => count + 1);
        window.scrollTo({
            top: 0,
            behavior: reduceMotionRef.current ? "auto" : "smooth",
        });
    }, []);

    const saveSettings = useCallback(async (settings) => {
        if (diagnosisRequestRef.current) {
            return null;
        }
        setSettingsSaveState({error: "", status: "saving"});
        try {
            const saved = await saveBrowserSettings(settings);
            setSettingsState((current) => ({
                data: {
                    ...saved,
                    presets: current.data.presets,
                    server_presets: current.data.server_presets,
                },
                error: "",
                status: "ready",
            }));
            setSettingsSaveState({error: "", status: "success"});
            return saved;
        } catch (error) {
            setSettingsSaveState({error: error.message, status: "error"});
            throw error;
        }
    }, []);

    const clearSettingsSaveFeedback = useCallback(() => {
        setSettingsSaveState((current) => (
            current.status === "success"
                ? {error: "", status: "idle"}
                : current
        ));
    }, []);

    const runDiagnosis = useCallback((target, location) => {
        if (diagnosisRequestRef.current || !settingsState.data) {
            return diagnosisRequestRef.current;
        }
        const runSettings = {...settingsState.data, location};
        setSettingsState((current) => ({
            ...current,
            data: {...current.data, location},
        }));
        setSettingsSaveState({error: "", status: "idle"});
        setDiagnosisState({
            error: "",
            events: [],
            location,
            reportUrl: "",
            status: "running",
            target,
        });

        let request;
        request = (async () => {
            try {
                await saveBrowserSettings(runSettings);
                const result = await runDiagnosisRequest((signal) => (
                    startDiagnosis(target, runSettings, {
                        signal,
                        onEvent: (event) => {
                            if (event.type !== "run_started") {
                                setDiagnosisState((current) => ({
                                    ...current,
                                    events: [...current.events, event],
                                }));
                            }
                        },
                    })
                ));
                if (!result.completed) {
                    return null;
                }
                const report = await saveReport(result.value);
                const reportUrl = `/reports/${report.id}`;
                if (currentPath() === "/") {
                    setDiagnosisState((current) => ({...current, status: "idle"}));
                    navigate(reportUrl);
                } else {
                    setDiagnosisState((current) => ({
                        ...current,
                        reportUrl,
                        status: "complete",
                    }));
                }
                return report;
            } catch (error) {
                setDiagnosisState((current) => ({
                    ...current,
                    error: error.message,
                    status: "error",
                }));
                return null;
            } finally {
                if (diagnosisRequestRef.current === request) {
                    diagnosisRequestRef.current = null;
                }
            }
        })();
        diagnosisRequestRef.current = request;
        return request;
    }, [navigate, runDiagnosisRequest, settingsState.data]);

    const clearDiagnosisFeedback = useCallback(() => {
        setDiagnosisState((current) => (
            current.status === "error"
                ? {...current, error: "", events: [], status: "idle"}
                : current
        ));
    }, []);

    const reportMatch = path.match(/^\/reports\/(\d+)$/);
    const shellActivity = diagnosisState.status === "idle"
        ? ({
            error: {label: "Settings save failed", status: "error"},
            saving: {label: "Saving browser settings", status: "running"},
            success: {label: "Browser settings saved", status: "complete"},
        }[settingsSaveState.status] || diagnosisState)
        : diagnosisState;
    let page;

    if (reportMatch) {
        page = <ReportPage reportId={reportMatch[1]} navigate={navigate} />;
    } else if (path === "/history") {
        page = <HistoryPage navigate={navigate} />;
    } else if (path === "/settings") {
        page = (
            <SettingsPage
                appSettings={settingsState.data}
                diagnosisRunning={diagnosisState.status === "running"}
                error={settingsState.error}
                onChange={clearSettingsSaveFeedback}
                onSave={saveSettings}
                saveError={settingsSaveState.error}
                saveStatus={settingsSaveState.status}
                status={settingsState.status}
            />
        );
    } else {
        page = (
            <DashboardPage
                appSettings={settingsState.data}
                diagnosis={diagnosisState}
                onChange={clearDiagnosisFeedback}
                onStartDiagnosis={runDiagnosis}
                settingsError={settingsState.error}
                settingsSaveError={settingsSaveState.error}
                settingsSaveStatus={settingsSaveState.status}
                settingsStatus={settingsState.status}
            />
        );
    }

    return (
        <Shell activity={shellActivity} path={path} navigate={navigate}>
            <div className="page-transition" key={path}>{page}</div>
        </Shell>
    );
}
