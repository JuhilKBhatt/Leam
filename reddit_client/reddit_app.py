# ./reddit_client/reddit_app.py

import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

from .fetcher import fetch_story
from utilities.gpt_handler import format_story_with_gpt
from utilities.tts_generator import generate_tts
from .reddit_video_creator import create_video
from utilities.video_splitter import split_video

load_dotenv()

REDDIT_AI_PROMPT = os.getenv("REDDIT_AI_PROMPT")    

OUTPUT_DIR = Path("output_videos/reddit")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run_video_pipeline():
    print("Fetching Reddit story...")
    story = fetch_story()
    if not story:
        print("No story found.")
        return
    print(f"Fetched story from r/{story['subreddit']}: {story['url']}")

    # Combine title and text into a single string for gpt_handler
    ai_input = f"{REDDIT_AI_PROMPT}"+f"Title: {story['title']}\n\n{story['body']}"
    formatted_story = format_story_with_gpt(ai_input)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
        print("Generating TTS...")
        audio_path = generate_tts(story, Path(tmp_audio.name))

    output_file = OUTPUT_DIR / f"{story['subreddit']}_{story['title'][:30].replace(' ', '_')}.mp4"

    print("Creating final video...")
    final_video = create_video(story, audio_path, output_file)

    print("Splitting video into shorts...")
    parts = split_video(final_video, OUTPUT_DIR)

    print("\nDone! Generated clips:")
    for part in parts:
        print("  -", part)

if __name__ == "__main__":
    run_video_pipeline()