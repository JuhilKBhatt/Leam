document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const runBtn = document.getElementById("run-btn");
    const moduleName = window.LEAM_MODULE;

    if (!runBtn) return;

    // Request initial status
    socket.emit("get_module_status", { module: moduleName });

    runBtn.addEventListener("click", () => {
        const toggle = document.getElementById("run-mode-toggle");
        const isOn = runBtn.getAttribute("data-status") === "running";

        if (isOn) {
            // Stop logic
            socket.emit("stop_module", { module: moduleName });
            runBtn.textContent = "Stopping...";
        } else {
            // Run logic
            const mode = toggle.checked ? "indefinite" : "finite";
            const options = {
                on: true,
                mode,
                runs_per_day: document.getElementById("runs-per-day").value,
                start_time: document.getElementById("start-time").value,
                end_time: document.getElementById("end-time").value
            };

            socket.emit("run_module", {
                module: moduleName,
                options
            });
            runBtn.textContent = "Starting...";
        }
    });

    socket.on("module_status", (data) => {
        if (data.module !== moduleName) return;

        if (data.status === "running") {
            runBtn.textContent = "Stop Module";
            runBtn.classList.add("btn-running");
            runBtn.setAttribute("data-status", "running");
        } else {
            runBtn.textContent = `Run ${window.MODULE_RUN_FILE || 'Module'}`;
            runBtn.classList.remove("btn-running");
            runBtn.setAttribute("data-status", "stopped");
        }
    });
});
