# modules/reddit_story/reddit_video_creator.py

import textwrap
import random
from pathlib import Path
from core.engine.video import extract_footage, format_for_subtitles
from core.api.llm import transcribe_audio_with_timestamps
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    CompositeAudioClip,
    ImageClip
)

VIDEO_SIZE = (1080, 1920)  # Portrait resolution

def generate_subtitles_clips(text: str, duration: float, video_size=VIDEO_SIZE, audio_file=None):
    """Generate subtitle clips that appear line by line."""
    FONT_PATH = "./static/fonts/Lexend-Regular.otf"
    
    clips = []

    if audio_file:
        word_data = transcribe_audio_with_timestamps(str(audio_file))
        if word_data:
            print("Using Whisper word-level timestamps for subtitles.")
            current_line_words = []
            current_line_length = 0
            lines_data = []
            
            for w_info in word_data:
                w_text = w_info["word"].strip()
                if not w_text:
                    continue
                
                if current_line_length + len(w_text) + (1 if current_line_words else 0) > 55:
                    lines_data.append({
                        "text": " ".join(w["word"].strip() for w in current_line_words),
                        "start": current_line_words[0]["start"],
                        "end": current_line_words[-1]["end"]
                    })
                    current_line_words = [w_info]
                    current_line_length = len(w_text)
                else:
                    current_line_words.append(w_info)
                    current_line_length += len(w_text) + (1 if current_line_words else 0)
                    
            if current_line_words:
                lines_data.append({
                    "text": " ".join(w["word"].strip() for w in current_line_words),
                    "start": current_line_words[0]["start"],
                    "end": current_line_words[-1]["end"]
                })
                
            for i, line_info in enumerate(lines_data):
                start_time = line_info["start"]
                end_time = line_info["end"]
                
                # Extend end time to next subtitle's start time to prevent gaps
                if i < len(lines_data) - 1:
                    next_start = lines_data[i+1]["start"]
                    end_time = next_start
                else:
                    end_time = max(end_time, duration)
                
                start_time = min(start_time, duration)
                end_time = min(end_time, duration)
                
                if end_time <= start_time:
                    continue
                
                txt_clip = TextClip(
                    text=line_info["text"],
                    font_size=54,
                    font=FONT_PATH,
                    color="white",
                    size=(video_size[0] - 200, video_size[1] // 3),
                    method="caption"
                ).with_position(
                    ("center", "center")
                ).with_start(
                    start_time
                ).with_duration(
                    end_time - start_time
                )
                clips.append(txt_clip)
                
            return clips
            
    print("Falling back to length-based subtitle estimation.")
    lines = textwrap.wrap(text, width=55)
    
    def get_line_weight(line):
        weight = len(line)
        weight += line.count('.') * 15
        weight += line.count('!') * 15
        weight += line.count('?') * 15
        weight += line.count(',') * 8
        weight += line.count('-') * 5
        weight += line.count(';') * 10
        weight += line.count(':') * 10
        return weight

    total_weight = sum(get_line_weight(line) for line in lines)
    if total_weight == 0:
        total_weight = 1
        
    current_time = 0.0

    for line in lines:
        line_duration = (get_line_weight(line) / total_weight) * duration
        
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
            current_time
        ).with_duration(
            line_duration
        )

        clips.append(txt_clip)
        current_time += line_duration

    return clips

def create_video(
    story_text: str,
    audio_file: Path,
    output_file: Path,
):
    """
    Creates the final reddit-style video using extracted background footage.
    """
    story_text = format_for_subtitles(story_text)

    # Load audio and detect TTS length
    audio_clip = AudioFileClip(str(audio_file))
    tts_duration = audio_clip.duration

    final_audio = audio_clip
    music_dir = Path("media/audio/music")

    if music_dir.exists():
        music_files = [f for f in music_dir.iterdir() if f.suffix.lower() in [".mp3", ".wav", ".m4a"]]
        if music_files:
            chosen_music = random.choice(music_files)
            print(f"Adding background music: {chosen_music}")
            music_clip = AudioFileClip(str(chosen_music))

            # Loop or cut music to match TTS duration
            if music_clip.duration < tts_duration:
                from moviepy.audio.fx.all import audio_loop
                music_clip = audio_loop(music_clip, duration=tts_duration)
            else:
                music_clip = music_clip.subclipped(0, tts_duration)

            # Set volume to 20%
            music_clip = music_clip.with_volume_scaled(0.2)

            final_audio = CompositeAudioClip([audio_clip.with_start(0), music_clip.with_start(0)])

    print(f"TTS duration detected: {tts_duration:.2f}s")
    print("Extracting background footage...")

    # Ensure background video directory exists
    video_dir = Path("media/video/game")
    video_dir.mkdir(parents=True, exist_ok=True)

    # Extract background footage matching the TTS length
    extracted_path = extract_footage(
        folder=video_dir,
        target_length=tts_duration,
        start_from=None,
        filename=None
    )
    print(f"Using extracted background footage: {extracted_path}")

    # Load extracted footage
    bg_clip = VideoFileClip(str(extracted_path)).with_duration(tts_duration)

    # Crop centre to 9:16 aspect ratio
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
        video_size=VIDEO_SIZE,
        audio_file=audio_file
    )

    # Composite video
    final_clip = CompositeVideoClip(
        [bg_clip, *subtitles],
        size=VIDEO_SIZE
    ).with_audio(final_audio)

    # Export final video
    final_clip.write_videofile(
        str(output_file),
        fps=30,
        codec="libx264", # libx264 is more widely compatible than x265
        audio_codec="aac",
        preset="ultrafast",
        bitrate="12000k",
        threads=4
    )

    # Clean up the temporary background footage clip
    try:
        if extracted_path and Path(extracted_path).exists():
            Path(extracted_path).unlink()
            print(f"Cleaned up temporary background clip: {extracted_path}")
    except Exception as e:
        print(f"Failed to clean up {extracted_path}: {e}")

    return output_file
