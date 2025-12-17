# ./reddit_client/reddit_app.py

import os
from pathlib import Path
from dotenv import load_dotenv

from .fetcher import fetch_story
from utilities.gpt_handler import format_story_with_gpt
from utilities.tts_generator import generate_tts
from .reddit_video_creator import create_video
from utilities.youtube_uploader import upload_video
from utilities.gpt_handler import generate_youtube_metadata

load_dotenv()

REDDIT_AI_PROMPT = os.getenv("REDDIT_AI_PROMPT")

OUTPUT_DIR = Path("leam_modules/Reddit_Story_Generator/output")
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
    #formatted_story = 'Hi, this is a test story for the video creation pipeline.' # Temporary placeholder
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

    # Generate YouTube metadata
    print("Generating YouTube metadata...")
    yt_title, yt_desc, yt_tags = generate_youtube_metadata(
        original_title=story["title"],
        story_text=formatted_story,
        subreddit=story["subreddit"],
        url=story["url"]
    )
    print("YouTube metadata generated.")

    # Upload to YouTube
    print("\nUploading video to YouTube...")
    upload_video(
        file_path=str(final_video),
        title=yt_title,
        description=yt_desc,
        tags=yt_tags,
        category=24,
        privacy="public",
    )

    print("\n Done! Generated files:")
    print(" - Full video:", final_video)
    print(" - TTS audio:", audio_path)

if __name__ == "__main__":
    run_video_pipeline()