# ./reddit_client/reddit_video_creator.py

import textwrap
from pathlib import Path
import moviepy.editor as mp

def generate_subtitles_clips(text: str, duration: float, video_size=(1080, 1920)):
    """Generate subtitle clips that appear line by line."""
    lines = textwrap.wrap(text, width=60)
    duration_per_line = duration / len(lines)
    clips = []

    for i, line in enumerate(lines):
        txt_clip = mp.TextClip(
            line,
            fontsize=40,
            color="white",
            font="Arial-Bold",
            stroke_color="black",
            stroke_width=2,
            size=(video_size[0] - 100, None),
            method="caption",
            align="center"
        ).set_position(("center", "bottom")).set_start(i * duration_per_line).set_duration(duration_per_line)

        clips.append(txt_clip)

    return clips

def create_video(story_text: str, audio_file: Path, output_file: Path, background_path="static/backgrounds/bg.jpg"):
    """Combine background, subtitles, and audio into a final video."""
    audio_clip = mp.AudioFileClip(str(audio_file))
    duration = audio_clip.duration

    # Background video or static image
    bg_clip = mp.ImageClip(background_path).set_duration(duration).resize(height=1920).set_position("center")

    # Subtitles
    subtitles = generate_subtitles_clips(story_text, duration)

    # Final composition
    final_clip = mp.CompositeVideoClip([bg_clip, *subtitles]).set_audio(audio_clip)
    final_clip.write_videofile(str(output_file), fps=30, codec="libx264", audio_codec="aac")

    return output_file