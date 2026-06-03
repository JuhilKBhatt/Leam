import json
from pathlib import Path

def safe_filename(text: str, max_length: int = 50) -> str:
    """Remove bad filename characters and shorten."""
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in text)[:max_length]

def load_config(config_path="config.json"):
    path = Path(config_path)
    if not path.exists():
        return None
    with open(path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None

def update_config(data, config_path="config.json"):
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=4)
