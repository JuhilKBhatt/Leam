import random
import re
import unicodedata
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
            candidates = [folder / filename]
    else:
        candidates = video_files.copy()
        random.shuffle(candidates)
        
    source = None
    video_length = 0
    for cand in candidates:
        print(f"[FootageExtractor] Trying video: {cand.name}")
        video_length = get_video_duration(cand)

        if video_length >= target_length:
            source = cand
            break
        else:
            print(f"[FootageExtractor] Too short ({video_length:.2f}s), trying next...")
    else:
        # None were long enough
        raise ValueError(
            f"No videos long enough for required length {target_length:.2f}s"
        )

    # Choose random start
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
            preset="fast",
            logger=None
        )

    print(f"[FootageExtractor] Saved clip → {output_path}")
    return output_path

def split_video(input_file: Path, output_dir: Path, max_duration=70):
    """Split video into short clips (e.g., for TikTok Shorts)."""
    video = VideoFileClip(str(input_file))
    clips = []

    for i, start in enumerate(range(0, int(video.duration), max_duration)):
        end = min(start + max_duration, video.duration)
        subclip = video.subclipped(start, end)
        part_file = output_dir / f"{input_file.stem}_part{i+1}.mp4"
        subclip.write_videofile(str(part_file), fps=30, codec="libx264", audio_codec="aac", logger=None)
        clips.append(part_file)

    return clips

def clean_subtitle_text(text: str) -> str:
    """
    Cleans TTS / Reddit text for subtitles.
    """
    if not isinstance(text, str):
        return ""

    # Normalize to fix strange unicode encodings
    text = unicodedata.normalize("NFKC", text)

    # Remove null bytes and invisible control chars
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

    # Remove weird zero-width chars
    text = re.sub(r"[\u200B-\u200F\uFEFF]", "", text)

    # Replace multiple newlines with one
    text = re.sub(r"\n{2,}", "\n", text)

    # Replace multiple spaces with one
    text = re.sub(r"[ ]{2,}", " ", text)

    # Strip common Reddit formatting symbols
    text = text.replace("&nbsp;", " ")
    text = text.replace("*", "")
    text = text.replace("•", "-")

    # Trim leading/trailing whitespace
    text = text.strip()

    return text

def format_for_subtitles(text: str, max_length: int = 20000) -> str:
    """
    Final formatting step.
    """
    text = clean_subtitle_text(text)

    # Safety length cap
    if len(text) > max_length:
        text = text[:max_length] + "…"

    # Guarantee something is returned
    return text if text else " "
