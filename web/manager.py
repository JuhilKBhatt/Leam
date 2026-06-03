import json
import sys
from gevent import subprocess
from pathlib import Path
from datetime import datetime

RUNNING_PROCESSES = {}  # module_name -> Popen

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
    supervisor_script = "core/supervisor.py"
    cmd = [sys.executable, supervisor_script, module_name]

    with open(log_file, "a") as log:
        log.write(f"\n--- SUPERVISOR START {datetime.now()} ---\n")
        if module_name in RUNNING_PROCESSES:
            stop_module(module_name)
        proc = subprocess.Popen(cmd, stdout=log, stderr=log, text=True)

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
