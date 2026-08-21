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

def load_module_config(module_dir: Path):
    """Loads module.json and overlays module.local.json if it exists."""
    base_path = module_dir / "module.json"
    local_path = module_dir / "module.local.json"
    
    if not base_path.exists():
        return {}
        
    try:
        config = json.loads(base_path.read_text())
    except Exception:
        config = {}
        
    if local_path.exists():
        try:
            local_config = json.loads(local_path.read_text())
            if "settings" in local_config:
                config.setdefault("settings", {}).update(local_config["settings"])
            if "run_options" in local_config:
                config.setdefault("run_options", {}).update(local_config["run_options"])
        except Exception:
            pass
            
    return config

def save_module_config(module_dir: Path, config_data: dict):
    """Saves settings and run_options from config_data to module.local.json."""
    local_path = module_dir / "module.local.json"
    local_config = {}
    if local_path.exists():
        try:
            local_config = json.loads(local_path.read_text())
        except Exception:
            pass
            
    if "settings" in config_data:
        local_config["settings"] = config_data["settings"]
    if "run_options" in config_data:
        local_config["run_options"] = config_data["run_options"]
        
    local_path.write_text(json.dumps(local_config, indent=4))
