import os
import json
import socket
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / "secrets" / ".env")

TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "leam_parameters")

# Known mapping between DynamoDB parameter_name and local data files
DATA_FILE_MAP = {
    "tts_quota": project_root / "data" / "tts_quota.json",
    "pexels_quota": project_root / "data" / "pexels_quota.json",
    "reddit_quota": project_root / "data" / "reddit_quota.json",
    "google_search_quota": project_root / "data" / "google_search_quota.json",
    "global_settings": project_root / "data" / "settings.json",
    "sp500": project_root / "data" / "sp500.json",
}

def _to_decimal(obj):
    """Recursively converts floats to Decimals for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_to_decimal(v) for v in obj]
    return obj

def _from_decimal(obj):
    """Recursively converts Decimals back to int or float for Python standard JSON."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: _from_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_from_decimal(v) for v in obj]
    return obj

def get_dynamo_table():
    """
    Instantiates and returns the DynamoDB Table resource using credentials in secrets/.env.
    Returns None if AWS credentials are not configured or connection fails.
    """
    load_dotenv(project_root / "secrets" / ".env", override=False)
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION", "ap-southeast-2")

    if not aws_access_key or not aws_secret_key:
        return None

    try:
        session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region_name
        )
        dynamodb = session.resource("dynamodb")
        return dynamodb.Table(TABLE_NAME)
    except Exception as e:
        print(f"[DynamoDB] Warning: Could not initialize DynamoDB table '{TABLE_NAME}': {e}")
        return None

def get_parameter(parameter_name: str, default=None):
    """
    Retrieves a parameter item from DynamoDB by parameter_name partition key.
    Returns the parsed Python data structure, or default if missing or on failure.
    """
    table = get_dynamo_table()
    if table is None:
        return default

    try:
        resp = table.get_item(Key={"parameter_name": parameter_name})
        item = resp.get("Item")
        if not item:
            return default

        # Prefer deserializing data_json if present for pure JSON fidelity
        if "data_json" in item and item["data_json"]:
            try:
                return json.loads(item["data_json"])
            except Exception:
                pass

        if "data" in item:
            return _from_decimal(item["data"])

        return default
    except (BotoCoreError, ClientError) as e:
        print(f"[DynamoDB] Warning: Failed to get parameter '{parameter_name}': {e}")
        return default

def put_parameter(parameter_name: str, data: Any) -> bool:
    """
    Saves or updates a parameter item in DynamoDB under parameter_name.
    Stores both native DynamoDB Map (with Decimals) and serialized data_json string.
    """
    table = get_dynamo_table()
    if table is None:
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    hostname = socket.gethostname()

    try:
        data_json = json.dumps(data)
        dynamo_data = _to_decimal(data)

        item = {
            "parameter_name": parameter_name,
            "data": dynamo_data,
            "data_json": data_json,
            "updated_at": now_iso,
            "source_host": hostname
        }
        table.put_item(Item=item)
        return True
    except (BotoCoreError, ClientError, Exception) as e:
        print(f"[DynamoDB] Warning: Failed to put parameter '{parameter_name}': {e}")
        return False

def delete_parameter(parameter_name: str) -> bool:
    """Deletes a parameter from DynamoDB."""
    table = get_dynamo_table()
    if table is None:
        return False

    try:
        table.delete_item(Key={"parameter_name": parameter_name})
        return True
    except (BotoCoreError, ClientError) as e:
        print(f"[DynamoDB] Warning: Failed to delete parameter '{parameter_name}': {e}")
        return False

def list_parameters() -> list[dict]:
    """Scans and returns summary of all parameters in DynamoDB."""
    table = get_dynamo_table()
    if table is None:
        return []

    try:
        resp = table.scan(
            ProjectionExpression="parameter_name, updated_at, source_host"
        )
        return resp.get("Items", [])
    except Exception as e:
        print(f"[DynamoDB] Warning: Could not list parameters: {e}")
        return []

# --- High-level Batch Synchronization ---

