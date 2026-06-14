import json
from pathlib import Path
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

GLOBAL_SETTINGS_PATH = Path("data/settings.json")

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

def get_global_settings():
    """Load global settings from data/settings.json."""
    if not GLOBAL_SETTINGS_PATH.exists():
        return {"timezone": "UTC"}
    try:
        return json.loads(GLOBAL_SETTINGS_PATH.read_text())
    except Exception:
        return {"timezone": "UTC"}

def save_global_settings(settings):
    """Save global settings to data/settings.json."""
    GLOBAL_SETTINGS_PATH.parent.mkdir(exist_ok=True)
    GLOBAL_SETTINGS_PATH.write_text(json.dumps(settings, indent=4))

def get_now():
    """Get current datetime in the configured global timezone."""
    settings = get_global_settings()
    tz_name = settings.get("timezone", "UTC")
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now(ZoneInfo("UTC"))
