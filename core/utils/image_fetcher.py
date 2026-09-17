import os
from pathlib import Path
from core.api.serpapi import get_google_image_from_serpapi, get_serpapi_keys

SUPPORTED_IMAGE_ELEMENTS = {"FigureShow", "FigureQuote", "ObjectShow", "NewsClipping"}

def fetch_image(
    target: str | dict,
    data_dir: Path | str,
    output_subpath: str = "",
    num_images: int = 1
) -> tuple[str | None, str | None]:
    """
    Downloads an image via SerpApi using configured keys with automatic fallback.

    Accepts either:
      - A search query string (e.g. "Apple Inc. logo icon transparent png")
      - A scene element dictionary (from video element templates or market_news)
        with fields like 'image_query', 'name', or 'object_name'.

    If a dictionary is provided, automatically verifies element type against
    SUPPORTED_IMAGE_ELEMENTS (if a 'type' field is present) and attaches:
      element["image_url"] = rel_path

    Returns:
        (abs_path, rel_path) where:
          abs_path: absolute file system path to the downloaded image (or None)
          rel_path: relative path formatted for video rendering (or None)
    """
    if isinstance(target, dict):
        elem_type = target.get("type")
        if elem_type and elem_type not in SUPPORTED_IMAGE_ELEMENTS:
            return None, None

        query = target.get("image_query") or target.get("name") or target.get("object_name")
    else:
        query = str(target) if target else None

    if not query or not str(query).strip():
        return None, None

    keys = get_serpapi_keys()
    if not keys:
        return None, None

    try:
        data_dir_path = Path(data_dir)
        downloaded = get_google_image_from_serpapi(str(query).strip(), str(data_dir_path), num_images=num_images)
        if downloaded:
            abs_path = downloaded[0] if isinstance(downloaded, list) else downloaded
            if abs_path and os.path.exists(abs_path):
                filename = Path(abs_path).name
                rel_path = f"{output_subpath.rstrip('/')}/{filename}" if output_subpath else filename

                if isinstance(target, dict):
                    target["image_url"] = rel_path

                return abs_path, rel_path
    except Exception as e:
        print(f"[ImageFetcher] SerpAPI image fetch failed for query '{query}': {e}")

    return None, None

def fetch_and_attach_element_image(
    element: dict,
    data_dir: Path | str,
    output_subpath: str = "modules/market_news/output"
) -> bool:
    """
    Convenience wrapper to fetch and attach image_url to an element dictionary.
    Returns True if an image was successfully fetched and attached, False otherwise.
    """
    abs_path, rel_path = fetch_image(element, data_dir, output_subpath)
    return bool(rel_path)
