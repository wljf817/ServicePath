import {appPath} from "./paths";


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

async function responseJson(response, invalidMessage) {
    const text = await response.text();
    if (!text) {
        return {};
    }
    try {
        return JSON.parse(text);
    } catch {
        throw requestError(invalidMessage, response.status);
    }
}

async function request(url, options = {}) {
    const response = await fetch(url, options);
    const data = await responseJson(
        response,
        response.ok
            ? "The server returned an invalid response."
            : `The request failed with status ${response.status}.`,
    );

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
        const data = await responseJson(
            response,
            `The request failed with status ${response.status}.`,
        );
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
    return request(appPath("/api/app-settings"), {signal});
}

export function startDiagnosis(domain, settings, {onEvent, signal} = {}) {
    if (typeof onEvent !== "function") {
        throw new TypeError("A diagnostic event handler is required.");
    }
    const presetServer = settings.location.startsWith("preset:");
    return streamRequest(appPath("/diagnose"), {
        method: "POST",
        signal,
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            domain,
            location: presetServer ? "preset" : settings.location,
            server_id: presetServer ? settings.location.slice(7) : "",
            provider: settings.provider_type === "preset"
                ? {type: "preset", id: settings.preset_id}
                : {
                    type: "custom",
                    api_key: settings.openai_api_key,
                    api_mode: settings.openai_api_mode,
                    base_url: settings.openai_base_url,
                    model: settings.openai_model,
                },
            custom_server: {
                token: settings.custom_server_token,
                url: settings.custom_server_url,
            },
        }),
    }, onEvent);
}
