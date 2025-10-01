# ./reddit_client/reddit_app.py

import tempfile
from pathlib import Path
from dotenv import load_dotenv

from .fetcher import fetch_random_story
from utilities.gpt_handler import format_story_with_gpt
from utilities.tts_generator import generate_tts
from .reddit_video_creator import create_video
from utilities.video_splitter import split_video

load_dotenv()

OUTPUT_DIR = Path("output_videos/reddit")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_video_pipeline():
    print("Fetching Reddit story...")
    story = fetch_random_story()
    if not story:
        print("No story found.")
        return
    print(f"Fetched story from r/{story['subreddit']}: {story['title']}")

    # Combine title and text into a single string for gpt_handler
    ai_input = f"Title: {story['title']}\n\nStory: {story['text']}"

    print("Formatting story with GPT...")
    formatted_story = format_story_with_gpt(ai_input)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
        print("Generating TTS...")
        audio_path = generate_tts(formatted_story, Path(tmp_audio.name))

    output_file = OUTPUT_DIR / f"{story['subreddit']}_{story['title'][:30].replace(' ', '_')}.mp4"

    print("Creating final video...")
    final_video = create_video(formatted_story, audio_path, output_file)

    print("Splitting video into shorts...")
    parts = split_video(final_video, OUTPUT_DIR)

    print("\nDone! Generated clips:")
    for part in parts:
        print("  -", part)

if __name__ == "__main__":
    run_video_pipeline()