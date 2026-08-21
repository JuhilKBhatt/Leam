from flask_socketio import SocketIO
from pathlib import Path
from web.manager import run_module, stop_module, RUNNING_PROCESSES

def register_module_run(socketio: SocketIO, modules_dir: Path):

    @socketio.on("run_module")
    def handle_run(data):
        module = data["module"]
        options = data["options"]

        module_dir = modules_dir / module
        print(f"[Runner] Manually starting {module}...")
        
        def on_module_finish(finished_module):
            from core.utils.common import load_module_config, save_module_config
            m_dir = modules_dir / finished_module
            config = load_module_config(m_dir)
            if config:
                try:
                    if config.get("run_options", {}).get("on"):
                        config.setdefault("run_options", {})["on"] = False
                        save_module_config(m_dir, config)
                except Exception as e:
                    print(f"[Runner] Error updating config on finish: {e}")

            socketio.emit("module_status", {
                "module": finished_module,
                "status": "stopped"
            })

        # This will update module.json with options and set 'on': true
        success = run_module(module, module_dir, options, on_finish=on_module_finish)

        if success:
            socketio.emit("module_status", {
                "module": module,
                "status": "running"
            })

    @socketio.on("stop_module")
    def handle_stop(data):
        module = data["module"]
        print(f"[Runner] Manually stopping {module}...")
        
        success = stop_module(module)

        # Also update module.json to reflect 'on': false so it doesn't auto-restart
        from core.utils.common import load_module_config, save_module_config
        module_dir = modules_dir / module
        config = load_module_config(module_dir)
        if config:
            try:
                config.setdefault("run_options", {})["on"] = False
                save_module_config(module_dir, config)
            except Exception as e:
                print(f"[Runner] Error updating config: {e}")

        socketio.emit("module_status", {
            "module": module,
            "status": "stopped"
        })

    @socketio.on("get_module_status")
    def handle_get_status(data):
        module = data.get("module")
        status = "running" if module in RUNNING_PROCESSES else "stopped"
        socketio.emit("module_status", {"module": module, "status": status})

# Need to import json for the stop_module config update
import json
