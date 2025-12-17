from flask import Flask, render_template, abort
from flask_socketio import SocketIO
from pathlib import Path
import json
from utilities.flask_modules import get_modules, load_stats, push_stats
from utilities.flask_log_socket import register_log_sockets

app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet")

MODULES_DIR = Path("leam_modules")
STATS_FILE = Path("data/system_stats.json")

# Register log-related SocketIO events
register_log_sockets(socketio, MODULES_DIR)

# Routes
@app.route("/")
def index():
    return render_template("index.html", current_page="Home", modules=get_modules(MODULES_DIR))

@app.route("/settings")
def settings():
    return render_template("settings.html", current_page="Settings")

@app.route("/modules/<module_name>")
def module_page(module_name):
    module_path = MODULES_DIR / module_name
    module_json = module_path / "module.json"

    if not module_path.exists() or not module_json.exists():
        abort(404)

    module_data = module_json.read_text()
    return render_template(
        "components/modules/module_page.html",
        current_page=module_name,
        module_name=module_name,
        module=json.loads(module_data)
    )

# SocketIO System Stats
@socketio.on("connect")
def on_connect():
    print("Client connected")
    socketio.start_background_task(push_stats, socketio, STATS_FILE)

if __name__ == "__main__":
    socketio.run(app, port=5000, debug=True)