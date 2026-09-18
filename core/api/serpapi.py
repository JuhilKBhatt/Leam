import os
import requests
import json
import re
import time
from datetime import date, timedelta
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / "secrets" / ".env")

QUOTA_FILE = project_root / "data" / "google_search_quota.json"


def get_current_billing_cycle_start(reset_day: int, today: date | None = None) -> date:
    """
    Given a reset day of the month (e.g. 23 or 17), calculates the date
    when the current billing cycle started.
    """
    if today is None:
        today = date.today()

    if today.day >= reset_day:
        return today.replace(day=reset_day)
    else:
        first_of_this_month = today.replace(day=1)
        last_day_prev_month = first_of_this_month - timedelta(days=1)
        clamped_day = min(reset_day, last_day_prev_month.day)
        return last_day_prev_month.replace(day=clamped_day)

def get_next_reset_date(reset_day: int, today: date | None = None) -> date:
    """Calculates the upcoming reset date for the next billing cycle."""
    start = get_current_billing_cycle_start(reset_day, today)
    first_next = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_day = (first_next.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return first_next.replace(day=min(reset_day, last_day.day))

def load_quota_data() -> dict:
    try:
        from core.utils.dynamodb_sync import get_parameter
        remote_data = get_parameter("google_search_quota")
        if remote_data and isinstance(remote_data, dict):
            return remote_data
    except Exception:
        pass

    if not QUOTA_FILE.exists():
        return {}
    try:
        with open(QUOTA_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_quota_data(data: dict):
    synced = False
    try:
        from core.utils.dynamodb_sync import put_parameter
        synced = put_parameter("google_search_quota", data)
    except Exception as e:
        print(f"[SerpApi] Warning: Could not sync quota to DynamoDB: {e}")

    if not synced:
        try:
            QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(QUOTA_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SerpApi] Warning: Could not save quota data locally: {e}")

def get_key_quota_status(key_name: str, api_key: str, reset_day: int, limit: int) -> dict:
    """
    Returns the quota tracking dict for a given key, resetting usage if
    the billing cycle reset day has passed. Syncs initial count from SerpApi if needed.
    """
    cycle_start = get_current_billing_cycle_start(reset_day).isoformat()
    next_reset = get_next_reset_date(reset_day).isoformat()

    quota_data = load_quota_data()
    key_data = quota_data.get(key_name)
    needs_save = False

    if not isinstance(key_data, dict) or key_data.get("cycle_start") != cycle_start:
        key_data = {
            "cycle_start": cycle_start,
            "count": 0,
            "limit": limit,
            "reset_day": reset_day,
            "next_reset": next_reset
        }
        quota_data[key_name] = key_data
        needs_save = True

    # If count is 0 or unverified, try a lightweight check against SerpApi account endpoint
    if key_data.get("count") == 0:
        try:
            r = requests.get(f"https://serpapi.com/account?api_key={api_key}", timeout=4)
            if r.status_code == 200:
                acc_info = r.json()
                usage = acc_info.get("this_month_usage")
                if usage is not None and usage > key_data["count"]:
                    key_data["count"] = usage
                    quota_data[key_name] = key_data
                    needs_save = True
        except Exception:
            pass

    if needs_save:
        save_quota_data(quota_data)

    return key_data

def record_key_usage(key_name: str, count_increment: int = 1):
    """Increments request count for the key in google_search_quota.json."""
    quota_data = load_quota_data()
    key_data = quota_data.get(key_name, {})
    new_count = key_data.get("count", 0) + count_increment
    key_data["count"] = new_count
    quota_data[key_name] = key_data
    save_quota_data(quota_data)

def get_configured_keys() -> list[dict]:
    """
    Returns an ordered list of configured SerpApi keys with quota configuration
    loaded from environment variables and data/google_search_quota.json.
    """
    load_dotenv(project_root / "secrets" / ".env", override=False)
    quota_data = load_quota_data()
    keys = []
    seen = set()

    i = 1
    while True:
        k_name = f"SERPAPI_KEY_{i}"
        val = os.getenv(k_name)
        if val and val.strip():
            val = val.strip()
            cfg = quota_data.get(k_name, {}) if isinstance(quota_data.get(k_name), dict) else {}
            keys.append({
                "name": k_name,
                "key": val,
                "reset_day": cfg.get("reset_day", 1),
                "limit": cfg.get("limit", 250)
            })
            seen.add(val)
            i += 1
        else:
            break

    val = os.getenv("SERPAPI_KEY")
    if val and val.strip() and val.strip() not in seen:
        val = val.strip()
        cfg = quota_data.get("SERPAPI_KEY", {}) if isinstance(quota_data.get("SERPAPI_KEY"), dict) else {}
        keys.append({
            "name": "SERPAPI_KEY",
            "key": val,
            "reset_day": cfg.get("reset_day", 1),
            "limit": cfg.get("limit", 250)
        })
        seen.add(val)

    for env_k, env_v in os.environ.items():
        if env_k.startswith("SERPAPI_KEY_") and env_v and env_v.strip() not in seen:
            cfg = quota_data.get(env_k, {}) if isinstance(quota_data.get(env_k), dict) else {}
            keys.append({
                "name": env_k,
                "key": env_v.strip(),
                "reset_day": cfg.get("reset_day", 1),
                "limit": cfg.get("limit", 250)
            })
            seen.add(env_v.strip())

    return keys

def get_serpapi_keys() -> list[str]:
    """Returns an ordered list of configured SerpApi key strings."""
    return [k["key"] for k in get_configured_keys()]

def get_serpapi_key() -> str | None:
    """Returns the primary SerpApi key or None if not configured."""
    keys = get_serpapi_keys()
    return keys[0] if keys else None

SERPAPI_KEY = get_serpapi_key()

def get_google_image_from_serpapi(query: str, download_dir: str, num_images: int = 1) -> str | list[str]:
    """
    Searches for an image using SerpApi and downloads the first result (or up to `num_images`).
    Returns the path to the downloaded image, or a list of paths if num_images > 1.
    
    Tracks monthly quota per key with billing cycle reset dates from quota tracking.
    Automatically falls back to the other key on quota exhaustion OR any errors.
    """
    key_objs = get_configured_keys()
    if not key_objs:
        raise ValueError("No SerpApi keys found in environment variables.")

    url = "https://serpapi.com/search"
    print(f"[SerpApi] Searching for: '{query}' (need {num_images}, {len(key_objs)} key(s) configured)")

    data = None

    for key_idx, key_info in enumerate(key_objs):
        key_name = key_info["name"]
        api_key = key_info["key"]
        reset_day = key_info["reset_day"]
        limit = key_info["limit"]

        # Check local cycle quota
        status = get_key_quota_status(key_name, api_key, reset_day, limit)
        current_count = status.get("count", 0)
        remaining = limit - current_count

        if remaining <= 0:
            print(f"[SerpApi] {key_name} has reached its monthly limit ({current_count}/{limit}, resets on Day {reset_day}). Skipping...")
            continue

        print(f"[SerpApi] Using {key_name} (usage: {current_count}/{limit}, {remaining} remaining, resets {status.get('next_reset')})")

        params = {
            "engine": "google",
            "q": query,
            "tbm": "isch",
            "api_key": api_key,
            "num": max(10, num_images * 3)
        }

        request_failed = False
        error_reason = ""

        try:
            response = requests.get(url, params=params, timeout=45)
            if response.status_code in [401, 403, 429]:
                request_failed = True
                error_reason = f"HTTP {response.status_code} (Quota or Auth)"
            elif response.status_code != 200:
                request_failed = True
                error_reason = f"HTTP {response.status_code}"
            else:
                res_json = response.json()
                if "error" in res_json:
                    request_failed = True
                    error_reason = f"API error: {res_json['error']}"
                else:
                    data = res_json
                    record_key_usage(key_name, count_increment=1)
                    break
        except Exception as e:
            request_failed = True
            error_reason = f"Exception: {e}"

        if request_failed:
            print(f"[SerpApi] {key_name} failed ({error_reason}). Falling back to next key...")
            continue

    if not data:
        return [] if num_images > 1 else ""

    images_results = data.get("images_results", [])
    if not images_results:
        print(f"[SerpApi] No images found for query: {query}")
        return [] if num_images > 1 else ""

    os.makedirs(download_dir, exist_ok=True)
    safe_query = re.sub(r'[^a-zA-Z0-9_]', '_', query)[:50]

    downloaded_files = []

    for idx, image_result in enumerate(images_results):
        if len(downloaded_files) >= num_images:
            break

        image_url = image_result.get("original")
        if not image_url:
            continue

        try:
            img_resp = requests.get(image_url, timeout=10)
            img_resp.raise_for_status()

            file_path = os.path.join(download_dir, f"{safe_query}_{idx}.jpg")
            img = Image.open(BytesIO(img_resp.content))
            img = img.convert('RGB')
            img.save(file_path, 'JPEG')
            print(f"[SerpApi] Successfully downloaded image to {file_path}")
            downloaded_files.append(file_path)
        except Exception as e:
            print(f"[SerpApi] Failed to download {image_url}: {e}. Trying next...")
            continue

    if not downloaded_files:
        print(f"[SerpApi] All download attempts failed for query: {query}")
        return [] if num_images > 1 else ""

    return downloaded_files if num_images > 1 else downloaded_files[0]
