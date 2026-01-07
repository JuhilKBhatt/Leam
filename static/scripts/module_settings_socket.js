document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const saveBtn = document.getElementById("save-settings-btn");
    
    if (saveBtn) {
        saveBtn.addEventListener("click", (e) => {
            e.preventDefault(); // Prevent default form submission if inside a form tag
            
            const form = document.getElementById("settings-form");
            const formData = new FormData(form);
            const settings = {};
            
            // Convert FormData to a standard JSON object
            formData.forEach((value, key) => {
                settings[key] = value;
            });

            // Send to backend
            socket.emit("save_settings", {
                module: window.LEAM_MODULE,
                settings: settings
            });
            
            // Optional: Visual feedback immediately
            saveBtn.textContent = "Saving...";
            saveBtn.disabled = true;
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