def sync_all_push() -> dict[str, bool]:
    """
    Pushes all local API data files and module configurations to DynamoDB.
    Returns a dict mapping parameter_name -> success_boolean.
    """
    results = {}
    print(f"[DynamoDB Sync] Pushing local parameters to AWS DynamoDB ({TABLE_NAME})...")

    # 1. Push data/*.json files
    for param_name, file_path in DATA_FILE_MAP.items():
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    content = json.load(f)
                ok = put_parameter(param_name, content)
                results[param_name] = ok
                print(f"  ✓ Pushed {param_name} ({file_path.name}) -> {'OK' if ok else 'FAILED'}")
            except Exception as e:
                print(f"  ✗ Error reading {file_path}: {e}")
                results[param_name] = False

    # 2. Push module configurations
    modules_dir = project_root / "modules"
    if modules_dir.exists():
        for mod_dir in modules_dir.iterdir():
            if mod_dir.is_dir() and not mod_dir.name.startswith((".", "_")):
                local_file = mod_dir / "module.local.json"
                base_file = mod_dir / "module.json"
                param_name = f"module_config_{mod_dir.name}"

                payload = {}
                if base_file.exists():
                    try:
                        with open(base_file, "r") as f:
                            payload["base"] = json.load(f)
                    except Exception:
                        pass
                if local_file.exists():
                    try:
                        with open(local_file, "r") as f:
                            payload["local"] = json.load(f)
                    except Exception:
                        pass

                if payload:
                    ok = put_parameter(param_name, payload)
                    results[param_name] = ok
                    print(f"  ✓ Pushed {param_name} -> {'OK' if ok else 'FAILED'}")

    return results

def sync_all_pull() -> dict[str, bool]:
    """
    Pulls all parameters from DynamoDB and updates local data files and module configs.
    Returns a dict mapping parameter_name -> success_boolean.
    """
    results = {}
    print(f"[DynamoDB Sync] Pulling parameters from AWS DynamoDB ({TABLE_NAME}) to local disk...")

    # 1. Pull data/*.json files
    for param_name, file_path in DATA_FILE_MAP.items():
        val = get_parameter(param_name)
        if val is not None:
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w") as f:
                    json.dump(val, f, indent=2)
                results[param_name] = True
                print(f"  ✓ Pulled {param_name} -> {file_path.name}")
            except Exception as e:
                print(f"  ✗ Error writing to {file_path}: {e}")
                results[param_name] = False
        else:
            print(f"  - {param_name} not found in DynamoDB. Skipping local update.")

    # 2. Pull module configs
    modules_dir = project_root / "modules"
    if modules_dir.exists():
        for mod_dir in modules_dir.iterdir():
            if mod_dir.is_dir() and not mod_dir.name.startswith((".", "_")):
                param_name = f"module_config_{mod_dir.name}"
                val = get_parameter(param_name)
                if val and isinstance(val, dict):
                    local_payload = val.get("local")
                    if local_payload:
                        local_file = mod_dir / "module.local.json"
                        try:
                            with open(local_file, "w") as f:
                                json.dump(local_payload, f, indent=4)
                            results[param_name] = True
                            print(f"  ✓ Pulled {param_name} -> {local_file.name}")
                        except Exception as e:
                            print(f"  ✗ Error writing {local_file}: {e}")
                            results[param_name] = False

    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Leam AWS DynamoDB Parameters Synchronizer")
    parser.add_argument("--push", action="store_true", help="Push local data files and module configs to DynamoDB")
    parser.add_argument("--pull", action="store_true", help="Pull DynamoDB parameters to local data files and module configs")
    parser.add_argument("--status", action="store_true", help="List all parameters stored in DynamoDB")
    args = parser.parse_args()

    if args.push:
        sync_all_push()
    elif args.pull:
        sync_all_pull()
    elif args.status:
        items = list_parameters()
        print(f"\n[DynamoDB Table: {TABLE_NAME}] ({len(items)} parameters found)")
        for it in sorted(items, key=lambda x: x.get("parameter_name", "")):
            print(f"  • {it.get('parameter_name'):<30} (Updated: {it.get('updated_at', 'N/A')} by {it.get('source_host', 'N/A')})")
    else:
        parser.print_help()
