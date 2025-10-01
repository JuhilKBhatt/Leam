# ./utilities/video_splitter.py

from pathlib import Path
from moviepy import VideoFileClip

def split_video(input_file: Path, output_dir: Path, max_duration=70):
    """Split video into short clips (e.g., for TikTok Shorts)."""
    video = VideoFileClip(str(input_file))
    clips = []

    for i, start in enumerate(range(0, int(video.duration), max_duration)):
        end = min(start + max_duration, video.duration)
        subclip = video.subclipped(start, end)
        part_file = output_dir / f"{input_file.stem}_part{i+1}.mp4"
        subclip.write_videofile(str(part_file), fps=30, codec="libx264", audio_codec="aac")
        clips.append(part_file)

    return clips