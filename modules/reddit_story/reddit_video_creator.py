import json
import random
import subprocess
from pathlib import Path
from core.engine.video import extract_footage, get_media_duration
from core.api.llm import transcribe_audio_with_timestamps
from core.engine.music import generate_music_lyria

def create_video(
    story_text: str,
    audio_file: Path,
    output_file: Path,
    title_text: str = None,
    use_lyria: bool = True
):
    print("Preparing assets for Remotion rendering...")

    # Load audio just to get the duration
    tts_duration = get_media_duration(audio_file)

    print(f"TTS duration detected: {tts_duration:.2f}s")
    
    # 1. Background Video
    print("Extracting background footage...")
    video_dir = Path("media/video/game")
    video_dir.mkdir(parents=True, exist_ok=True)

    extracted_path = extract_footage(
        folder=video_dir,
        target_length=tts_duration + 7,
        start_from=None,
        filename=None
    )
    print(f"Using extracted background footage: {extracted_path}")

    # 2. Transcribe Subtitles
    word_data = transcribe_audio_with_timestamps(str(audio_file))
    if not word_data:
        word_data = [] # Fallback, Remotion handles empty words gracefully

    # 3. Choose Music
    music_path = None
    if use_lyria:
        lyria_music_path = Path("media/audio/music/lyria_custom.mp3")
        try:
            generate_music_lyria(
                script=story_text, 
                video_type="Reddit Story", 
                duration_sec=int(tts_duration) + 12,
                output_path=lyria_music_path
            )
            if lyria_music_path.exists():
                music_path = lyria_music_path
        except Exception as e:
            print(f"Lyria generation failed, falling back to random local music: {e}")

    if not music_path:
        music_dir = Path("media/audio/music")
        if music_dir.exists():
            music_files = [f for f in music_dir.iterdir() if f.suffix.lower() in [".mp3", ".wav", ".m4a"] and "lyria_custom" not in f.name]
            if music_files:
                music_path = random.choice(music_files)

    # 4. Prepare props for Remotion
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # We must ensure output_file's parent directory exists before Remotion tries to save there
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Add 7 seconds (210 frames) for the like/subscribe outro
    duration_frames = int(tts_duration * 30) + 210
    
    props = {
        "bgVideoPath": str(extracted_path) if extracted_path else "",
        "ttsAudioPath": str(audio_file),
        "musicPath": str(music_path) if music_path else "",
        "words": word_data,
        "title": title_text or "Reddit Story",
        "durationInFrames": duration_frames
    }

    remotion_dir = project_root / "remotion"
    remotion_dir.mkdir(parents=True, exist_ok=True)
    props_file = remotion_dir / "props_reddit.json"
    
    with open(props_file, "w") as f:
        json.dump(props, f)

    # 5. Run Remotion!
    print(f"Starting Remotion render ({duration_frames} frames)...")
    
    cmd = [
        "npx", "remotion", "render", 
        "src/index.ts", 
        "RedditStory", 
        str(output_file.absolute()),
        "--props=./props_reddit.json",
        "--concurrency=4",
        "--crf=14",
        "--scale=2",
        "--log=info"
    ]

    try:
        # Run Remotion command
        subprocess.run(cmd, cwd=remotion_dir, check=True)
        print(f"Remotion render complete! Saved to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Remotion rendering failed: {e}")
        
    # Clean up temporary footage
    try:
        if extracted_path and Path(extracted_path).exists():
            Path(extracted_path).unlink()
            print(f"Cleaned up temporary background clip: {extracted_path}")
    except Exception as e:
        print(f"Failed to clean up {extracted_path}: {e}")

    return output_file
