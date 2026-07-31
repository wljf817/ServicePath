function getErrorMessage(data, response) {
    const serverMessage = [data?.error, data?.message]
        .find((value) => typeof value === "string" && value.trim());

    return serverMessage
        || response.statusText
        || `The request failed with status ${response.status}.`;
}

function requestError(message, status) {
    const error = new Error(message);
    error.status = status;
    return error;
}

async function request(url, options = {}) {
    const response = await fetch(url, options);
    const responseText = await response.text();
    let data = {};

    // Read the body once so HTML and empty error responses remain understandable.
    if (responseText) {
        try {
            data = JSON.parse(responseText);
        } catch {
            const message = response.ok
                ? "The server returned an invalid response."
                : `The request failed with status ${response.status}.`;
            throw requestError(message, response.status);
        }
    }

    if (!response.ok) {
        throw requestError(getErrorMessage(data, response), response.status);
    }

    return data;
}

function parseStreamEvent(line) {
    let event;
    try {
        event = JSON.parse(line);
    } catch {
        throw new Error("The server returned an invalid diagnostic event.");
    }
    if (!event || typeof event !== "object" || Array.isArray(event)) {
        throw new Error("The server returned an invalid diagnostic event.");
    }
    return event;
}

async function streamRequest(url, options, onEvent) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const responseText = await response.text();
        let data = {};
        if (responseText) {
            try {
                data = JSON.parse(responseText);
            } catch {
                throw requestError(
                    `The request failed with status ${response.status}.`,
                    response.status,
                );
            }
        }
        throw requestError(getErrorMessage(data, response), response.status);
    }
    if (!response.body) {
        throw new Error("The server did not provide a diagnostic event stream.");
    }
    const contentType = response.headers.get("Content-Type")?.split(";", 1)[0];
    if (contentType !== "application/x-ndjson") {
        throw new Error("The server returned an invalid diagnostic content type.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let result;

    function consume(line) {
        if (!line) {
            return;
        }
        const event = parseStreamEvent(line);
        if (event.type === "error") {
            throw new Error(event.error);
        }
        if (event.type === "complete") {
            if (result !== undefined) {
                throw new Error("The server returned multiple completion events.");
            }
            result = event.result;
            return;
        }
        if (![
            "run_started",
            "tool_started",
            "tool_completed",
            "tool_failed",
        ].includes(event.type)) {
            throw new Error("The server returned an unknown diagnostic event.");
        }
        onEvent(event);
    }

    while (true) {
        const {done, value} = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), {stream: !done});
        const lines = buffer.split("\n");
        buffer = lines.pop();
        lines.forEach(consume);
        if (done) {
            break;
        }
    }
    consume(buffer);

    if (result === undefined) {
        throw new Error("The diagnostic stream ended before completion.");
    }
    return result;
}

export function getAppSettings({signal} = {}) {
    return request("/api/app-settings", {signal});
}

export function getReport(reportId, {signal} = {}) {
    return request(`/api/reports/${reportId}`, {signal});
}

export function getHistory({signal} = {}) {
    return request("/api/history", {signal});
}

export function saveAppSettings(settings, {signal} = {}) {
    return request("/api/app-settings", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(settings),
        signal,
    });
}

export function startDiagnosis(domain, mode, {onEvent, signal} = {}) {
    if (typeof onEvent !== "function") {
        throw new TypeError("A diagnostic event handler is required.");
    }
    return streamRequest("/diagnose", {
        method: "POST",
        signal,
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({domain, mode}),
    }, onEvent);
}
