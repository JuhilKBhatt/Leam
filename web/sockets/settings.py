import json
from pathlib import Path
from flask_socketio import SocketIO
from web.manager import run_module, stop_module, RUNNING_PROCESSES
from core.utils.common import get_global_settings, save_global_settings

def register_settings_socket(socketio: SocketIO, modules_dir: Path):
    @socketio.on("get_global_settings")
    def handle_get_global_settings():
        socketio.emit("global_settings", get_global_settings())

    @socketio.on("save_global_settings")
    def handle_save_global_settings(data):
        try:
            save_global_settings(data)
            socketio.emit("global_settings_saved", {"status": "success", "settings": data})
            print(f"[Settings] Global settings updated: {data}")
        except Exception as e:
            print(f"[Settings] Error saving global settings: {e}")
            socketio.emit("global_settings_saved", {"status": "error", "error": str(e)})

    @socketio.on("save_settings")
    def handle_save_settings(data):
        from core.utils.common import load_module_config, save_module_config
        module_name = data.get("module")
        new_settings = data.get("settings", {})
        new_run_options = data.get("run_options", {})
        
        module_dir = modules_dir / module_name
        
        try:
            module_data = load_module_config(module_dir)
            if not module_data:
                return
                
            current_settings = module_data.get("settings", {})
            current_run_options = dict(module_data.get("run_options", {}))

            # 1. Update Module Settings
            for key, value in new_settings.items():
                if key in current_settings:
                    if "-integer" in key:
                        try:
                            module_data["settings"][key] = float(value) if "integerF" in key else int(value)
                        except (ValueError, TypeError):
                            pass
                    elif "-boolean" in key:
                        module_data["settings"][key] = bool(value)
                    else:
                        module_data["settings"][key] = value

            # 2. Update Run Options
            for key, value in new_run_options.items():
                if key == "runs_per_day":
                    try:
                        module_data.setdefault("run_options", {})[key] = int(value)
                    except (ValueError, TypeError):
                        pass
                elif key == "on":
                    module_data.setdefault("run_options", {})[key] = bool(value)
                else:
                    module_data.setdefault("run_options", {})[key] = value

            # Save to module.local.json
            save_module_config(module_dir, module_data)
            socketio.emit("settings_saved", {"status": "success", "module": module_name})

            # 3. Handle Running State Changes ONLY if run_options actually changed
            run_options_changed = (module_data.get("run_options", {}) != current_run_options)
            if run_options_changed:
                is_running = module_name in RUNNING_PROCESSES
                should_be_on = module_data["run_options"].get("on", False)
                run_mode = module_data["run_options"].get("mode", "finite")

                if is_running and not should_be_on:
                    print(f"[Settings] Stopping {module_name} as it was toggled OFF...")
                    stop_module(module_name)
                    socketio.emit("module_status", {"module": module_name, "status": "stopped"})
                
                elif is_running and should_be_on:
                    if run_mode == "indefinite":
                        print(f"[Settings] Restarting {module_name} scheduler to apply changes...")
                        stop_module(module_name)
                        run_module(module_name, module_dir, module_data["run_options"])
                        socketio.emit("module_status", {"module": module_name, "status": "running"})
                
                elif not is_running and should_be_on:
                    if run_mode == "indefinite":
                        print(f"[Settings] Starting {module_name} scheduler as it was toggled ON...")
                        run_module(module_name, module_dir, module_data["run_options"])
                        socketio.emit("module_status", {"module": module_name, "status": "running"})

        except Exception as e:
            print(f"[Settings] Error saving settings for {module_name}: {e}")
            socketio.emit("settings_saved", {"status": "error", "module": module_name, "error": str(e)})
