import json
from threading import Lock
from pathlib import Path
from flask import request
from flask_socketio import join_room
from .flask_logging import tail_log, send_existing_logs

log_threads = {}
log_thread_lock = Lock()

def register_log_sockets(socketio, modules_dir: Path):
    """Register all SocketIO events for log handling."""

    @socketio.on("subscribe_logs")
    def subscribe_logs(data):
        from core.utils.common import load_module_config
        module_name = data.get("module")
        if not module_name:
            return

        module_path = modules_dir / module_name
        module_data = load_module_config(module_path)
        if not module_data:
            return

        log_rel_path = module_data.get("log_file")
        if not log_rel_path:
            return

        log_path = module_path / log_rel_path
        log_path.parent.mkdir(exist_ok=True)
        log_path.touch(exist_ok=True)

        # Join the room specific to this module so only relevant logs are sent
        room = f"module_{module_name}"
        join_room(room)

        # Send up to 1000 existing logs in a single batch directly to requesting client
        send_existing_logs(socketio, module_name, log_path, limit=1000, to=request.sid)

        # Start live tail background task for this module if not running
        with log_thread_lock:
            if module_name not in log_threads:
                log_threads[module_name] = socketio.start_background_task(tail_log, socketio, module_name, log_path)