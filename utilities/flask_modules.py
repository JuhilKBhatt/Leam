import json
from pathlib import Path

def get_modules(modules_dir: Path):
    """Return a list of all available modules with basic info."""
    modules = []
    for folder in modules_dir.iterdir():
        if folder.is_dir():
            desc_file = folder / "module.json"
            desc = {}
            if desc_file.exists():
                desc = json.loads(desc_file.read_text())
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
    return json.loads(stats_file.read_text())

def push_stats(socketio, stats_file: Path):
    """Emit system stats every second."""
    while True:
        socketio.emit("stats", load_stats(stats_file))
        socketio.sleep(1)