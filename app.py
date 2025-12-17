from flask import Flask, render_template, abort
from flask_socketio import SocketIO
import json
from pathlib import Path

app = Flask(__name__)

socketio = SocketIO(app, async_mode="eventlet")

STATS_FILE = Path("data/system_stats.json")
MODULES_DIR = Path("leam_modules")

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
        module_name=module_name,
        module=module_data
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