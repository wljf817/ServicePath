import {useEffect, useState} from "react";

import {getAppSettings} from "./api";
import DashboardPage from "./pages/DashboardPage";
import ReportPage from "./pages/ReportPage";
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

    return (
        <Shell path={path} navigate={navigate}>
            {reportMatch ? (
                <ReportPage reportId={reportMatch[1]} navigate={navigate} />
            ) : (
                <DashboardPage appSettings={appSettings} navigate={navigate} />
            )}
        </Shell>
    );
}
