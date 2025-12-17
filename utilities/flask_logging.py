from pathlib import Path
from flask_socketio import SocketIO
import datetime

def write_log(log_path: Path, message: str):
    """Write a log with timestamp to file."""
    log_path.parent.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"{timestamp} | {message}\n")

def send_existing_logs(socketio: SocketIO, module_name: str, log_path: Path, limit: int = 50):
    """Send the last `limit` lines from log file (newest first)."""
    if not log_path.exists():
        return
    with open(log_path, "r") as f:
        lines = f.readlines()[-limit:]
        for line in reversed(lines):
            socketio.emit("module_log", {"module": module_name, "line": line.rstrip()})

def tail_log(socketio: SocketIO, module_name: str, log_path: Path):
    """Continuously emits new log lines for a module."""
    with open(log_path, "r") as f:
        f.seek(0, 2)  # move to end
        while True:
            line = f.readline()
            if line:
                socketio.emit("module_log", {"module": module_name, "line": line.rstrip()})
            else:
                socketio.sleep(0.5)