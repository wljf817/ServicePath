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

export function startDiagnosis(domain, mode, {signal} = {}) {
    return request("/diagnose", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({domain, mode}),
        signal,
    });
}
