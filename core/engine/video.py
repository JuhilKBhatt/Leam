import re
import os
import random
import subprocess
import unicodedata
from pathlib import Path
from core.engine.gpu import detect_gpu_backend
import core.engine.gpu as gpu_module

def get_media_duration(media_path: Path) -> float:
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "default=noprint_wrappers=1:nokey=1", str(media_path)],
            capture_output=True, text=True, check=True
        )
        return float(res.stdout.strip())
    except Exception as e:
        print(f"[MediaInfo] Could not read duration of {media_path.name}")
        return 0.0

def _normalize_video(raw_path: Path, cache_path: Path):
    """Normalizes a raw video to 1080x1920, 30fps, no audio using the best GPU backend."""
    backend = detect_gpu_backend()
    print(f"[FootageExtractor] 🔄 Normalizing {raw_path.name} on {backend} GPU...")
    
    # Complex scale filter to ensure we crop to 1080x1920 without stretching
    vf = "fps=30,scale=w='if(gt(a,1080/1920),-1,1080)':h='if(gt(a,1080/1920),1920,-1)',crop=1080:1920"
    
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    
    if backend == "vaapi":
        device = gpu_module._working_vaapi_device or "/dev/dri/renderD128"
        command.extend(["-init_hw_device", f"vaapi=va:{device}", "-filter_hw_device", "va", "-i", str(raw_path)])
        vf += ",format=nv12,hwupload"
        command.extend(["-vf", vf, "-c:v", "h264_vaapi", "-qp", "24"])
    elif backend == "videotoolbox":
        command.extend(["-i", str(raw_path), "-vf", vf, "-c:v", "h264_videotoolbox", "-q:v", "50"])
    elif backend == "nvenc":
        command.extend(["-i", str(raw_path), "-vf", vf, "-c:v", "h264_nvenc", "-preset", "p4"])
    else:
        command.extend(["-i", str(raw_path), "-vf", vf, "-c:v", "libx264", "-preset", "fast"])

    # CRITICAL: Force a standard timebase for all clips so concat doesn't corrupt timestamps.
    # CRITICAL: Force keyframes every 30 frames (-g 30) so Remotion can seek flawlessly without glitching.
    command.extend(["-video_track_timescale", "90000", "-g", "30", "-an", str(cache_path)])
    
    subprocess.run(command, check=True)

def _get_ready_assets(folder: Path) -> list[Path]:
    """Checks the cache and normalizes only what is missing."""
    cache_dir = folder / ".cached"
    cache_dir.mkdir(exist_ok=True)
    
    ready_files = []
    
    for file in folder.iterdir():
        if not file.is_file():
            continue
        if file.suffix.lower() not in [".mp4", ".mov", ".avi", ".mkv"]:
            continue
        if file.name.startswith("clip_stitched"):
            continue
            
        cache_path = cache_dir / f"{file.stem}_norm.mp4"
        if not cache_path.exists():
            try:
                _normalize_video(file, cache_path)
            except subprocess.CalledProcessError as e:
                print(f"[FootageExtractor] ❌ Failed to normalize {file.name}: {e}")
                continue
                
        ready_files.append(cache_path)
        
    return ready_files

def extract_footage(
    folder: Path,
    target_length: float,
    start_from: float | None = None,
    filename: str | None = None,
    output_path: Path | None = None
) -> Path:
    """
    Extracts a clip of a given length from a folder of long videos.
    Uses FFmpeg concat demuxer for instant stitching of cached files.
    """
    folder = Path(folder)

    if output_path is None:
        output_path = folder / f"clip_stitched_{int(target_length)}.mp4"

    ready_files = _get_ready_assets(folder)
    
    if filename:
        ready_files = [f for f in ready_files if filename in f.name]
    
    if not ready_files:
        raise ValueError(f"No valid background videos found in {folder}")

    random.shuffle(ready_files)

    total_len = 0.0
    selected = []
    for f in ready_files:
        if total_len >= target_length: 
            break
        selected.append(f)
        total_len += get_media_duration(f)

    # If still not enough footage, loop the selected ones until we reach target length
    if total_len < target_length:
        print("[FootageExtractor] Not enough footage even after stitching. Looping to fill duration.")
        idx = 0
        while total_len < target_length:
            f = selected[idx % len(selected)]
            selected.append(f)
            total_len += get_media_duration(f)
            idx += 1

    # Stitch using FFmpeg concat demuxer (Instant stream copy without re-encoding)
    concat_list = folder / "concat_list.txt"
    with open(concat_list, "w") as f:
        for s in selected:
            f.write(f"file '{s.absolute()}'\n")

    print(f"[FootageExtractor] Stitching normalized videos instantly via stream copy...")
    
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-t", str(target_length),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "fastdecode",
        "-g", "1",
        "-an", str(output_path)
    ]
    
    try:
        subprocess.run(cmd, check=True)
    finally:
        if concat_list.exists():
            concat_list.unlink()
    
    print(f"[FootageExtractor] Saved clip → {output_path}")
    return output_path

def split_video(input_file: Path, output_dir: Path, max_duration=70):
    """Split video into short clips using raw FFmpeg."""
    clips = []
    total_duration = int(get_media_duration(input_file))
    
    for i, start in enumerate(range(0, total_duration, max_duration)):
        end = min(start + max_duration, total_duration)
        duration = end - start
        part_file = output_dir / f"{input_file.stem}_part{i+1}.mp4"
        
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(input_file),
            "-ss", str(start),
            "-t", str(duration),
            "-c:v", "libx264", "-c:a", "aac",
            str(part_file)
        ]
        subprocess.run(cmd, check=True)
        clips.append(part_file)

    return clips

def clean_subtitle_text(text: str) -> str:
    """Cleans TTS / Reddit text for subtitles."""
    if not isinstance(text, str): return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)
    text = re.sub(r"[\u200B-\u200F\uFEFF]", "", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = text.replace("&nbsp;", " ").replace("*", "").replace("•", "-").strip()
    return text

def format_for_subtitles(text: str, max_length: int = 20000) -> str:
    text = clean_subtitle_text(text)
    if len(text) > max_length:
        text = text[:max_length] + "…"
    return text if text else " "
