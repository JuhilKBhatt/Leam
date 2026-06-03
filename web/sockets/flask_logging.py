import time
import os
from pathlib import Path

def tail_log(socketio, module_name, log_path: Path):
    """Tails a log file and emits new lines to SocketIO."""
    with open(log_path, "r") as f:
        # Go to the end of the file
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                socketio.sleep(0.1)  # Use socketio.sleep for eventlet/gevent compatibility
                continue
            socketio.emit("log", {"module": module_name, "data": line})

def send_existing_logs(socketio, module_name, log_path: Path, limit=50):
    """Sends the last N lines of a log file to SocketIO."""
    if not log_path.exists():
        return
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                socketio.emit("log", {"module": module_name, "data": line})
    except Exception as e:
        print(f"[Logging] Error reading existing logs: {e}")
