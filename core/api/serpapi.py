import os
import requests
import json
import re
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv('SERPAPI_KEY')

def get_google_image_from_serpapi(query: str, download_dir: str) -> str:
    """
    Searches for an image using SerpApi and downloads the first result.
    Returns the path to the downloaded image.
    """
    if not SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY not found in environment variables.")
        
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "tbm": "isch",
        "api_key": SERPAPI_KEY,
        "num": 5  # Get a few in case the first fails to download
    }
    
    print(f"[SerpApi] Searching for: {query}")
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    images_results = data.get("images_results", [])
    if not images_results:
        print(f"[SerpApi] No images found for query: {query}")
        return ""
        
    os.makedirs(download_dir, exist_ok=True)
    # Clean the query to create a safe filename, limited to 50 characters
    safe_query = re.sub(r'[^a-zA-Z0-9_]', '_', query)[:50]
    file_path = os.path.join(download_dir, f"{safe_query}.jpg")
    
    for image_result in images_results:
        image_url = image_result.get("original")
        if not image_url:
            continue
            
        try:
            img_resp = requests.get(image_url, timeout=10)
            img_resp.raise_for_status()
            
            img = Image.open(BytesIO(img_resp.content))
            img = img.convert('RGB')
            img.save(file_path, 'JPEG')
            print(f"[SerpApi] Successfully downloaded image to {file_path}")
            return file_path
        except Exception as e:
            print(f"[SerpApi] Failed to download {image_url}: {e}. Trying next...")
            continue
            
    print(f"[SerpApi] All download attempts failed for query: {query}")
    return ""
