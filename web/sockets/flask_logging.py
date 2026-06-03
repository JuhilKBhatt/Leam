import time
import os
from pathlib import Path

def tail_log(socketio, module_name, log_path: Path):
    """Tails a log file and emits new lines to SocketIO."""
    if not log_path.exists():
        log_path.parent.mkdir(exist_ok=True)
        log_path.touch()

    with open(log_path, "r") as f:
        # Go to the end of the file
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                socketio.sleep(0.5)  # Slightly longer sleep to reduce CPU usage
                continue
            # Use "module_log" to match the frontend expectation
            socketio.emit("module_log", {"module": module_name, "line": line})

def send_existing_logs(socketio, module_name, log_path: Path, limit=50):
    """Sends the last N lines of a log file to SocketIO."""
    if not log_path.exists():
        return
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                socketio.emit("module_log", {"module": module_name, "line": line})
    except Exception as e:
        print(f"[Logging] Error reading existing logs: {e}")
