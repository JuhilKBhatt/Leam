document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const saveBtn = document.getElementById("save-settings-btn");
    const moduleName = window.LEAM_MODULE;

    if (!saveBtn) return;

    saveBtn.addEventListener("click", () => {
        // 1. Gather Settings from form
        const settingsForm = document.getElementById("settings-form");
        const settings = {};
        
        // Use FormData but handle types if needed (backend also handles them)
        const formData = new FormData(settingsForm);
        formData.forEach((value, key) => {
            settings[key] = value;
        });

        // 2. Gather Run Options
        const runOptions = {
            on: document.getElementById("run-toggle").checked,
            mode: document.getElementById("run-mode-toggle").checked ? "indefinite" : "finite",
            runs_per_day: document.getElementById("runs-per-day").value,
            start_time: document.getElementById("start-time").value,
            end_time: document.getElementById("end-time").value
        };

        // Disable button while saving
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";

        socket.emit("save_settings", {
            module: moduleName,
            settings: settings,
            run_options: runOptions
        });
    });

    socket.on("settings_saved", (data) => {
        if (data.module !== moduleName) return;

        saveBtn.disabled = false;
        saveBtn.textContent = "Save Settings";

        if (data.status === "success") {
            // Flash green or show toast
            saveBtn.classList.add("btn-success");
            setTimeout(() => saveBtn.classList.remove("btn-success"), 2000);
        } else {
            alert("Error: " + data.error);
        }
    });
});
