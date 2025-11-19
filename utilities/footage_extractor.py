# ./utilities/footage_extractor.py

import random
from pathlib import Path
from moviepy import VideoFileClip

def get_video_duration(video_path: Path) -> float:
    """Return duration (seconds) of a video file."""
    with VideoFileClip(str(video_path)) as clip:
        return clip.duration


def extract_footage(
    folder: Path,
    target_length: float,
    start_from: float | None = None,
    filename: str | None = None,
    output_path: Path | None = None
) -> Path:
    """
    Extracts a clip of a given length from a folder of long videos.
    If no filename is provided → choose a random video.
    If no start_from is provided → choose a random start time.

    Args:
        folder (Path): directory containing source background videos
        target_length (float): required clip duration (matches TTS)
        start_from (float|None): where to start inside the video (optional)
        filename (str|None): specific video to select (optional)
        output_path (Path|None): output clip path

    Returns:
        Path: Path to the extracted clip
    """
    folder = Path(folder)

    # Get video file list
    video_files = [
        f for f in folder.iterdir()
        if f.suffix.lower() in [".mp4", ".mov", ".avi", ".mkv"]
    ]

    if not video_files:
        raise FileNotFoundError(f"No video files found in: {folder}")

    # Video selection
    if filename:
        source = folder / filename
        if not source.exists():
            raise FileNotFoundError(f"Specified video not found: {source}")
    else:
        source = random.choice(video_files)

    print(f"[FootageExtractor] Selected video: {source.name}")

    # Determine duration
    video_length = get_video_duration(source)

    if video_length < target_length:
        raise ValueError(
            f"Video '{source.name}' is too short "
            f"({video_length:.2f}s < required {target_length:.2f}s)"
        )

    # Choose random start point if not provided
    if start_from is None:
        max_start = max(video_length - target_length, 0)
        start_from = random.uniform(0, max_start)

    end_time = start_from + target_length

    print(f"[FootageExtractor] Extracting from {start_from:.2f}s → {end_time:.2f}s")

    # Default output filename
    if output_path is None:
        output_path = folder / f"clip_{source.stem}_{int(start_from)}_{int(target_length)}.mp4"

    # Extract the clip
    with VideoFileClip(str(source)) as clip:
        extracted = clip.subclipped(start_from, end_time)
        extracted.write_videofile(
            str(output_path),
            codec="libx264",
            audio=False,
            fps=30,
            preset="fast"
        )

    print(f"[FootageExtractor] Saved clip → {output_path}")

    return output_path