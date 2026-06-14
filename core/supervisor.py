import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from core.utils.common import get_now
from core.utils.logger import write_log, manage_log_size

# Global log file path for the module
LOG_FILE = None

def log(message, level="INFO"):
    if LOG_FILE:
        write_log(LOG_FILE, message, level)
    else:
        # Fallback to print if LOG_FILE isn't set yet
        print(message)

def load_config(json_path: Path):
    if not json_path.exists():
        return None
    try:
        return json.loads(json_path.read_text())
    except Exception as e:
        log(f"[Supervisor] Error loading config: {e}", "ERROR")
        return None

def get_seconds_until(target_time_str):
    """Calculates seconds from now until the next occurrence of HH:MM."""
    now = get_now()
    target_time = datetime.strptime(target_time_str, "%H:%M").time()
    target_dt = now.replace(hour=target_time.hour, minute=target_time.minute, second=0, microsecond=0)
    
    if target_dt <= now:
        target_dt += timedelta(days=1)
        
    return (target_dt - now).total_seconds()

def is_within_window(start_str, end_str):
    """Checks if current time is between start and end."""
    now = get_now().time()
    start = datetime.strptime(start_str, "%H:%M").time()
    end = datetime.strptime(end_str, "%H:%M").time()
    
    if start <= end:
        return start <= now <= end
    else:
        return start <= now or now <= end

def run_module_task(run_file_path, module_root):
    """Executes the actual module script."""
    log(f"[Supervisor] Starting task: {run_file_path.name}")
    project_root = Path.cwd() 
    
    # Force module_root to be the module dir so it can find local modules
    cmd = [sys.executable, "-m", f"modules.{module_root.name}.{run_file_path.stem}"]
    
    try:
        subprocess.run(cmd, cwd=project_root, check=True)
        log(f"[Supervisor] Task finished: {run_file_path.name}")
    except subprocess.CalledProcessError as e:
        log(f"[Supervisor] Task crashed with code {e.returncode}", "ERROR")
    except Exception as e:
        log(f"[Supervisor] Failed to run task: {e}", "ERROR")

def main():
    global LOG_FILE
    if len(sys.argv) < 2:
        print("Usage: python supervisor.py <module_name>")
        return

    module_name = sys.argv[1]
    project_root = Path.cwd()
    module_dir = project_root / "modules" / module_name
    config_path = module_dir / "module.json"

    # Set the log file path from config
    config = load_config(config_path)
    if config:
        log_rel_path = config.get("log_file", "logs/runtime.log")
        LOG_FILE = module_dir / log_rel_path
        manage_log_size(LOG_FILE)

    log(f"[Supervisor] Started for {module_name}")

    while True:
        config = load_config(config_path)
        if not config:
            log("[Supervisor] Config missing. Sleeping 10s...", "WARN")
            time.sleep(10)
            continue

        run_options = config.get("run_options", {})
        if not run_options.get("on", False):
            log("[Supervisor] Module is turned OFF. Sleeping 5s...")
            time.sleep(5)
            continue

        mode = run_options.get("mode", "finite")
        run_file = config.get("run_file")
        if not run_file:
            log("[Supervisor] No run_file defined. stopping.", "ERROR")
            break
            
        full_run_path = module_dir / run_file

        if mode == "finite":
            run_module_task(full_run_path, module_dir)
            log("[Supervisor] Finite run complete. Exiting supervisor.")
            config["run_options"]["on"] = False
            config_path.write_text(json.dumps(config, indent=4))
            break

        elif mode == "indefinite":
            start_str = run_options.get("start_time", "00:00")
            end_str = run_options.get("end_time", "23:59")
            runs_per_day = int(run_options.get("runs_per_day", 1))

            if is_within_window(start_str, end_str):
                start_dt = datetime.strptime(start_str, "%H:%M")
                end_dt = datetime.strptime(end_str, "%H:%M")
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                
                total_window_seconds = (end_dt - start_dt).total_seconds()
                interval_seconds = total_window_seconds / max(runs_per_day, 1)

                run_module_task(full_run_path, module_dir)
                
                log(f"[Supervisor] Task done. Sleeping for {interval_seconds/60:.1f} minutes...")
                time.sleep(interval_seconds)
            else:
                wait_sec = get_seconds_until(start_str)
                log(f"[Supervisor] Outside window ({start_str}-{end_str}). Sleeping {wait_sec/60:.1f} minutes until start.")
                sleep_chunk = 10
                while wait_sec > 0:
                    temp_conf = load_config(config_path)
                    if not temp_conf or not temp_conf.get("run_options", {}).get("on", False):
                        break 
                    
                    to_sleep = min(wait_sec, sleep_chunk)
                    time.sleep(to_sleep)
                    wait_sec -= to_sleep

if __name__ == "__main__":
    main()
