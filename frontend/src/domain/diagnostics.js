export const DIAGNOSTIC_TOOLS = [
    {key: "client", name: "Client Network", pathName: "Device", description: "Client network", number: "01"},
    {key: "dns", name: "DNS", pathName: "DNS", description: "Name resolution", number: "02"},
    {key: "traceroute", name: "Traceroute", pathName: "Route", description: "Network path", number: "TR"},
    {key: "tcp", name: "TCP", pathName: "TCP", description: "Port connection", number: "03"},
    {key: "tls", name: "TLS", pathName: "TLS", description: "Secure handshake", number: "04"},
    {key: "http", name: "HTTP", pathName: "HTTP", description: "Application response", number: "05"},
];

const STATUS_LABELS = {
    passed: "PASS",
    warning: "WARN",
    error: "ERROR",
    skipped: "SKIP",
};

const RUNTIME_STATES = new Set(["idle", "running", "error"]);

export function safeText(value, fallback = "") {
    if (typeof value === "string") {
        return value.trim() ? value : fallback;
    }
    if (typeof value === "number" || typeof value === "boolean") {
        return String(value);
    }
    return fallback;
}

export function safeTextList(value) {
    if (!Array.isArray(value)) {
        return [];
    }
    return value.map((item) => safeText(item)).filter(Boolean);
}

export function runtimeState(value, loading = false) {
    if (RUNTIME_STATES.has(value)) {
        return value;
    }
    return loading ? "running" : "idle";
}

function displayValue(value) {
    if (value === null || value === undefined || value === "") {
        return "None";
    }
    if (Array.isArray(value)) {
        return value.map((item) => (
            item && typeof item === "object" ? JSON.stringify(item) : String(item)
        )).join(", ") || "None";
    }
    return String(value);
}

export function detailLines(value, prefix = "") {
    const lines = [];

    Object.entries(value || {}).forEach(([key, item]) => {
        const label = prefix ? `${prefix} > ${key}` : key;
        if (item && typeof item === "object" && !Array.isArray(item)) {
            const nestedLines = detailLines(item, label);
            lines.push(...(nestedLines.length ? nestedLines : [{label, display: "None"}]));
        } else {
            lines.push({label, display: displayValue(item)});
        }
    });

    return lines;
}

export function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return "Unknown time";
    }
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}

export function reportLayers(report) {
    const layers = Array.isArray(report?.layers) ? report.layers : [];
    if (!report?.traceroute || layers.some((layer) => layer.key === "traceroute")) {
        return layers;
    }

    // Older reports store traceroute separately, so insert it after DNS.
    const dnsIndex = layers.findIndex((layer) => layer.key === "dns");
    if (dnsIndex < 0) {
        return [...layers, report.traceroute];
    }

    return [
        ...layers.slice(0, dnsIndex + 1),
        report.traceroute,
        ...layers.slice(dnsIndex + 1),
    ];
}

export function statusLabel(status = "") {
    return STATUS_LABELS[status] || status.toUpperCase();
}

export function toolNumber(key, fallbackIndex) {
    return DIAGNOSTIC_TOOLS.find((tool) => tool.key === key)?.number
        || String(fallbackIndex + 1).padStart(2, "0");
}
