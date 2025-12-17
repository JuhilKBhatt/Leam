document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const logsEl = document.getElementById("logs");
    const moduleName = window.LEAM_MODULE;
    const maxLogs = 50; // maximum number of lines to display
    const logBuffer = []; // stores log lines

    socket.emit("subscribe_logs", { module: moduleName });

    socket.on("module_log", (data) => {
        if (data.module !== moduleName) return;

        // Add new line to the start of buffer
        logBuffer.unshift(data.line);

        // Keep only the last maxLogs entries
        if (logBuffer.length > maxLogs) {
            logBuffer.pop();
        }

        // Display logs newest first
        logsEl.textContent = logBuffer.join("\n");
    });
});