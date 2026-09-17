// ./static/scripts/module_settings_socket.js

document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const saveBtn = document.getElementById("save-settings-btn");
    const moduleName = window.LEAM_MODULE;
    const settingsForm = document.getElementById("settings-form");
    const statusBadge = document.getElementById("save-status-badge");
    const statusText = document.getElementById("save-status-text");
    const statusDot = document.getElementById("save-status-dot");

    if (!moduleName) return;

    let debounceTimer = null;
    let isSaving = false;

    // Helper: collect current form settings
    function collectSettings() {
        const settings = {};
        if (!settingsForm) return settings;

        const formData = new FormData(settingsForm);
        formData.forEach((value, key) => {
            settings[key] = value;
        });

        // Explicitly capture checkboxes
        const checkboxes = settingsForm.querySelectorAll("input[type=checkbox]");
        checkboxes.forEach(cb => {
            settings[cb.name] = cb.checked;
        });

        return settings;
    }

    // Helper: collect run options
    function collectRunOptions() {
        const runToggle = document.getElementById("run-toggle");
        const runModeToggle = document.getElementById("run-mode-toggle");
        const runsPerDay = document.getElementById("runs-per-day");
        const startTime = document.getElementById("start-time");
        const endTime = document.getElementById("end-time");

        return {
            on: runToggle ? runToggle.checked : false,
            mode: (runModeToggle && runModeToggle.checked) ? "indefinite" : "finite",
            runs_per_day: runsPerDay ? runsPerDay.value : 1,
            start_time: startTime ? startTime.value : "09:00",
            end_time: endTime ? endTime.value : "17:00"
        };
    }

    function setSaveState(state, message) {
        if (!statusBadge) return;

        statusBadge.classList.remove("status-saving", "status-saved", "status-error");

        if (state === "saving") {
            statusBadge.classList.add("status-saving");
            if (statusText) statusText.textContent = message || "Saving...";
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = "Saving...";
            }
        } else if (state === "saved") {
            statusBadge.classList.add("status-saved");
            if (statusText) statusText.textContent = message || "All changes saved";
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = "Save Configuration";
                saveBtn.classList.add("btn-success");
                setTimeout(() => saveBtn.classList.remove("btn-success"), 1500);
            }
        } else if (state === "error") {
            statusBadge.classList.add("status-error");
            if (statusText) statusText.textContent = message || "Failed to save";
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = "Save Configuration";
            }
        }
    }

    function triggerSave() {
        isSaving = true;
        setSaveState("saving");

        const settings = collectSettings();
        const runOptions = collectRunOptions();

        socket.emit("save_settings", {
            module: moduleName,
            settings: settings,
            run_options: runOptions
        });
    }

    function queueDebouncedSave(delay = 500) {
        setSaveState("saving", "Saving...");
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            triggerSave();
        }, delay);
    }

    // Auto-save listeners on settingsForm
    if (settingsForm) {
        // Text / numbers / textareas on typing
        settingsForm.addEventListener("input", (e) => {
            const target = e.target;
            if (target.type === "checkbox" || target.tagName === "SELECT") {
                return;
            }
            queueDebouncedSave(500);
        });

        // Checkboxes & selects on change
        settingsForm.addEventListener("change", (e) => {
            queueDebouncedSave(50); // immediate save
        });
    }

    // Auto-save listeners on Run Options container
    const runOptionsContainer = document.getElementById("run-options");
    if (runOptionsContainer) {
        runOptionsContainer.addEventListener("input", (e) => {
            queueDebouncedSave(500);
        });
        runOptionsContainer.addEventListener("change", (e) => {
            queueDebouncedSave(50);
        });
    }

    // Switches outside run-options (Master switch and Mode switch)
    const runToggle = document.getElementById("run-toggle");
    if (runToggle) {
        runToggle.addEventListener("change", () => {
            queueDebouncedSave(50);
        });
    }

    const runModeToggle = document.getElementById("run-mode-toggle");
    if (runModeToggle) {
        runModeToggle.addEventListener("change", () => {
            queueDebouncedSave(50);
        });
    }

    // Manual Save button click
    if (saveBtn) {
        saveBtn.addEventListener("click", (e) => {
            e.preventDefault();
            clearTimeout(debounceTimer);
            triggerSave();
        });
    }

    // Socket response
    socket.on("settings_saved", (data) => {
        if (data.module !== moduleName) return;
        isSaving = false;

        if (data.status === "success") {
            setSaveState("saved", "All changes saved");
        } else {
            setSaveState("error", "Error: " + (data.error || "Unknown"));
        }
    });
});
