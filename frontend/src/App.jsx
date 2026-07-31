import {useCallback, useEffect, useRef, useState} from "react";

import {getAppSettings, saveAppSettings, startDiagnosis} from "./api";
import DashboardPage from "./pages/DashboardPage";
import HistoryPage from "./pages/HistoryPage";
import ReportPage from "./pages/ReportPage";
import SettingsPage from "./pages/SettingsPage";
import Shell from "./components/Shell";
import useAbortableTask from "./hooks/useAbortableTask";

function currentPath() {
    return window.location.pathname;
}

function settingsDraftFrom(appSettings) {
    return {
        instance_role: appSettings.settings.instance_role,
        new_settings_password: "",
        openai_api_key: "",
        openai_api_mode: appSettings.openai_api_mode,
        openai_base_url: appSettings.openai_base_url,
        openai_model: appSettings.openai_model,
        servicepath_api_token: "",
        settings_password: "",
    };
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
    const [settingsDraft, setSettingsDraft] = useState(null);
    const [diagnosisState, setDiagnosisState] = useState({
        error: "",
        events: [],
        mode: "server",
        reportUrl: "",
        status: "idle",
        target: "",
    });
    const settingsSaveRequestRef = useRef(null);
    const diagnosisRequestRef = useRef(null);
    const {
        abort: abortSettingsRequest,
        run: runSettingsRequest,
    } = useAbortableTask();
    const {run: runSaveSettingsRequest} = useAbortableTask();
    const {run: runDiagnosisRequest} = useAbortableTask();

    const loadAppSettings = useCallback(async () => {
        setSettingsState({data: null, error: "", status: "loading"});
        try {
            const result = await runSettingsRequest((signal) => getAppSettings({signal}));
            if (result.completed) {
                setSettingsState({data: result.value, error: "", status: "ready"});
                return true;
            }
            return false;
        } catch (error) {
            setSettingsState({
                data: null,
                error: error.message,
                status: "error",
            });
            return false;
        }
    }, [runSettingsRequest]);

    useEffect(() => {
        loadAppSettings();
    }, [loadAppSettings]);

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
        const updateMotionPreference = (event) => {
            reduceMotionRef.current = event.matches;
        };

        reduceMotionRef.current = motionQuery.matches;
        motionQuery.addEventListener("change", updateMotionPreference);
        return () => motionQuery.removeEventListener("change", updateMotionPreference);
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

        let focusFrame = null;
        if (navigationCount > 0) {
            focusFrame = window.requestAnimationFrame(() => {
                document.getElementById("main-content")?.focus({preventScroll: true});
            });
        }

        return () => {
            if (focusFrame !== null) {
                window.cancelAnimationFrame(focusFrame);
            }
        };
    }, [navigationCount, path]);

    useEffect(() => {
        if (
            diagnosisState.status === "complete"
            && diagnosisState.reportUrl === path
        ) {
            setDiagnosisState((current) => ({...current, status: "idle"}));
        }
    }, [diagnosisState.reportUrl, diagnosisState.status, path]);

    const navigate = useCallback((nextPath, options = {}) => {
        window.history.pushState({}, "", nextPath);
        setPath(nextPath);
        setNavigationCount((count) => count + 1);
        if (!options.preserveScroll) {
            window.scrollTo({
                top: 0,
                behavior: reduceMotionRef.current ? "auto" : "smooth",
            });
        }
    }, []);

    const handleSettingsSaved = useCallback((data) => {
        abortSettingsRequest();
        setSettingsState({data, error: "", status: "ready"});
    }, [abortSettingsRequest]);

    const saveSettings = useCallback((settings) => {
        // Keep one save authoritative across page navigation.
        if (settingsSaveRequestRef.current) {
            return settingsSaveRequestRef.current;
        }
        if (diagnosisRequestRef.current) {
            return Promise.resolve(null);
        }

        setDiagnosisState((current) => ({
            ...current,
            error: "",
            events: [],
            reportUrl: "",
            status: "idle",
        }));
        setSettingsDraft(settings);
        setSettingsSaveState({error: "", status: "saving"});
        let request;
        request = (async () => {
            try {
                const result = await runSaveSettingsRequest((signal) => (
                    saveAppSettings(settings, {signal})
                ));
                if (!result.completed) {
                    setSettingsSaveState({error: "", status: "idle"});
                    return null;
                }

                handleSettingsSaved(result.value);
                setSettingsDraft(null);
                setSettingsSaveState({error: "", status: "success"});
                return result.value;
            } catch (error) {
                setSettingsSaveState({
                    error: error.message,
                    status: "error",
                });
                throw error;
            } finally {
                if (settingsSaveRequestRef.current === request) {
                    settingsSaveRequestRef.current = null;
                }
            }
        })();
        settingsSaveRequestRef.current = request;
        return request;
    }, [handleSettingsSaved, runSaveSettingsRequest]);

    const clearSettingsSaveFeedback = useCallback(() => {
        setSettingsSaveState((current) => (
            current.status === "success"
                ? {error: "", status: "idle"}
                : current
        ));
    }, []);

    const updateSettingsDraft = useCallback((field, value) => {
        setSettingsDraft((current) => ({
            ...(current || settingsDraftFrom(settingsState.data)),
            [field]: value,
        }));
    }, [settingsState.data]);

    const runDiagnosis = useCallback((target, mode) => {
        // Keep diagnostics alive and visible when the user changes pages.
        if (diagnosisRequestRef.current) {
            return diagnosisRequestRef.current;
        }
        if (settingsSaveRequestRef.current) {
            return Promise.resolve(null);
        }

        setSettingsSaveState({error: "", status: "idle"});
        setDiagnosisState({
            error: "",
            events: [],
            mode,
            reportUrl: "",
            status: "running",
            target,
        });
        let request;
        request = (async () => {
            try {
                const result = await runDiagnosisRequest((signal) => (
                    startDiagnosis(target, mode, {
                        signal,
                        onEvent: (event) => {
                            if (event.type === "run_started") {
                                return;
                            }
                            setDiagnosisState((current) => ({
                                ...current,
                                events: [...current.events, event],
                            }));
                        },
                    })
                ));
                if (!result.completed) {
                    return null;
                }

                if (currentPath() === "/") {
                    setDiagnosisState((current) => ({...current, status: "idle"}));
                    navigate(result.value.report_url);
                } else {
                    setDiagnosisState((current) => ({
                        ...current,
                        reportUrl: result.value.report_url,
                        status: "complete",
                    }));
                }
                return result.value;
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
    }, [navigate, runDiagnosisRequest]);

    const clearDiagnosisFeedback = useCallback(() => {
        setDiagnosisState((current) => (
            current.status === "error"
                ? {...current, error: "", events: [], status: "idle"}
                : current
        ));
    }, []);

    const reportMatch = path.match(/^\/reports\/(\d+)$/);
    const settingsActivities = {
        error: {label: "Settings save failed", status: "error"},
        saving: {label: "Saving settings", status: "running"},
        success: {label: "Settings saved", status: "complete"},
    };
    const shellActivity = diagnosisState.status === "idle"
        ? (settingsActivities[settingsSaveState.status] || diagnosisState)
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
                error={settingsState.error}
                diagnosisRunning={diagnosisState.status === "running"}
                draft={settingsDraft}
                onChange={clearSettingsSaveFeedback}
                onDraftChange={updateSettingsDraft}
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
            <div className="page-transition" key={path}>
                {page}
            </div>
        </Shell>
    );
}
