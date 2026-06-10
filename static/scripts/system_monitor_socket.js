// ./static/scripts/system_monitor_socket.js
const socket = io();

// Formatter for undefined values
const fmt = (v, unit = "") =>
    v === undefined || v === null || v === ""
        ? "N/A"
        : `${v}${unit}`;

const createBadge = (label, value) => `
    <div class="stat-badge">
        <span class="stat-label">${label}</span>
        <span class="stat-value">${value}</span>
    </div>
`;

socket.on("stats", (s = {}) => {
    const timestamp = s.timestamp
        ? new Date(s.timestamp).toLocaleString()
        : new Date().toLocaleString();

    const cpu = fmt(s.cpu, "%");
    const ramPercent = fmt(s.memory?.percent, "%");
    const networkUp = fmt(s.network?.up, "MB/s");
    const networkDown = fmt(s.network?.down, "MB/s");
    const uptime = fmt(s.uptime, "s");

    const monitorEl = document.getElementById("system-monitor");
    const timestampEl = document.getElementById("stat-timestamp");

    let badges = "";
    badges += createBadge("CPU Usage", cpu);
    badges += createBadge("RAM Usage", ramPercent);
    badges += createBadge("Network ↑", networkUp);
    badges += createBadge("Network ↓", networkDown);
    badges += createBadge("System Uptime", uptime);

    const tempsObj = s.temps || {};
    if (Object.keys(tempsObj).length > 0) {
        Object.entries(tempsObj).forEach(([k, v]) => {
            badges += createBadge(`${k} Temp`, fmt(v, "°C"));
        });
    }

    monitorEl.innerHTML = badges;
    if (timestampEl) timestampEl.textContent = `Last update: ${timestamp}`;
});