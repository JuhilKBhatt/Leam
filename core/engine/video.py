import random
import re
import unicodedata
from pathlib import Path
from moviepy import VideoFileClip
from core.engine.gpu import gpu_write_videofile

def get_video_duration(video_path: Path) -> float:
    """Return duration (seconds) of a video file. Safely ignores corrupted/unsupported files."""
    try:
        with VideoFileClip(str(video_path)) as clip:
            return clip.duration
    except Exception as e:
        print(f"[FootageExtractor] Skipping {video_path.name} due to metadata/read error.")
        return 0.0

def extract_footage(
    folder: Path,
    target_length: float,
    start_from: float | None = None,
    filename: str | None = None,
    output_path: Path | None = None
) -> Path:
    """
    Extracts a clip of a given length from a folder of long videos.
    If individual videos are too short, stitches multiple random clips together.
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
        
    clips_to_concat = []
    current_length = 0.0

    for cand in candidates:
        if current_length >= target_length:
            break
            
        print(f"[FootageExtractor] Trying video: {cand.name}")
        vid_len = get_video_duration(cand)
        if vid_len <= 0:
            continue
            
        needed = target_length - current_length
        
        try:
            if vid_len >= needed:
                if start_from is not None and current_length == 0:
                    start = start_from
                else:
                    max_start = vid_len - needed
                    start = random.uniform(0, max_start) if max_start > 0 else 0
                
                clip = VideoFileClip(str(cand)).subclipped(start, start + needed)
            else:
                clip = VideoFileClip(str(cand))
                
            # Resize and crop to exactly 1080x1920 (TikTok standard) to prevent OOM
            # If we don't do this, MoviePy creates a massive canvas for 4K video combinations.
            clip = clip.resized(height=1920)
            if clip.w > 1080:
                x_center = clip.w / 2
                clip = clip.cropped(x1=x_center - 540, y1=0, x2=x_center + 540, y2=1920)
            elif clip.w < 1080:
                # If width is less than 1080, resize width to 1080 and crop height
                clip = clip.resized(width=1080)
                y_center = clip.h / 2
                clip = clip.cropped(x1=0, y1=y_center - 960, x2=1080, y2=y_center + 960)
                
            clips_to_concat.append(clip)
            current_length += clip.duration
        except Exception as e:
            print(f"[FootageExtractor] Error processing {cand.name}: {e}")
            continue

    if not clips_to_concat:
        raise ValueError(f"No valid videos found in {folder} to extract from.")

    try:
        from moviepy.editor import concatenate_videoclips, vfx
    except ImportError:
        from moviepy import concatenate_videoclips, vfx

    if current_length < target_length:
        print("[FootageExtractor] Not enough footage even after stitching. Looping to fill duration.")
        # method="chain" is now safe because all clips are strictly 1080x1920
        temp_comp = concatenate_videoclips(clips_to_concat, method="chain")
        try:
            final_clip = temp_comp.fx(vfx.loop, duration=target_length)
        except AttributeError:
            # For MoviePy 2.0+ where fx might be replaced with direct method
            from moviepy.video.fx.all import loop
            final_clip = loop(temp_comp, duration=target_length)
    else:
        final_clip = concatenate_videoclips(clips_to_concat, method="chain")

    # Default output filename
    if output_path is None:
        output_path = folder / f"clip_stitched_{int(target_length)}.mp4"

    print(f"[FootageExtractor] Extracting/stitching to {output_path}")
    gpu_write_videofile(
        final_clip,
        str(output_path),
        codec="libx264",
        audio=False,
        fps=30,
        preset="fast",
        logger=None
    )

    # Clean up clips to prevent memory leaks
    final_clip.close()
    for clip in clips_to_concat:
        clip.close()

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
        gpu_write_videofile(subclip, str(part_file), fps=30, codec="libx264", audio_codec="aac", logger=None)
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
