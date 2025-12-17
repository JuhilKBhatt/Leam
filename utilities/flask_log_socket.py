import json
from threading import Lock
from pathlib import Path
from .flask_logging import tail_log, send_existing_logs

log_threads = {}
log_thread_lock = Lock()

def register_log_sockets(socketio, modules_dir: Path):
    """Register all SocketIO events for log handling."""

    @socketio.on("subscribe_logs")
    def subscribe_logs(data):
        module_name = data.get("module")
        module_path = modules_dir / module_name
        module_json = module_path / "module.json"

        if not module_path.exists() or not module_json.exists():
            return

        module_data = json.loads(module_json.read_text())
        log_rel_path = module_data.get("log_file")
        if not log_rel_path:
            return

        log_path = module_path / log_rel_path
        log_path.parent.mkdir(exist_ok=True)
        log_path.touch(exist_ok=True)

        # send last 50 logs first
        send_existing_logs(socketio, module_name, log_path, limit=50)

        # start live tail
        with log_thread_lock:
            if module_name not in log_threads:
                log_threads[module_name] = socketio.start_background_task(tail_log, socketio, module_name, log_path)