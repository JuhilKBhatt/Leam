// ./static/scripts/settings_page.js

document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const timezoneSelect = document.getElementById("timezone-select");
    const saveBtn = document.getElementById("save-global-settings");

    // Load current settings
    socket.emit("get_global_settings");

    socket.on("global_settings", (data) => {
        if (data.timezone) {
            timezoneSelect.value = data.timezone;
        }
    });

    saveBtn.addEventListener("click", () => {
        const settings = {
            timezone: timezoneSelect.value
        };
        socket.emit("save_global_settings", settings);
        saveBtn.innerText = "Saving...";
        saveBtn.disabled = true;
    });

    socket.on("global_settings_saved", (data) => {
        if (data.status === "success") {
            saveBtn.innerText = "Settings Saved!";
            saveBtn.classList.add("btn-success"); // Assuming such a class exists or just visual feedback
            setTimeout(() => {
                saveBtn.innerText = "Save Settings";
                saveBtn.disabled = false;
                saveBtn.classList.remove("btn-success");
            }, 2000);
        } else {
            alert("Error saving settings: " + data.error);
            saveBtn.innerText = "Save Settings";
            saveBtn.disabled = false;
        }
    });
});
