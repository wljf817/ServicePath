import {useEffect, useState} from "react";

const checkLabels = [
    "client network details",
    "DNS resolution",
    "network route",
    "TCP connections",
    "TLS security",
    "HTTP response",
    "diagnostic results",
];

const modeLabels = {
    local: "Local device",
    remote: "Remote server",
    compare: "Local and remote",
};

export default function ScanProgress({loading, mode}) {
    const [elapsedSeconds, setElapsedSeconds] = useState(0);

    useEffect(() => {
        if (!loading) {
            setElapsedSeconds(0);
            return undefined;
        }

        const timer = window.setInterval(() => {
            setElapsedSeconds((seconds) => seconds + 1);
        }, 1000);

        return () => window.clearInterval(timer);
    }, [loading]);

    if (!loading) {
        return null;
    }

    const checkIndex = Math.floor(elapsedSeconds / 2) % checkLabels.length;
    const currentCheck = checkLabels[checkIndex];
    const locationLabel = modeLabels[mode] || "Diagnostic service";

    return (
        <div className="scan-progress">
            <div className="scan-progress-orb" aria-hidden="true">
                <span />
            </div>

            <div className="scan-progress-copy">
                <span className="scan-progress-location">{locationLabel}</span>
                <p
                    className="scan-progress-announcement"
                    aria-atomic="true"
                    aria-live="polite"
                >
                    Currently checking {currentCheck}
                </p>
            </div>

            <time className="scan-progress-time">
                {elapsedSeconds}s elapsed
            </time>

            <div className="scan-progress-track" aria-hidden="true">
                <span />
            </div>
        </div>
    );
}
