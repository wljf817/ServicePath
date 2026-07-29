const form = document.getElementById("diagnostic-form");
const button = document.getElementById("submit-button");
const consoleOutput = document.getElementById("console-output");

if (form) {
    form.addEventListener("submit", function () {
        button.disabled = true;
        button.textContent = "Running checks...";
        consoleOutput.innerHTML = "<p><span class='info'>[INFO]</span> Starting diagnostics...</p>";
    });
}
