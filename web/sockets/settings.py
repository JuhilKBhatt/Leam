import json
from pathlib import Path
from flask_socketio import SocketIO
from web.manager import run_module, stop_module, RUNNING_PROCESSES

def register_settings_socket(socketio: SocketIO, modules_dir: Path):
    @socketio.on("save_settings")
    def handle_save_settings(data):
        module_name = data.get("module")
        new_settings = data.get("settings", {})
        new_run_options = data.get("run_options", {}) 
        
        module_dir = modules_dir / module_name
        module_path = module_dir / "module.json"
        
        if not module_path.exists():
            return

        try:
            module_data = json.loads(module_path.read_text())
            current_settings = module_data.get("settings", {})

            # 1. Update Module Settings
            for key, value in new_settings.items():
                if key in current_settings:
                    if "-integer" in key:
                        try:
                            module_data["settings"][key] = float(value) if "integerF" in key else int(value)
                        except (ValueError, TypeError):
                            pass # Keep old value or handle error
                    else:
                        module_data["settings"][key] = value

            # 2. Update Run Options
            for key, value in new_run_options.items():
                if key == "runs_per_day":
                    module_data["run_options"][key] = int(value)
                else:
                    module_data["run_options"][key] = value

            # Save to file
            module_path.write_text(json.dumps(module_data, indent=4))
            socketio.emit("settings_saved", {"status": "success", "module": module_name})

            # 3. Handle Running State Changes
            is_running = module_name in RUNNING_PROCESSES
            should_be_on = module_data["run_options"].get("on", False)

            if is_running and not should_be_on:
                # User toggled it OFF while it was running
                print(f"[Settings] Stopping {module_name} as it was toggled OFF...")
                stop_module(module_name)
                socketio.emit("module_status", {"module": module_name, "status": "stopped"})
            
            elif is_running and should_be_on:
                # Restart to apply new settings
                print(f"[Settings] Restarting {module_name} to apply changes...")
                stop_module(module_name)
                run_module(module_name, module_dir, module_data["run_options"])
                socketio.emit("module_status", {"module": module_name, "status": "running"})
            
            elif not is_running and should_be_on:
                # User toggled it ON
                print(f"[Settings] Starting {module_name} as it was toggled ON...")
                run_module(module_name, module_dir, module_data["run_options"])
                socketio.emit("module_status", {"module": module_name, "status": "running"})

        except Exception as e:
            print(f"[Settings] Error: {e}")
            socketio.emit("settings_saved", {"status": "error", "error": str(e)})
