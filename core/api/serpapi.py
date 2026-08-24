import os
import requests
import json
import re
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv('SERPAPI_KEY')

def get_google_image_from_serpapi(query: str, download_dir: str, num_images: int = 1) -> str | list[str]:
    """
    Searches for an image using SerpApi and downloads the first result (or up to `num_images`).
    Returns the path to the downloaded image, or a list of paths if num_images > 1.
    """
    if not SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY not found in environment variables.")
        
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "tbm": "isch",
        "api_key": SERPAPI_KEY,
        "num": max(10, num_images * 3)  # Get more in case some fail
    }
    
    print(f"[SerpApi] Searching for: {query} (need {num_images})")
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
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
