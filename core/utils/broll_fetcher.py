import os
from pathlib import Path
from core.api.pexels import download_pexels_landscape_broll, get_pexels_api_key

__all__ = ["fetch_broll", "fetch_scene_brolls", "download_pexels_landscape_broll"]

def fetch_broll(
    query: str,
    save_path: Path | str,
    pexels_key: str | None = None,
    module_name: str = "general"
) -> bool:
    """
    Downloads a landscape B-roll video clip for a given search query using Pexels.
    Returns True if successfully downloaded and normalized, False otherwise.
    """
    return download_pexels_landscape_broll(
        query=query,
        save_path=save_path,
        pexels_key=pexels_key,
        module_name=module_name
    )

def fetch_scene_brolls(
    scenes: list[dict],
    data_dir: Path | str,
    run_id: str,
    output_subpath: str = "modules/market_news/output",
    default_query: str = "stock market wall street",
    module_name: str = "market_news"
) -> list[str]:
    """
    Fetches landscape B-roll video clips for a list of scenes and attaches
    'b_roll_video' (relative path for Revideo/renderer) to each scene.
    
    If an individual scene clip fails to download, it reuses an earlier downloaded
    B-roll clip as a fallback so the video pipeline remains robust.
    
    Returns:
        List of relative paths to downloaded/assigned B-roll clips.
    """
    data_dir_path = Path(data_dir)
    data_dir_path.mkdir(parents=True, exist_ok=True)
    pexels_key = get_pexels_api_key()

    downloaded_brolls: list[str] = []
    print(f"[{module_name}] Fetching {len(scenes)} landscape B-roll clips via Pexels...")

    for idx, scene in enumerate(scenes):
        b_roll_query = scene.get("b_roll_query", default_query)
        vid_path = data_dir_path / f"{module_name}_{run_id}_bg_{idx}.mp4"

        success = download_pexels_landscape_broll(
            query=b_roll_query,
            save_path=vid_path,
            pexels_key=pexels_key,
            module_name=module_name
        )

        if not success and downloaded_brolls:
            # Fallback to previously downloaded clip in this run
            scene["b_roll_video"] = downloaded_brolls[-1]
        elif success:
            rel_vid_path = f"{output_subpath.rstrip('/')}/{vid_path.name}" if output_subpath else vid_path.name
            scene["b_roll_video"] = rel_vid_path
            downloaded_brolls.append(rel_vid_path)

    return downloaded_brolls
