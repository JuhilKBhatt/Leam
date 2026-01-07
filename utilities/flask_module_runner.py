import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime

RUNNING_PROCESSES = {}  # module_name -> Popen

def run_module(module_name: str, module_dir: Path, options: dict):
    module_json = module_dir / "module.json"
    
    # 1. Load and Update Config
    data = json.loads(module_json.read_text())
    
    # Ensure options are valid and persisted
    data["run_options"] = options
    # Force 'on' to true when manually running
    data["run_options"]["on"] = True 
    
    module_json.write_text(json.dumps(data, indent=4))

    log_file = module_dir / data.get("log_file", "logs/runtime.log")
    log_file.parent.mkdir(exist_ok=True)

    # 2. Command to run the Supervisor
    # We run from project root so 'utilities' matches the file path
    supervisor_script = "utilities/module_supervisor.py"
    
    cmd = [sys.executable, supervisor_script, module_name]

    # 3. Start Process
    with open(log_file, "a") as log:
        log.write(f"\n--- SUPERVISOR START {datetime.now()} ---\n")
        
        # Stop existing if running
        if module_name in RUNNING_PROCESSES:
            stop_module(module_name)

        # Run from Project Root (cwd=None or cwd=Path.cwd())
        # We assume flask_module_runner is called from App Root
        proc = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=log,
            text=True
        )

    RUNNING_PROCESSES[module_name] = proc
    return True

def stop_module(module_name: str):
    proc = RUNNING_PROCESSES.get(module_name)
    if proc:
        # Terminate the supervisor
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        del RUNNING_PROCESSES[module_name]
        
        # Optional: Update JSON to reflect 'on': false
        # This prevents it from being auto-resumed if you add a watcher later
        return True
    return False