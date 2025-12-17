document.getElementById("run-btn").addEventListener("click", () => {
    const mode = document.querySelector('input[name="mode"]:checked').value;

    const payload = {
        mode,
        runs_per_day: Number(document.getElementById("runs-per-day").value),
        start_time: document.getElementById("start-time").value,
        end_time: document.getElementById("end-time").value
    };

    console.log("Run config:", payload);
    // Later: socket.emit("run_module", payload)
});