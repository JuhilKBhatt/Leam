import os
import requests
import json
import re
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / "secrets" / ".env")

def get_serpapi_keys() -> list[str]:
    """
    Returns an ordered list of configured SerpApi keys.
    Checks SERPAPI_KEY_1, SERPAPI_KEY_2, etc., and falls back to SERPAPI_KEY.
    """
    load_dotenv(project_root / "secrets" / ".env", override=False)
    keys = []
    i = 1
    while True:
        k = os.getenv(f"SERPAPI_KEY_{i}")
        if k and k.strip():
            keys.append(k.strip())
            i += 1
        else:
            break

    default_key = os.getenv("SERPAPI_KEY")
    if default_key and default_key.strip() and default_key.strip() not in keys:
        keys.append(default_key.strip())

    # Catch any additional SERPAPI_KEY_* keys in the environment
    for env_k, env_v in os.environ.items():
        if env_k.startswith("SERPAPI_KEY_") and env_v and env_v.strip() not in keys:
            keys.append(env_v.strip())

    return keys

def get_serpapi_key() -> str | None:
    """Returns the primary SerpApi key or None if not configured."""
    keys = get_serpapi_keys()
    return keys[0] if keys else None

SERPAPI_KEY = get_serpapi_key()

def get_google_image_from_serpapi(query: str, download_dir: str, num_images: int = 1) -> str | list[str]:
    """
    Searches for an image using SerpApi and downloads the first result (or up to `num_images`).
    Returns the path to the downloaded image, or a list of paths if num_images > 1.
    Supports multiple keys (SERPAPI_KEY_1, SERPAPI_KEY_2, ...) and automatically
    falls back to subsequent keys if a key runs out of quota or fails.
    """
    keys = get_serpapi_keys()
    if not keys:
        raise ValueError("SERPAPI_KEY (or SERPAPI_KEY_1, SERPAPI_KEY_2, etc.) not found in environment variables.")
        
    url = "https://serpapi.com/search"
    print(f"[SerpApi] Searching for: {query} (need {num_images}, {len(keys)} key(s) available)")

    data = None
    for key_idx, key in enumerate(keys):
        key_label = f"Key #{key_idx + 1}"
        params = {
            "engine": "google",
            "q": query,
            "tbm": "isch",
            "api_key": key,
            "num": max(10, num_images * 3)  # Get more in case some fail
        }

        max_retries = 3
        key_quota_exhausted = False

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=45)
                if response.status_code in [401, 403, 429]:
                    print(f"[SerpApi] {key_label} returned HTTP {response.status_code} (quota or auth issue).")
                    key_quota_exhausted = True
                    break

                response.raise_for_status()
                res_json = response.json()

                if "error" in res_json:
                    err_msg = res_json["error"]
                    print(f"[SerpApi] {key_label} returned error: {err_msg}")
                    if any(w in err_msg.lower() for w in ["searches", "quota", "limit", "exhausted", "valid", "invalid", "plan"]):
                        key_quota_exhausted = True
                        break

                data = res_json
                break
            except requests.exceptions.RequestException as e:
                print(f"[SerpApi] {key_label} attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(3)
                else:
                    print(f"[SerpApi] {key_label} retries exhausted.")

        if data and data.get("images_results"):
            break

        if key_quota_exhausted and key_idx < len(keys) - 1:
            print(f"[SerpApi] Switching to next SerpApi key ({key_idx + 2}/{len(keys)})...")
            continue
    
    if not data:
        return [] if num_images > 1 else ""
    
    images_results = data.get("images_results", [])
    if not images_results:
        print(f"[SerpApi] No images found for query: {query}")
        return [] if num_images > 1 else ""
        
    os.makedirs(download_dir, exist_ok=True)
    # Clean the query to create a safe filename, limited to 50 characters
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
