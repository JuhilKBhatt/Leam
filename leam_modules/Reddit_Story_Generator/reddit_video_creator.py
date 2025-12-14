# ./reddit_client/reddit_video_creator.py

import textwrap
from pathlib import Path
from utilities.footage_extractor import extract_footage
from utilities.subtitle_formatter import format_for_subtitles
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
    FONT_PATH = (
        Path(__file__).resolve().parent.parent
        / "static" / "fonts" / "Lexend-Regular.otf"
    )

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
        ).with_position(
            ("center", "center")
        ).with_start(
            i * duration_per_line
        ).with_duration(
            duration_per_line
        )

        clips.append(txt_clip)

    return clips

def create_video(
    story_text: str,
    audio_file: Path,
    output_file: Path,
):
    """
    Creates the final reddit-style video using extracted background footage.

    Automatically determines required length from TTS audio.
    start_from  = optional forced start time in background footage
    name        = optional video filename to pull from
    """

    story_text = format_for_subtitles(story_text)

    # Load audio and detect TTS length
    audio_clip = AudioFileClip(str(audio_file))
    tts_duration = audio_clip.duration

    print(f"TTS duration detected: {tts_duration:.2f}s")
    print("Extracting background footage...")

    # Extract background footage matching the TTS length
    extracted_path = extract_footage(
        folder=Path("bg_videos"),
        target_length=tts_duration,
        start_from=None,
        filename=None
    )
    print(f"Using extracted background footage: {extracted_path}")

    # Load extracted footage
    if Path(extracted_path).suffix.lower() in [".mp4", ".mov", ".avi"]:
        bg_clip = VideoFileClip(str(extracted_path)).with_duration(tts_duration)
    else:
        bg_clip = ImageClip(str(extracted_path)).with_duration(tts_duration)

    # Crop centre
    bg_clip = VideoFileClip.cropped(
        bg_clip,
        width=min(bg_clip.w, bg_clip.h * VIDEO_SIZE[0] / VIDEO_SIZE[1]),
        height=min(bg_clip.h, bg_clip.w * VIDEO_SIZE[1] / VIDEO_SIZE[0]),
        x_center=bg_clip.w / 2,
        y_center=bg_clip.h / 2
    )

    # Resize to 1080x1920
    bg_clip = bg_clip.resized(VIDEO_SIZE)

    # Add subtitles
    subtitles = generate_subtitles_clips(
        story_text,
        tts_duration,
        video_size=VIDEO_SIZE
    )

    # Composite video
    final_clip = CompositeVideoClip(
        [bg_clip, *subtitles],
        size=VIDEO_SIZE
    ).with_audio(audio_clip)

    # Export final video
    final_clip.write_videofile(
        str(output_file),
        fps=30,
        codec="libx265",
        audio_codec="aac",
        preset="slow",
        bitrate="12000k"
    )

    return output_file