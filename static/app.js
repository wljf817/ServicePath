function showConsoleMessage(consoleOutput, label, className, message) {
    const line = document.createElement("p");
    const marker = document.createElement("span");

    marker.className = className;
    marker.textContent = `[${label}]`;
    line.append(marker, document.createTextNode(` ${message}`));
    consoleOutput.replaceChildren(line);
}

document.addEventListener("submit", async function (event) {
    const form = event.target;

    if (form.id !== "diagnostic-form") {
        return;
    }

    event.preventDefault();

    const button = form.querySelector("#submit-button");
    const consoleOutput = document.querySelector("#console-output");
    button.disabled = true;
    button.textContent = "Agent investigating...";
    showConsoleMessage(consoleOutput, "AGENT", "info", "Selecting diagnostic tools...");

    try {
        const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: {"Accept": "application/json"},
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "The diagnosis could not be completed.");
        }

        window.location.assign(data.report_url);
    } catch (error) {
        showConsoleMessage(consoleOutput, "ERROR", "error", error.message);
        button.disabled = false;
        button.textContent = "Start investigation";
    }
});
