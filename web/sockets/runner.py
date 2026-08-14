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
            m_dir = modules_dir / finished_module
            m_json = m_dir / "module.json"
            if m_json.exists():
                try:
                    config = json.loads(m_json.read_text())
                    if config.get("run_options", {}).get("on"):
                        config["run_options"]["on"] = False
                        m_json.write_text(json.dumps(config, indent=4))
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
        module_dir = modules_dir / module
        module_json = module_dir / "module.json"
        if module_json.exists():
            try:
                config = json.loads(module_json.read_text())
                config["run_options"]["on"] = False
                module_json.write_text(json.dumps(config, indent=4))
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
