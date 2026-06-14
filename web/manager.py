import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from core.utils.common import get_now

import threading
from core.utils.logger import SPAM_FILTER, manage_log_size

RUNNING_PROCESSES = {}  # module_name -> Popen

def log_reader(pipe, log_path):
    """Read from pipe and write to log_path if not spam."""
    with open(log_path, "a", encoding="utf-8") as f:
        for line in pipe:
            if not any(spam in line for spam in SPAM_FILTER):
                f.write(line)
                f.flush()

def get_modules(modules_dir: Path):
    """Return a list of all available modules with basic info."""
    modules = []
    if not modules_dir.exists():
        return modules
        
    for folder in modules_dir.iterdir():
        if folder.is_dir() and not folder.name.startswith("__"):
            desc_file = folder / "module.json"
            desc = {}
            if desc_file.exists():
                try:
                    desc = json.loads(desc_file.read_text())
                except json.JSONDecodeError:
                    pass
            modules.append({
                "module_name": desc.get("name", folder.name),
                "module_desc": desc.get("description", "No description available"),
                "module_link": f"/modules/{folder.name}",
                "run_file": desc.get("run_file")
            })
    return modules

def load_stats(stats_file: Path):
    if not stats_file.exists():
        return {}
    try:
        return json.loads(stats_file.read_text())
    except json.JSONDecodeError:
        return {}

def push_stats(socketio, stats_file: Path):
    """Emit system stats every second."""
    while True:
        socketio.emit("stats", load_stats(stats_file))
        socketio.sleep(1)

def run_module(module_name: str, module_dir: Path, options: dict):
    module_json = module_dir / "module.json"
    if not module_json.exists():
        return False
        
    data = json.loads(module_json.read_text())
    data["run_options"] = options
    data["run_options"]["on"] = True 
    module_json.write_text(json.dumps(data, indent=4))

    log_file = module_dir / data.get("log_file", "logs/runtime.log")
    log_file.parent.mkdir(exist_ok=True)

    # Updated path to supervisor
    cmd = [sys.executable, "-m", "core.supervisor", module_name]

    if module_name in RUNNING_PROCESSES:
        stop_module(module_name)

    # Manage log size before starting
    manage_log_size(log_file)

    with open(log_file, "a") as f:
        f.write(f"\n--- SUPERVISOR START {get_now()} ---\n")

    proc = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True,
        bufsize=1
    )

    thread = threading.Thread(target=log_reader, args=(proc.stdout, log_file), daemon=True)
    thread.start()

    RUNNING_PROCESSES[module_name] = proc
    return True

def stop_module(module_name: str):
    proc = RUNNING_PROCESSES.get(module_name)
    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        del RUNNING_PROCESSES[module_name]
        return True
    return False
