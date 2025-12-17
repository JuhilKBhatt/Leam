const socket = io();
const moduleName = "{{ module_name }}";
const logsEl = document.getElementById("logs");

socket.emit("subscribe_logs", { module: moduleName });

socket.on("module_log", (data) => {
    if (data.module !== moduleName) return;

    logsEl.textContent += data.line + "\n";
    logsEl.scrollTop = logsEl.scrollHeight;
});