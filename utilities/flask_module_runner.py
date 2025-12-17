import subprocess
import json
from pathlib import Path
from datetime import datetime

RUNNING_PROCESSES = {}  # module_name -> Popen

def run_module(module_name: str, module_dir: Path, options: dict):
    module_json = module_dir / "module.json"
    data = json.loads(module_json.read_text())

    run_file = data["run_file"]
    log_file = module_dir / data.get("log_file", "logs/runtime.log")

    log_file.parent.mkdir(exist_ok=True)

    # persist run options
    data["run_options"] = options
    module_json.write_text(json.dumps(data, indent=4))

    cmd = ["python", run_file]

    with open(log_file, "a") as log:
        log.write(f"\n--- RUN START {datetime.now()} ---\n")

        proc = subprocess.Popen(
            cmd,
            cwd=module_dir,
            stdout=log,
            stderr=log,
            text=True
        )

    RUNNING_PROCESSES[module_name] = proc
    return True


def stop_module(module_name: str):
    proc = RUNNING_PROCESSES.get(module_name)
    if proc:
        proc.terminate()
        del RUNNING_PROCESSES[module_name]
        return True
    return False