# ./reddit_client/reddit_app.py

import os
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

def safe_filename(text: str, max_length: int = 50) -> str:
    # Remove bad filename characters and shorten
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in text)[:max_length]

def run_video_pipeline():
    print("Fetching Reddit story...")
    story = fetch_story()
    if not story:
        print("No story found.")
        return
    print(f"Fetched story from r/{story['subreddit']}: {story['url']}")

    # Format story with GPT
    ai_input = f"{REDDIT_AI_PROMPT}\nTitle: {story['title']}\n\n{story['body']}"
    formatted_story = format_story_with_gpt(ai_input)
    print(f"Formatted story with GPT.{formatted_story}")

    # Save TTS audio in OUTPUT_DIR
    safe_title = safe_filename(story['title'])
    audio_file_path = OUTPUT_DIR / f"{story['subreddit']}_{safe_title}.mp3"
    print("Generating TTS...")
    audio_path = generate_tts(formatted_story, audio_file_path)
    print(f"Saved TTS audio: {audio_path}")

    # Save final video in OUTPUT_DIR
    video_output_path = OUTPUT_DIR / f"{story['subreddit']}_{safe_title}.mp4"
    print("Creating final video...")
    final_video = create_video(formatted_story, audio_path, video_output_path)
    print(f"Saved final video: {final_video}")

    # Split into shorts
    print("Splitting video into shorts...")
    parts = split_video(final_video, OUTPUT_DIR)

    print("\n Done! Generated files:")
    print(" - Full video:", final_video)
    print(" - TTS audio:", audio_path)
    print(" - Shorts:")
    for part in parts:
        print("   •", part)

if __name__ == "__main__":
    run_video_pipeline()