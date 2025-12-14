const socket = io();

const fmt = (v, unit = "") =>
    v === undefined || v === null || v === ""
        ? "N/A"
        : `${v}${unit}`;

socket.on("stats", (s = {}) => {
    const tempsObj = s.temps || {};
    let temps = "";

    if (Object.keys(tempsObj).length === 0) {
        temps = `<div>Temp: N/A</div>`;
    } else {
        for (const [k, v] of Object.entries(tempsObj)) {
            temps += `<div>${k}: ${fmt(v, "°C")}</div>`;
        }
    }

    document.getElementById("system-monitor").innerHTML = `
        <div>⏱ Uptime: ${fmt(s.uptime, "s")}</div>
        <div>CPU: ${fmt(s.cpu, "%")}</div>
        <div>
            RAM:
            ${fmt(s.memory?.used)} /
            ${fmt(s.memory?.total)} MB
            (${fmt(s.memory?.percent, "%")})
        </div>
        <div>
            Network:
            ↑ ${fmt(s.network?.up, " MB/s")}
            ↓ ${fmt(s.network?.down, " MB/s")}
        </div>
        ${temps}
    `;
});