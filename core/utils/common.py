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
    """Load global settings from DynamoDB or data/settings.json fallback."""
    try:
        from core.utils.dynamodb_sync import get_parameter
        remote = get_parameter("global_settings")
        if remote and isinstance(remote, dict):
            return remote
    except Exception:
        pass

    if not GLOBAL_SETTINGS_PATH.exists():
        return {"timezone": "UTC"}
    try:
        return json.loads(GLOBAL_SETTINGS_PATH.read_text())
    except Exception:
        return {"timezone": "UTC"}

def save_global_settings(settings):
    """Save global settings to DynamoDB, falling back to data/settings.json on failure."""
    synced = False
    try:
        from core.utils.dynamodb_sync import put_parameter
        synced = put_parameter("global_settings", settings)
    except Exception as e:
        print(f"[Settings] Warning: Could not sync global settings to DynamoDB: {e}")

    if not synced:
        try:
            GLOBAL_SETTINGS_PATH.parent.mkdir(exist_ok=True)
            GLOBAL_SETTINGS_PATH.write_text(json.dumps(settings, indent=4))
        except Exception as e:
            print(f"[Settings] Warning: Could not save settings locally: {e}")

def get_now():
    """Get current datetime in the configured global timezone."""
    settings = get_global_settings()
    tz_name = settings.get("timezone", "UTC")
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now(ZoneInfo("UTC"))

def load_module_config(module_dir: Path):
    """Loads module.json and overlays module.local.json or DynamoDB configuration if available."""
    base_path = module_dir / "module.json"
    local_path = module_dir / "module.local.json"
    mod_name = module_dir.name
    
    if not base_path.exists():
        return {}
        
    try:
        config = json.loads(base_path.read_text())
    except Exception:
        config = {}

    local_config = None
    try:
        from core.utils.dynamodb_sync import get_parameter
        param_val = get_parameter(f"module_config_{mod_name}")
        if param_val and isinstance(param_val, dict):
            remote_local = param_val.get("local")
            if remote_local and isinstance(remote_local, dict):
                local_config = remote_local
                try:
                    local_path.write_text(json.dumps(local_config, indent=4))
                except Exception:
                    pass
    except Exception:
        pass

    if local_config is None and local_path.exists():
        try:
            local_config = json.loads(local_path.read_text())
        except Exception:
            pass

    if local_config:
        if "settings" in local_config:
            config.setdefault("settings", {}).update(local_config["settings"])
        if "run_options" in local_config:
            config.setdefault("run_options", {}).update(local_config["run_options"])
            
    return config

def save_module_config(module_dir: Path, config_data: dict):
    """Saves settings and run_options from config_data to module.local.json and syncs to DynamoDB."""
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

    try:
        from core.utils.dynamodb_sync import put_parameter
        base_path = module_dir / "module.json"
        base_payload = {}
        if base_path.exists():
            try:
                base_payload = json.loads(base_path.read_text())
            except Exception:
                pass
        put_parameter(f"module_config_{module_dir.name}", {
            "base": base_payload,
            "local": local_config
        })
    except Exception as e:
        print(f"[Config] Warning: Could not sync module config to DynamoDB: {e}")
