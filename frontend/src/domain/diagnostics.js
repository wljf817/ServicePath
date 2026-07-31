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

export function runtimeState(value) {
    if (!RUNTIME_STATES.has(value)) {
        throw new TypeError(`Invalid runtime state: ${value}`);
    }
    return value;
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
        throw new TypeError("Invalid report date.");
    }
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}

export function reportLayers(report) {
    if (!report || !Array.isArray(report.layers)) {
        throw new TypeError("Invalid report layers.");
    }

    const layers = report.layers;
    if (!report.traceroute || layers.some((layer) => layer.key === "traceroute")) {
        return layers;
    }

    // The report schema stores route evidence after DNS.
    const dnsIndex = layers.findIndex((layer) => layer.key === "dns");
    if (dnsIndex < 0) {
        throw new TypeError("Traceroute requires a DNS layer.");
    }

    return [
        ...layers.slice(0, dnsIndex + 1),
        report.traceroute,
        ...layers.slice(dnsIndex + 1),
    ];
}

export function statusLabel(status) {
    const label = STATUS_LABELS[status];
    if (!label) {
        throw new TypeError(`Invalid diagnostic status: ${status}`);
    }
    return label;
}

export function toolNumber(key) {
    const number = DIAGNOSTIC_TOOLS.find((tool) => tool.key === key)?.number;
    if (!number) {
        throw new TypeError(`Invalid diagnostic tool: ${key}`);
    }
    return number;
}
