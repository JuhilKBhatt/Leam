from flask import Flask, render_template, abort
from flask_socketio import SocketIO
import json
from pathlib import Path
import time
from threading import Lock

app = Flask(__name__)

socketio = SocketIO(app, async_mode="eventlet")

STATS_FILE = Path("data/system_stats.json")
MODULES_DIR = Path("leam_modules")
log_threads = {}
log_thread_lock = Lock()

def get_modules():
    modules = []
    for folder in MODULES_DIR.iterdir():
        if folder.is_dir():
            desc_file = folder / "module.json"
            desc = {}
            if desc_file.exists():
                with open(desc_file) as f:
                    desc = json.load(f)

            modules.append({
                "module_name": desc.get("name", folder.name),
                "module_desc": desc.get("description", "No description available"),
                "module_link": f"/modules/{folder.name}",
                "run_file": desc.get("run_file")
            })
    print(modules)
    return modules

def tail_log(module_name, log_path):
    """Continuously emits new log lines for a module"""
    with open(log_path, "r") as f:
        f.seek(0, 2)  # go to end of file

        while True:
            line = f.readline()
            if line:
                socketio.emit(
                    "module_log",
                    {"module": module_name, "line": line.rstrip()}
                )
            else:
                socketio.sleep(0.5)

@app.route("/")
def index():
    return render_template(
        "index.html",
        current_page="Home",
        modules=get_modules()
    )

@app.route("/settings")
def settings():
    return render_template("settings.html", current_page="Settings")

@app.route("/modules/<module_name>")
def module_page(module_name):
    module_path = MODULES_DIR / module_name

    if not module_path.exists():
        abort(404)

    module_json = module_path / "module.json"
    if not module_json.exists():
        abort(404)

    module_data = json.loads(module_json.read_text())

    return render_template(
        "components/modules/module_page.html",
        current_page=module_data.get("name", module_name),
        module_name=module_name,
        module=module_data
    )

@socketio.on("subscribe_logs")
def subscribe_logs(data):
    module_name = data.get("module")

    module_path = MODULES_DIR / module_name
    module_json = module_path / "module.json"

    if not module_json.exists():
        return

    module_data = json.loads(module_json.read_text())
    log_rel_path = module_data.get("log_file")

    if not log_rel_path:
        return

    log_path = module_path / log_rel_path
    log_path.parent.mkdir(exist_ok=True)
    log_path.touch(exist_ok=True)

    with log_thread_lock:
        if module_name not in log_threads:
            log_threads[module_name] = socketio.start_background_task(
                tail_log, module_name, log_path
            )

def load_stats():
    if not STATS_FILE.exists():
        return {}
    return json.loads(STATS_FILE.read_text())

def push_stats():
    while True:
        socketio.emit("stats", load_stats())
        socketio.sleep(1)

@socketio.on("connect")
def on_connect():
    socketio.start_background_task(push_stats)

if __name__ == "__main__":
    socketio.run(app, port=5000, debug=True)