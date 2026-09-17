import time
import os
from pathlib import Path

def tail_log(socketio, module_name, log_path: Path):
    """Tails a log file and emits new lines to SocketIO room for this module."""
    if not log_path.exists():
        log_path.parent.mkdir(exist_ok=True)
        log_path.touch()

    f = open(log_path, "r", encoding="utf-8", errors="replace")
    f.seek(0, os.SEEK_END)
    room = f"module_{module_name}"
    
    while True:
        line = f.readline()
        if not line:
            socketio.sleep(0.2)
            # Clear EOF state / read-ahead buffer in Python 3
            try:
                f.seek(f.tell())
                # Check if file was truncated (e.g. by manage_log_size)
                if f.tell() > os.path.getsize(log_path):
                    f.close()
                    f = open(log_path, "r", encoding="utf-8", errors="replace")
                    f.seek(0, os.SEEK_END)
            except OSError:
                pass
            continue
            
        line_clean = line.rstrip("\r\n")
        if line_clean.strip():
            socketio.emit("module_log", {"module": module_name, "line": line_clean}, room=room)

def send_existing_logs(socketio, module_name, log_path: Path, limit=1000, to=None):
    """Sends the last N lines of a log file to a specific client via SocketIO."""
    if not log_path.exists():
        return
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            clean_lines = [l.rstrip("\r\n") for l in recent_lines if l.strip()]
            
            if to:
                socketio.emit("existing_logs", {"module": module_name, "lines": clean_lines}, to=to)
            else:
                socketio.emit("existing_logs", {"module": module_name, "lines": clean_lines}, room=f"module_{module_name}")
    except Exception as e:
        print(f"[Logging] Error reading existing logs: {e}")
