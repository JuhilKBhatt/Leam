const socket = io();

document.getElementById("run-btn").addEventListener("click", () => {
    const toggle = document.getElementById("run-mode-toggle");

    const mode = toggle.checked ? "indefinite" : "finite";

    const options = {
        mode,
        runs_per_day: document.getElementById("runs-per-day").value,
        start_time: document.getElementById("start-time").value,
        end_time: document.getElementById("end-time").value
    };

    socket.emit("run_module", {
        module: window.LEAM_MODULE,
        options
    });
});