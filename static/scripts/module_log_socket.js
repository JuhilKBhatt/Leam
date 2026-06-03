document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const logsEl = document.getElementById("logs");
    const moduleName = window.LEAM_MODULE;
    const maxLogs = 100; // Increased limit
    const logBuffer = [];

    if (!logsEl) return;

    socket.emit("subscribe_logs", { module: moduleName });

    socket.on("module_log", (data) => {
        if (data.module !== moduleName) return;

        // Clean line
        const line = data.line.trim();
        if (!line) return;

        // Add new line to buffer
        logBuffer.push(line);

        // Keep only the last maxLogs entries
        if (logBuffer.length > maxLogs) {
            logBuffer.shift();
        }

        // Display logs with auto-scroll
        logsEl.textContent = logBuffer.join("\n");
        logsEl.scrollTop = logsEl.scrollHeight;
    });

    // Handle clearing logs UI
    socket.on("module_status", (data) => {
        if (data.module === moduleName && data.status === "running") {
            // Optional: clear UI on restart
            // logBuffer.length = 0;
            // logsEl.textContent = "Restarting module...";
        }
    });
});
