import os
import time
import json
import praw
from pathlib import Path
from dotenv import load_dotenv
from core.utils.common import get_now

project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / "secrets" / ".env")

REDDIT_QUOTA_FILE = project_root / "data" / "reddit_quota.json"

def get_reddit_credentials() -> dict:
    """Retrieves Reddit OAuth credentials from environment."""
    return {
        "client_id": os.getenv("REDDIT_CLIENT_ID"),
        "client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
        "user_agent": os.getenv("REDDIT_USER_AGENT", "Leam by u/J-Bhatt")
    }

def get_reddit_client() -> praw.Reddit:
    """Instantiates and returns an authenticated PRAW Reddit instance."""
    creds = get_reddit_credentials()
    if not creds["client_id"] or not creds["client_secret"]:
        raise ValueError("Missing Reddit API credentials in secrets/.env")

    return praw.Reddit(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        user_agent=creds["user_agent"]
    )

def load_reddit_quota_data() -> dict:
    """Loads raw Reddit quota telemetry from DynamoDB or disk fallback."""
    try:
        from core.utils.dynamodb_sync import get_parameter
        remote_data = get_parameter("reddit_quota")
        if remote_data and isinstance(remote_data, dict):
            return remote_data
    except Exception:
        pass

    if not REDDIT_QUOTA_FILE.exists():
        return {}
    try:
        with open(REDDIT_QUOTA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_reddit_quota_data(data: dict):
    """Saves Reddit quota telemetry to DynamoDB, falling back to disk on failure."""
    synced = False
    try:
        from core.utils.dynamodb_sync import put_parameter
        synced = put_parameter("reddit_quota", data)
    except Exception as e:
        print(f"[Reddit] Warning: Could not sync quota to DynamoDB: {e}")

    if not synced:
        try:
            REDDIT_QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(REDDIT_QUOTA_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Reddit] Warning: Could not save quota data locally: {e}")

def get_reddit_quota_status() -> dict:
    """
    Returns current Reddit API quota metrics for the 100 QPM limit and monthly totals,
    pruning timestamps older than 60 seconds and resetting monthly counts if a new month began.
    """
    now_ts = time.time()
    current_month = get_now().strftime("%Y-%m")
    data = load_reddit_quota_data()
    needs_save = False

    # 1. Monthly Reset check
    stored_month = data.get("month")
    if stored_month != current_month:
        data["month"] = current_month
        data["monthly_used"] = 0
        data["modules"] = {}
        needs_save = True

    # 2. Sliding 60-second window (Queries Per Minute)
    recent_ts = data.get("recent_timestamps", [])
    sixty_secs_ago = now_ts - 60
    pruned_ts = [ts for ts in recent_ts if ts >= sixty_secs_ago]
    if len(pruned_ts) != len(recent_ts):
        data["recent_timestamps"] = pruned_ts
        needs_save = True

    qpm_used = len(pruned_ts)
    monthly_used = data.get("monthly_used", 0)
    modules_usage = data.get("modules", {})

    # Discover any active modules
    modules_dir = project_root / "modules"
    if modules_dir.exists():
        for mod_dir in modules_dir.iterdir():
            if mod_dir.is_dir() and not mod_dir.name.startswith((".", "_")):
                if mod_dir.name not in modules_usage:
                    modules_usage[mod_dir.name] = 0
                    needs_save = True

    # Calculate seconds until the oldest request in the current 60s window rolls off
    resets_in_seconds = 0
    if pruned_ts:
        oldest_ts = min(pruned_ts)
        resets_in_seconds = max(0, int(60 - (now_ts - oldest_ts)))

    qpm_limit = data["qpm_limit"]

    status = {
        "month": current_month,
        "qpm": {
            "limit": qpm_limit,
            "used": qpm_used,
            "remaining": max(0, qpm_limit - qpm_used),
            "percent_used": round((qpm_used / qpm_limit) * 100, 2) if qpm_limit > 0 else 0,
            "resets_in_seconds": resets_in_seconds
        },
        "monthly": {
            "used": monthly_used
        },
        "modules": modules_usage,
        "upstream": {
            "remaining": data.get("upstream_remaining"),
            "reset_timestamp": data.get("upstream_reset_timestamp")
        },
        "last_updated": get_now().isoformat()
    }

    if needs_save:
        data["qpm_used"] = qpm_used
        data["monthly_used"] = monthly_used
        data["modules"] = modules_usage
        data["last_updated"] = status["last_updated"]
        save_reddit_quota_data(data)

    return status

def record_reddit_query(module_name: str, count: int = 1, client: praw.Reddit | None = None):
    """
    Records an outgoing query against the 60s QPM sliding window and monthly counter,
    attributing it to the requesting module and synchronizing PRAW internal rate limit state.
    """
    now_ts = time.time()
    current_month = get_now().strftime("%Y-%m")
    data = load_reddit_quota_data()

    if data.get("month") != current_month:
        data["month"] = current_month
        data["monthly_used"] = 0
        data["modules"] = {}

    # Update rolling 60s timestamps
    recent_ts = [ts for ts in data.get("recent_timestamps", []) if ts >= (now_ts - 60)]
    for _ in range(count):
        recent_ts.append(now_ts)
    data["recent_timestamps"] = recent_ts
    data["qpm_used"] = len(recent_ts)

    # Update monthly total
    data["monthly_used"] = data.get("monthly_used", 0) + count

    # Update per-module breakdown
    modules = data.setdefault("modules", {})
    modules[module_name] = modules.get(module_name, 0) + count

    # Sync upstream PRAW rate limiter state if client available
    if client and hasattr(client, "_core") and hasattr(client._core, "_rate_limiter"):
        rl = client._core._rate_limiter
        remaining = getattr(rl, "remaining", None)
        reset_ts = getattr(rl, "reset_timestamp", None)
        if remaining is not None:
            data["upstream_remaining"] = float(remaining)
        if reset_ts is not None:
            data["upstream_reset_timestamp"] = float(reset_ts)

    data["last_updated"] = get_now().isoformat()
    save_reddit_quota_data(data)

def ensure_qpm_budget(module_name: str = "reddit_story", count: int = 1):
    """
    Checks the rolling 60s QPM window. If budget is exceeded (or near limit),
    waits for the window to clear rather than causing an HTTP 429 error.
    """
    status = get_reddit_quota_status()
    limit = status["qpm"]["limit"]
    remaining = status["qpm"]["remaining"]

    if remaining < count:
        wait_time = status["qpm"]["resets_in_seconds"] or 1
        print(f"⏳ [Reddit] {limit} QPM rate limit reached. Pausing for {wait_time}s to reset rolling window...")
        time.sleep(wait_time + 0.5)
