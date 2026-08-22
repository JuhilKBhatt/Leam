# ./app.py
from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, abort
from flask_socketio import SocketIO
from pathlib import Path
import json

from web.manager import get_modules, load_stats, push_stats
from web.sockets.logging import register_log_sockets
from web.sockets.runner import register_module_run
from web.sockets.settings import register_settings_socket

app = Flask(__name__)
socketio = SocketIO(app, async_mode="gevent")

MODULES_DIR = Path("modules")
STATS_FILE = Path("data/system_stats.json")

# Register log related SocketIO events
register_log_sockets(socketio, MODULES_DIR)
register_module_run(socketio, MODULES_DIR)
register_settings_socket(socketio, MODULES_DIR)

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
    from core.utils.common import load_module_config
    from core.api.google import get_yt_channels
    module_data = load_module_config(module_path)

    if not module_data:
        abort(404)

    return render_template(
        "components/modules/module_page.html",
        current_page=module_name,
        module_name=module_name,
        module=module_data,
        yt_channels=get_yt_channels()
    )

# YouTube Auth Endpoints
from flask import request

@app.route("/api/youtube/channels", methods=["GET"])
def yt_channels_list():
    from core.api.google import get_yt_channels
    return {"channels": get_yt_channels()}

@app.route("/api/youtube/channels/<channel_name>", methods=["DELETE"])
def yt_channel_delete(channel_name):
    from core.api.google import delete_yt_channel
    success = delete_yt_channel(channel_name)
    return {"success": success}

@app.route("/api/youtube/channels/<old_name>", methods=["PUT"])
def yt_channel_rename(old_name):
    from core.api.google import rename_yt_channel
    new_name = request.json.get("new_name")
    success = rename_yt_channel(old_name, new_name)
    return {"success": success}

@app.route("/api/youtube/auth_start", methods=["POST"])
def yt_auth_start():
    channel_name = request.json.get("channel_name", "Default")
    import threading
    from core.api.google import get_youtube_service
    # Run in background to prevent blocking the web worker
    threading.Thread(target=get_youtube_service, args=(channel_name,)).start()
    return {"status": "started"}

@app.route("/api/youtube/auth_poll")
def yt_auth_poll():
    url_file = Path("secrets/auth_url.txt")
    if url_file.exists():
        with open(url_file, "r") as f:
            url = f.read().strip()
        url_file.unlink()
        return {"url": url}
    return {"url": None}

@app.route("/api/youtube/auth_code", methods=["POST"])
def yt_auth_code():
    code = request.json.get("code")
    with open("secrets/auth_code.txt", "w") as f:
        f.write(code)
    return {"status": "success"}

# SocketIO System Stats
@socketio.on("connect")
def on_connect():
    socketio.start_background_task(push_stats, socketio, STATS_FILE)

if __name__ == "__main__":
    from core.engine.gpu import detect_gpu_backend
    detect_gpu_backend() # Probe GPU at startup

    
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)
