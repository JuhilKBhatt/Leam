# ./utilities/config_loader.py
import json
from pathlib import Path

def load_config(config_path="config.json"):
    path = Path(config_path)
    if not path.exists():
        return None
        
    with open(path, 'r') as f:
        data = json.load(f)
    
    # Optional: Logic to strip the "-stringME" etc. suffixes for easier use
    return data

def update_config(data, config_path="config.json"):
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=4)