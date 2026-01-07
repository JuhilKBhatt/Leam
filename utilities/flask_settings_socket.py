import json
from pathlib import Path
from flask_socketio import SocketIO
from .flask_module_runner import run_module, stop_module, RUNNING_PROCESSES

def register_settings_socket(socketio: SocketIO, modules_dir: Path):
    @socketio.on("save_settings")
    def handle_save_settings(data):
        module_name = data.get("module")
        new_settings = data.get("settings", {})
        # Capture run options from the frontend
        new_run_options = data.get("run_options", {}) 
        
        module_dir = modules_dir / module_name
        module_path = module_dir / "module.json"
        
        if not module_path.exists():
            return

        try:
            module_data = json.loads(module_path.read_text())
            current_settings = module_data.get("settings", {})
            current_run_ops = module_data.get("run_options", {})

            # Update Settings (keeping type conversion logic)
            for key, value in new_settings.items():
                if key in current_settings:
                    if "-integer" in key:
                        module_data["settings"][key] = float(value) if "integerF" in key else int(value)
                    else:
                        module_data["settings"][key] = value

            # Update Run Options
            for key, value in new_run_options.items():
                # run_options usually plain strings/ints from HTML inputs
                # Convert numbers if necessary
                if key in ["runs_per_day"]:
                    module_data["run_options"][key] = int(value)
                else:
                    module_data["run_options"][key] = value

            # Save to file
            module_path.write_text(json.dumps(module_data, indent=4))
            socketio.emit("settings_saved", {"status": "success", "module": module_name})

            # RESTART LOGIC
            # If module is currently running, restart it to pick up new settings
            if module_name in RUNNING_PROCESSES:
                print(f"[Settings] Restarting {module_name} to apply changes...")
                stop_module(module_name)
                # Restart with the updated options from the file
                run_module(module_name, module_dir, module_data["run_options"])
                socketio.emit("module_status", {"module": module_name, "status": "running"})

        except Exception as e:
            print(f"Error: {e}")
            socketio.emit("settings_saved", {"status": "error", "error": str(e)})