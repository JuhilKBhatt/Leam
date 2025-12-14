from flask import Flask, render_template
from flask_socketio import SocketIO
import json
from pathlib import Path

app = Flask(__name__)

socketio = SocketIO(app, async_mode="eventlet")

STATS_FILE = Path("data/system_stats.json")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/settings")
def settings():
    return render_template("settings.html", current_page="Settings")

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