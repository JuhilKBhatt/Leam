document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const saveBtn = document.getElementById("save-settings-btn");
    
    if (saveBtn) {
        saveBtn.addEventListener("click", () => {
            // 1. Gather Settings
            const settingsForm = document.getElementById("settings-form");
            const settingsData = new FormData(settingsForm);
            const settings = {};
            settingsData.forEach((val, key) => settings[key] = val);

            // 2. Gather Run Options explicitly
            // (These inputs are in a different div, likely not inside the settings-form tag)
            const runOptions = {
                mode: document.getElementById("run-mode-toggle")?.checked ? "indefinite" : "finite",
                runs_per_day: document.getElementById("runs-per-day")?.value,
                start_time: document.getElementById("start-time")?.value,
                end_time: document.getElementById("end-time")?.value
            };

            console.log("Saving Settings:", settings);
            console.log("Run Options:", runOptions);

            // 3. Send both
            socket.emit("save_settings", {
                module: window.LEAM_MODULE,
                settings: settings,
                run_options: runOptions 
            });
            
            saveBtn.textContent = "Saving...";
        });
    }
    
    // Listen for confirmation
    socket.on("settings_saved", (data) => {
        if (saveBtn) {
            saveBtn.textContent = "Save Settings";
            saveBtn.disabled = false;
        }

        if (data.status === "success") {
            // You could use a nicer toast notification here
            alert("Settings saved successfully!");
        } else {
            alert("Error saving settings: " + data.error);
        }
    });
});