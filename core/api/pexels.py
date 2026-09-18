import os
import time
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from core.utils.common import get_now

project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / "secrets" / ".env")

PEXELS_QUOTA_FILE = project_root / "data" / "pexels_quota.json"

def get_pexels_api_key() -> str | None:
    """Retrieves Pexels API key from environment."""
    return os.getenv("PEXELS_API_KEY")

def load_pexels_quota_data() -> dict:
    """Loads raw quota tracking data from DynamoDB or disk fallback."""
    try:
        from core.utils.dynamodb_sync import get_parameter
        remote_data = get_parameter("pexels_quota")
        if remote_data and isinstance(remote_data, dict):
            return remote_data
    except Exception:
        pass

    if not PEXELS_QUOTA_FILE.exists():
        return {}
    try:
        with open(PEXELS_QUOTA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_pexels_quota_data(data: dict):
    """Saves quota tracking data to DynamoDB or falls back to disk."""
    synced = False
    try:
        from core.utils.dynamodb_sync import put_parameter
        synced = put_parameter("pexels_quota", data)
    except Exception as e:
        print(f"[Pexels] Warning: Could not sync quota to DynamoDB: {e}")

    if not synced:
        try:
            PEXELS_QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(PEXELS_QUOTA_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Pexels] Warning: Could not save quota data locally: {e}")

def get_pexels_quota_status() -> dict:
    """
    Returns current Pexels API quota metrics for both hourly and monthly limits,
    pruning expired timestamps and resetting monthly counts if a new calendar month started.
    """
    now_ts = time.time()
    current_month = get_now().strftime("%Y-%m")
    data = load_pexels_quota_data()
    needs_save = False

    # 1. Monthly Reset check
    stored_month = data.get("month")
    if stored_month != current_month:
        data["month"] = current_month
        data["monthly_used"] = 0
        data["modules"] = {}
        needs_save = True

    # 2. Hourly sliding window check (last 3600 seconds)
    recent_ts = data.get("recent_timestamps", [])
    one_hour_ago = now_ts - 3600
    pruned_ts = [ts for ts in recent_ts if ts >= one_hour_ago]
    if len(pruned_ts) != len(recent_ts):
        data["recent_timestamps"] = pruned_ts
        needs_save = True

    hourly_used = len(pruned_ts)
    monthly_used = data.get("monthly_used", 0)
    modules_usage = data.get("modules", {})

    # Discover any active modules if not listed
    modules_dir = project_root / "modules"
    if modules_dir.exists():
        for mod_dir in modules_dir.iterdir():
            if mod_dir.is_dir() and not mod_dir.name.startswith((".", "_")):
                if mod_dir.name not in modules_usage:
                    modules_usage[mod_dir.name] = 0
                    needs_save = True

    # Calculate oldest request in the hour to determine next hourly reset
    resets_in_seconds = 0
    if pruned_ts:
        oldest_ts = min(pruned_ts)
        resets_in_seconds = max(0, int(3600 - (now_ts - oldest_ts)))

    hourly_limit = data["hourly_limit"]
    monthly_limit = data["monthly_limit"]

    status = {
        "month": current_month,
        "hourly": {
            "limit": hourly_limit,
            "used": hourly_used,
            "remaining": max(0, hourly_limit - hourly_used),
            "percent_used": round((hourly_used / hourly_limit) * 100, 2) if hourly_limit > 0 else 0,
            "resets_in_seconds": resets_in_seconds
        },
        "monthly": {
            "limit": monthly_limit,
            "used": monthly_used,
            "remaining": max(0, monthly_limit - monthly_used),
            "percent_used": round((monthly_used / monthly_limit) * 100, 2) if monthly_limit > 0 else 0
        },
        "modules": modules_usage,
        "upstream": {
            "limit": data.get("upstream_limit"),
            "remaining": data.get("upstream_remaining"),
            "reset": data.get("upstream_reset")
        },
        "last_updated": get_now().isoformat()
    }

    if needs_save:
        data["hourly_used"] = hourly_used
        data["monthly_used"] = monthly_used
        data["modules"] = modules_usage
        data["last_updated"] = status["last_updated"]
        save_pexels_quota_data(data)

    return status

def record_pexels_request(module_name: str, response_headers: dict | None = None):
    """
    Records an outgoing Pexels API request against hourly and monthly quotas,
    attributing it to the requesting module and synchronizing upstream response headers.
    """
    now_ts = time.time()
    current_month = get_now().strftime("%Y-%m")
    data = load_pexels_quota_data()

    if data.get("month") != current_month:
        data["month"] = current_month
        data["monthly_used"] = 0
        data["modules"] = {}

    # Update hourly timestamps
    recent_ts = [ts for ts in data.get("recent_timestamps", []) if ts >= (now_ts - 3600)]
    recent_ts.append(now_ts)
    data["recent_timestamps"] = recent_ts
    data["hourly_used"] = len(recent_ts)

    # Update monthly count
    data["monthly_used"] = data.get("monthly_used", 0) + 1

    # Update per-module breakdown
    modules = data.setdefault("modules", {})
    modules[module_name] = modules.get(module_name, 0) + 1

    # Upstream headers sync
    if response_headers:
        for k, v in response_headers.items():
            k_lower = k.lower()
            if k_lower == "x-ratelimit-limit":
                try:
                    data["upstream_limit"] = int(v)
                except ValueError:
                    pass
            elif k_lower == "x-ratelimit-remaining":
                try:
                    data["upstream_remaining"] = int(v)
                except ValueError:
                    pass
            elif k_lower == "x-ratelimit-reset":
                try:
                    data["upstream_reset"] = int(v)
                except ValueError:
                    pass

    data["last_updated"] = get_now().isoformat()
    save_pexels_quota_data(data)

def download_pexels_landscape_broll(
    query: str,
    save_path: Path | str,
    pexels_key: str | None = None,
    module_name: str = "market_news"
) -> bool:
    """
    Searches and downloads a landscape B-roll video clip from Pexels,
    enforcing hourly (200 req/hr) and monthly (20,000 req/mo) limits,
    recording telemetry, and normalizing the video with hardware acceleration.
    """
    save_path = Path(save_path)
    if not pexels_key:
        pexels_key = get_pexels_api_key()

    if not pexels_key:
        print("[Pexels] Error: No PEXELS_API_KEY configured in environment or secrets/.env")
        return False

    # 1. Check Rate Limits
    quota_status = get_pexels_quota_status()
    hourly_limit = quota_status["hourly"]["limit"]
    monthly_limit = quota_status["monthly"]["limit"]
    hourly_rem = quota_status["hourly"]["remaining"]
    monthly_rem = quota_status["monthly"]["remaining"]

    if hourly_rem <= 0:
        reset_secs = quota_status["hourly"]["resets_in_seconds"]
        print(f"⚠️ [Pexels] Hourly rate limit reached ({hourly_limit:,} reqs/hr). Request blocked. Resets in ~{reset_secs}s.")
        return False

    if monthly_rem <= 0:
        print(f"❌ [Pexels] Monthly quota limit reached ({monthly_limit:,} reqs/mo). Request blocked.")
        return False

    try:
        headers = {"Authorization": pexels_key}
        url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(query)}&orientation=landscape&per_page=5"

        resp = requests.get(url, headers=headers, timeout=20)
        # Record request immediately upon receiving response
        record_pexels_request(module_name=module_name, response_headers=dict(resp.headers))

        if resp.status_code == 429:
            print("⚠️ [Pexels] Received HTTP 429 Too Many Requests from Pexels API.")
            return False

        if resp.status_code != 200:
            print(f"[Pexels] Search returned status {resp.status_code} for query: {query}")
            return False

        data = resp.json()
        videos = data.get("videos", [])
        if not videos:
            print(f"[Pexels] No videos found for query: '{query}'")
            return False

        # Find best landscape file (preferring 1920x1080)
        chosen_link = None
        for vid in videos:
            files = vid.get("video_files", [])
            landscape_files = [f for f in files if f.get("width", 0) >= f.get("height", 0)]
            if landscape_files:
                landscape_files.sort(key=lambda x: abs(x.get("width", 0) - 1920))
                chosen_link = landscape_files[0].get("link")
                break

        if not chosen_link and videos[0].get("video_files"):
            chosen_link = videos[0]["video_files"][0].get("link")

        if not chosen_link:
            return False

        save_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading Pexels B-Roll: {query} -> {save_path.name}")
        vid_resp = requests.get(chosen_link, stream=True, timeout=60)
        if vid_resp.status_code == 200:
            temp_raw = save_path.parent / f"raw_{save_path.name}"
            with open(temp_raw, "wb") as f:
                for chunk in vid_resp.iter_content(chunk_size=16384):
                    f.write(chunk)

            # Normalize to 30fps faststart H.264 MP4 for Revideo compatibility
            import subprocess
            from core.engine.gpu import detect_gpu_backend
            gpu_backend = detect_gpu_backend()

            codec_args = ["-c:v", "libx264", "-preset", "ultrafast"]
            if gpu_backend == "nvenc":
                codec_args = ["-c:v", "h264_nvenc", "-preset", "p4"]
            elif gpu_backend == "vaapi":
                from core.engine.gpu import _working_vaapi_device
                dev = _working_vaapi_device or "/dev/dri/renderD128"
                codec_args = ["-init_hw_device", f"vaapi=va:{dev}", "-filter_hw_device", "va", "-c:v", "h264_vaapi"]

            ff_cmd = [
                "ffmpeg", "-y", "-i", str(temp_raw),
                *codec_args, "-pix_fmt", "yuv420p",
                "-r", "30", "-movflags", "+faststart",
                str(save_path)
            ]
            result = subprocess.run(ff_cmd, capture_output=True, text=True, timeout=60)
            try:
                temp_raw.unlink(missing_ok=True)
            except Exception:
                pass

            if result.returncode == 0 and save_path.exists() and save_path.stat().st_size > 1000:
                print(f"Successfully normalized Pexels video on {gpu_backend.upper()} GPU: {save_path.name}")
                return True
            else:
                if temp_raw.exists():
                    temp_raw.rename(save_path)
                return True

        return False
    except Exception as e:
        print(f"[Pexels] Error downloading video for '{query}': {e}")
        return False
