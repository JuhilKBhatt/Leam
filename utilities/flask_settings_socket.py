import json
from pathlib import Path
from flask_socketio import SocketIO

def register_settings_socket(socketio: SocketIO, modules_dir: Path):
    """Registers SocketIO event for saving module settings."""

    @socketio.on("save_settings")
    def handle_save_settings(data):
        module_name = data.get("module")
        new_settings = data.get("settings", {})
        
        module_path = modules_dir / module_name / "module.json"
        
        if not module_path.exists():
            socketio.emit("settings_saved", {"status": "error", "error": "Module not found"})
            return

        try:
            # 1. Load existing JSON to preserve other fields (description, run_options, etc.)
            module_data = json.loads(module_path.read_text())
            current_settings = module_data.get("settings", {})

            # 2. Update settings with type conversion
            for key, value in new_settings.items():
                if key in current_settings:
                    # Handle Integers (e.g., Story_Min_Score-integerNE)
                    if "-integer" in key:
                        # Check for Floats (e.g., -integerFE)
                        if "integerF" in key:
                            try:
                                module_data["settings"][key] = float(value)
                            except ValueError:
                                pass # Keep old value or handle error
                        else:
                            try:
                                module_data["settings"][key] = int(value)
                            except ValueError:
                                pass
                    
                    # Handle Booleans (if you add them later)
                    elif "-bool" in key:
                        module_data["settings"][key] = (value == "on" or value is True)
                    
                    # Default to String
                    else:
                        module_data["settings"][key] = value

            # 3. Write updates back to file
            module_path.write_text(json.dumps(module_data, indent=4))
            
            # 4. Notify client
            socketio.emit("settings_saved", {"status": "success", "module": module_name})
            print(f"[Settings] Saved changes for {module_name}")

        except Exception as e:
            print(f"[Settings] Error saving {module_name}: {e}")
            socketio.emit("settings_saved", {"status": "error", "error": str(e)})