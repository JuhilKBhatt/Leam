from flask_socketio import SocketIO
from pathlib import Path
from .flask_module_runner import run_module, stop_module

def register_module_run(socketio: SocketIO, modules_dir: Path):

    @socketio.on("run_module")
    def handle_run(data):
        module = data["module"]
        options = data["options"]

        module_dir = modules_dir / module
        run_module(module, module_dir, options)

        socketio.emit("module_status", {
            "module": module,
            "status": "running"
        })

    @socketio.on("stop_module")
    def handle_stop(data):
        module = data["module"]
        stop_module(module)

        socketio.emit("module_status", {
            "module": module,
            "status": "stopped"
        })