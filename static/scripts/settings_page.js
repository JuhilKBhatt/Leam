// ./static/scripts/settings_page.js

document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const timezoneSelect = document.getElementById("timezone-select");
    const saveBtn = document.getElementById("save-global-settings");
    const statusBadge = document.getElementById("global-save-status");
    const statusText = document.getElementById("global-save-text");

    function setSaveStatus(state, message) {
        if (!statusBadge) return;
        statusBadge.classList.remove("status-saving", "status-saved", "status-error");
        
        if (state === "saving") {
            statusBadge.classList.add("status-saving");
            if (statusText) statusText.textContent = message || "Saving...";
            if (saveBtn) {
                saveBtn.innerText = "Saving...";
                saveBtn.disabled = true;
            }
        } else if (state === "saved") {
            statusBadge.classList.add("status-saved");
            if (statusText) statusText.textContent = message || "Settings saved";
            if (saveBtn) {
                saveBtn.innerText = "Saved";
                saveBtn.disabled = false;
                saveBtn.classList.add("btn-success");
                setTimeout(() => {
                    saveBtn.innerText = "Save Settings";
                    saveBtn.classList.remove("btn-success");
                }, 2000);
            }
        } else if (state === "error") {
            statusBadge.classList.add("status-error");
            if (statusText) statusText.textContent = message || "Save failed";
            if (saveBtn) {
                saveBtn.innerText = "Save Settings";
                saveBtn.disabled = false;
            }
        }
    }

    // Load current settings
    socket.emit("get_global_settings");

    socket.on("global_settings", (data) => {
        if (data && data.timezone && timezoneSelect) {
            timezoneSelect.value = data.timezone;
        }
    });

    function saveGlobalSettings() {
        if (!timezoneSelect) return;
        setSaveStatus("saving", "Saving...");
        const settings = {
            timezone: timezoneSelect.value
        };
        socket.emit("save_global_settings", settings);
    }

    // Auto-save immediately on timezone change
    if (timezoneSelect) {
        timezoneSelect.addEventListener("change", () => {
            saveGlobalSettings();
        });
    }

    // Manual save button fallback
    if (saveBtn) {
        saveBtn.addEventListener("click", (e) => {
            e.preventDefault();
            saveGlobalSettings();
        });
    }

    socket.on("global_settings_saved", (data) => {
        if (data.status === "success") {
            setSaveStatus("saved", "All settings saved");
        } else {
            setSaveStatus("error", "Error: " + (data.error || "Save failed"));
        }
    });
});
