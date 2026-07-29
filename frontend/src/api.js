async function request(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "The request could not be completed.");
    }

    return data;
}

export function getAppSettings() {
    return request("/api/app-settings");
}

export function getReport(reportId) {
    return request(`/api/reports/${reportId}`);
}

export function startDiagnosis(domain, mode) {
    const formData = new FormData();
    formData.append("domain", domain);
    formData.append("mode", mode);

    return request("/diagnose", {
        method: "POST",
        body: formData,
        headers: {Accept: "application/json"},
    });
}
