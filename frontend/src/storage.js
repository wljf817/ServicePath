const DATABASE_NAME = "servicepath";
const DATABASE_VERSION = 1;
const SETTINGS_KEY = "current";

export const defaultSettings = {
    custom_server_token: "",
    custom_server_url: "",
    location: "local",
    openai_api_key: "",
    openai_api_mode: "responses",
    openai_base_url: "",
    openai_model: "gpt-5.6",
    preset_id: "",
    provider_type: "custom",
};

function requestResult(request) {
    return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
        request.onupgradeneeded = () => {
            const database = request.result;
            database.createObjectStore("settings");
            database.createObjectStore("reports", {
                autoIncrement: true,
                keyPath: "id",
            });
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function store(name, mode, operation) {
    const database = await openDatabase();
    try {
        const transaction = database.transaction(name, mode);
        return await operation(transaction.objectStore(name));
    } finally {
        database.close();
    }
}

export async function getBrowserSettings() {
    const saved = await store(
        "settings",
        "readonly",
        (settings) => requestResult(settings.get(SETTINGS_KEY)),
    );
    return {...defaultSettings, ...(saved || {})};
}

export async function saveBrowserSettings(settings) {
    const saved = Object.fromEntries(
        Object.keys(defaultSettings).map((key) => [
            key,
            settings[key] ?? defaultSettings[key],
        ]),
    );
    await store(
        "settings",
        "readwrite",
        (records) => requestResult(records.put(saved, SETTINGS_KEY)),
    );
    return saved;
}

export async function saveReport(report) {
    const id = await store(
        "reports",
        "readwrite",
        (reports) => requestResult(reports.add(report)),
    );
    return {...report, id};
}

export async function getReport(reportId) {
    const id = Number(reportId);
    if (!Number.isSafeInteger(id) || id < 1) {
        throw new Error("Report ID is invalid.");
    }
    const report = await store(
        "reports",
        "readonly",
        (reports) => requestResult(reports.get(id)),
    );
    if (!report) {
        throw new Error("Report not found in this browser.");
    }
    return report;
}

export async function getHistory() {
    const reports = await store(
        "reports",
        "readonly",
        (records) => requestResult(records.getAll()),
    );
    return reports.sort((left, right) => right.id - left.id).slice(0, 50);
}
