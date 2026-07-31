import {useEffect, useState} from "react";

import {runtimeState} from "../domain/diagnostics";

const modeLabels = {
    client: "Client",
    server: "Server",
};

export default function ScanProgress({mode, state}) {
    const [elapsedSeconds, setElapsedSeconds] = useState(0);
    const currentState = runtimeState(state);
    const running = currentState === "running";

    useEffect(() => {
        if (!running) {
            setElapsedSeconds(0);
            return undefined;
        }

        const startedAt = window.performance.now();
        let timer = null;
        const updateElapsedTime = () => {
            const elapsedMs = window.performance.now() - startedAt;
            setElapsedSeconds(Math.floor(elapsedMs / 1000));
            timer = window.setTimeout(
                updateElapsedTime,
                Math.max(16, 1000 - (elapsedMs % 1000)),
            );
        };

        updateElapsedTime();
        return () => window.clearTimeout(timer);
    }, [running]);

    if (!running) {
        return null;
    }

    const locationLabel = modeLabels[mode];
    if (!locationLabel) {
        throw new TypeError(`Invalid diagnostic mode: ${mode}`);
    }

    return (
        <div className="scan-progress" data-state={currentState}>
            <div className="scan-progress-orb" aria-hidden="true">
                <span />
            </div>

            <div className="scan-progress-copy">
                <span className="scan-progress-location">{locationLabel}</span>
                <p aria-atomic="true" className="scan-progress-announcement" role="status">
                    Investigation in progress
                </p>
            </div>

            <time className="scan-progress-time" dateTime={`PT${elapsedSeconds}S`}>
                {elapsedSeconds}s elapsed
            </time>

            <div className="scan-progress-track" aria-hidden="true">
                <span />
            </div>
        </div>
    );
}
