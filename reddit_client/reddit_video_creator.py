# ./reddit_client/reddit_video_creator.py

import textwrap
from pathlib import Path
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    ImageClip
)

VIDEO_SIZE = (1080, 1920)  # Portrait resolution

def generate_subtitles_clips(text: str, duration: float, video_size=VIDEO_SIZE):
    """Generate subtitle clips that appear line by line."""
    # Font for subtitles
    FONT_PATH = Path(__file__).resolve().parent.parent / "static" / "fonts" / "Lexend-Regular.otf"

    lines = textwrap.wrap(text, width=55)
    duration_per_line = duration / max(len(lines), 1)
    clips = []

    for i, line in enumerate(lines):
        print(f"Adding subtitle: {line}")
        txt_clip = TextClip(
            text=line,
            font_size=54,
            font=FONT_PATH,
            color="white",
            size=(video_size[0] - 200, video_size[1] // 3),
            method="caption"
        ).with_position("center", "center").with_start(i * duration_per_line).with_duration(duration_per_line)

        clips.append(txt_clip)

    return clips

def create_video(story_text: str, audio_file: Path, output_file: Path, background_path="bg_videos/test3.mp4"):
    """Combine background, subtitles, and audio into a final video."""
    audio_clip = AudioFileClip(str(audio_file))
    duration = audio_clip.duration

    # Load original 4K background — don't resize yet
    if Path(background_path).suffix.lower() in [".mp4", ".mov", ".avi"]:
        bg_clip = VideoFileClip(background_path).with_duration(duration)
    else:
        bg_clip = ImageClip(background_path).with_duration(duration)

    # Crop the center of the original (keeps sharpness)
    bg_clip = VideoFileClip.cropped(
        bg_clip,
        width=min(bg_clip.w, bg_clip.h * VIDEO_SIZE[0] / VIDEO_SIZE[1]),
        height=min(bg_clip.h, bg_clip.w * VIDEO_SIZE[1] / VIDEO_SIZE[0]),
        x_center=bg_clip.w / 2,
        y_center=bg_clip.h / 2
    )

    # Resize once to portrait 1080×1920
    bg_clip = bg_clip.resized(VIDEO_SIZE)

    # Add subtitles
    subtitles = generate_subtitles_clips(story_text, duration, video_size=VIDEO_SIZE)

    # Final composite
    final_clip = CompositeVideoClip([bg_clip, *subtitles], size=VIDEO_SIZE).with_audio(audio_clip)

    # Export with higher quality settings
    final_clip.write_videofile(
        str(output_file),
        fps=30,
        codec="libx265",
        audio_codec="aac",
        preset="slow",              # better compression, higher quality
        bitrate="12000k"             # increase bitrate (try 8000k–12000k for crisp 1080p)
    )

    return output_file