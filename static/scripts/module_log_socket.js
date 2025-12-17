document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const logsEl = document.getElementById("logs");
    const moduleName = window.LEAM_MODULE;
    let firstLog = true; // Flag to clear placeholder on first log

    socket.emit("subscribe_logs", { module: moduleName });

    socket.on("module_log", (data) => {
        if (data.module !== moduleName) return;

        // Clear placeholder text on first log
        if (firstLog) {
            logsEl.textContent = "";
            firstLog = false;
        }

        logsEl.textContent += data.line + "\n";
        logsEl.scrollTop = logsEl.scrollHeight;
    });
});