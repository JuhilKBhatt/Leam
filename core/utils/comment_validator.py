
# utilities/comment_validator.py
import json
import os

HISTORY_FILE = "secrets/comment_history.json"

def load_history():
    """Loads comment history from JSON."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_history(history: dict):
    """Saves comment history to JSON."""
    os.makedirs("secrets", exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def has_commented(video_id: str) -> bool:
    """Checks if we've already commented on this video."""
    history = load_history()
    return video_id in history

def record_comment(video_id: str, comment_id: str):
    """Stores metadata about a posted comment."""
    history = load_history()
    history[video_id] = {
        "comment_id": comment_id,
        "video_id": video_id,
    }
    save_history(history)