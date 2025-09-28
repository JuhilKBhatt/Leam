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

def generate_subtitles_clips(text: str, duration: float, video_size=(1080, 1920)):
    """Generate subtitle clips that appear line by line."""
    lines = textwrap.wrap(text, width=60)
    duration_per_line = duration / max(len(lines), 1)
    clips = []

    for i, line in enumerate(lines):
        txt_clip = TextClip(
            txt="Hi",
            fontsize=40,
            font='Arial',
            color="white",
            size=(video_size[0] - 100, None),
            method="caption"
        ).set_position(("center", "bottom")).set_start(i * duration_per_line).set_duration(duration_per_line)

        clips.append(txt_clip)

    return clips

def create_video(story_text: str, audio_file: Path, output_file: Path, background_path="bg_videos/test.mp4"):
    """Combine background, subtitles, and audio into a final video."""
    audio_clip = AudioFileClip(str(audio_file))
    duration = audio_clip.duration

    if Path(background_path).suffix.lower() in [".mp4", ".mov", ".avi"]:
        bg_clip = VideoFileClip(background_path).with_duration(duration).resized(height=1920).with_position("center")
    else:
        bg_clip = ImageClip(background_path).with_duration(duration).resized(height=1920).with_position("center")

    subtitles = generate_subtitles_clips(story_text, duration)

    final_clip = CompositeVideoClip([bg_clip, *subtitles]).set_audio(audio_clip)
    
    final_clip.write_videofile(str(output_file), fps=30, codec="libx264", audio_codec="aac")

    return output_file