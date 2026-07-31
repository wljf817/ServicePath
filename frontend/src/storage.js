import {openDB} from "idb";


const DATABASE_NAME = "servicepath";
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

const databasePromise = openDB(DATABASE_NAME, 1, {
    upgrade(db) {
        db.createObjectStore("settings");
        db.createObjectStore("reports", {autoIncrement: true, keyPath: "id"});
    },
});

export async function getBrowserSettings() {
    const saved = await (await databasePromise).get("settings", SETTINGS_KEY);
    return {...defaultSettings, ...(saved || {})};
}

export async function saveBrowserSettings(settings) {
    const saved = Object.fromEntries(
        Object.keys(defaultSettings).map((key) => [
            key,
            settings[key] ?? defaultSettings[key],
        ]),
    );
    await (await databasePromise).put("settings", saved, SETTINGS_KEY);
    return saved;
}

export async function saveReport(report) {
    const id = await (await databasePromise).add("reports", report);
    return {...report, id};
}

export async function getReport(reportId) {
    const id = Number(reportId);
    if (!Number.isSafeInteger(id) || id < 1) {
        throw new Error("Report ID is invalid.");
    }
    const report = await (await databasePromise).get("reports", id);
    if (!report) {
        throw new Error("Report not found in this browser.");
    }
    return report;
}

export async function getHistory() {
    const reports = await (await databasePromise).getAll("reports");
    return reports.sort((left, right) => right.id - left.id).slice(0, 50);
}
