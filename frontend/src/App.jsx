import {useEffect, useState} from "react";

import {getAppSettings} from "./api";
import DashboardPage from "./pages/DashboardPage";
import HistoryPage from "./pages/HistoryPage";
import ReportPage from "./pages/ReportPage";
import SettingsPage from "./pages/SettingsPage";
import Shell from "./components/Shell";

function currentPath() {
    return window.location.pathname;
}

export default function App() {
    const [path, setPath] = useState(currentPath());
    const [appSettings, setAppSettings] = useState(null);

    useEffect(() => {
        getAppSettings().then(setAppSettings).catch(() => setAppSettings(null));

        function updatePath() {
            setPath(currentPath());
        }

        window.addEventListener("popstate", updatePath);
        return () => window.removeEventListener("popstate", updatePath);
    }, []);

    function navigate(nextPath) {
        window.history.pushState({}, "", nextPath);
        setPath(nextPath);
        window.scrollTo({top: 0, behavior: "smooth"});
    }

    const reportMatch = path.match(/^\/reports\/(\d+)$/);
    let page;

    if (reportMatch) {
        page = <ReportPage reportId={reportMatch[1]} navigate={navigate} />;
    } else if (path === "/history") {
        page = <HistoryPage navigate={navigate} />;
    } else if (path === "/settings") {
        page = (
            <SettingsPage
                appSettings={appSettings}
                onSaved={setAppSettings}
            />
        );
    } else {
        page = <DashboardPage appSettings={appSettings} navigate={navigate} />;
    }

    return (
        <Shell path={path} navigate={navigate}>
            {page}
        </Shell>
    );
}
