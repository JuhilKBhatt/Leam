const socket = io();

socket.on("stats", (s) => {
    if (!s.cpu) return;

    let temps = "";
    for (const [k, v] of Object.entries(s.temps || {})) {
        temps += `<div>${k}: ${v}°C</div>`;
    }

    document.getElementById("system-monitor").innerHTML = `
        <div>⏱ Uptime: ${s.uptime}s</div>
        <div>CPU: ${s.cpu}%</div>
        <div>RAM: ${s.memory.used}/${s.memory.total} MB (${s.memory.percent}%)</div>
        <div>Disk: ${s.disk.used}/${s.disk.total} GB (${s.disk.percent}%)</div>
        <div>Network: ↑ ${s.network.up} MB/s ↓ ${s.network.down} MB/s</div>
        ${temps}
    `;
});
