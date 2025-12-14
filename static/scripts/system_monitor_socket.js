// ./static/scripts/system_monitor_socket.js
const socket = io();

// Formatter for undefined values
const fmt = (v, unit = "") =>
    v === undefined || v === null || v === ""
        ? "N/A"
        : `${v}${unit}`;

socket.on("stats", (s = {}) => {
    const timestamp = s.timestamp
        ? new Date(s.timestamp).toLocaleString()
        : new Date().toLocaleString();

    const cpu = fmt(s.cpu, "%");
    const ramUsed = fmt(s.memory?.used, "MB");
    const ramPercent = fmt(s.memory?.percent, "%");
    const networkUp = fmt(s.network?.up, "MB/s");
    const networkDown = fmt(s.network?.down, "MB/s");
    const uptime = fmt(s.uptime, "s");

    const tempsObj = s.temps || {};
    let temps = "";
    if (Object.keys(tempsObj).length > 0) {
        temps = " | Temp: " + Object.entries(tempsObj)
            .map(([k, v]) => `${k}: ${fmt(v, "°C")}`)
            .join(", ");
    }

    // Single line display
    document.getElementById("system-monitor").textContent =
        `${timestamp} = CPU: ${cpu} | RAM: ${ramUsed} (${ramPercent}) | Network: ↑${networkUp} ↓${networkDown} | Uptime: ${uptime}${temps}`;
});