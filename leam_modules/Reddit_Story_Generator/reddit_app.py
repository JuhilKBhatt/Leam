# ./reddit_client/reddit_app.py

from pathlib import Path
from utilities.config_loader import load_config

from .fetcher import fetch_story
from utilities.gpt_handler import format_story_with_gpt
from utilities.tts_generator import generate_tts
from .reddit_video_creator import create_video
from utilities.youtube_uploader import upload_video
from utilities.gpt_handler import generate_youtube_metadata
from utilities.logger import write_log
from utilities.safe_filename import safe_filename

config_path = Path("leam_modules/Reddit_Story_Generator/module.json")
config = load_config(str(config_path))
settings = config['settings']

SUBREDDITS = settings.get("Subreddits-stringME").split(",") if settings.get("Subreddits-stringME") else []
MIN_SCORE = settings.get("Story_Min_Score-integerNE")
MIN_LENGTH = settings.get("Story_Min_Length_minutes-integerFE")
MAX_RETRIES = settings.get("Story_Max_Fetches-integerNE")
REDDIT_AI_PROMPT = settings.get("Reddit_Story_AI_Prompt-stringLE")
VIDEO_UPLOAD_SPEED = settings.get("Video_Upload_Speed_MBs-integerFE")
TTS_VOICES = settings.get("Reddit_TTS_Voice-stringME").split(",") if settings.get("Reddit_TTS_Voice-stringME") else []
TTS_CHARACTER_LIMIT = settings.get("Reddit_TTS_Character_Limit-integerNE", 150000)

OUTPUT_DIR = Path("leam_modules/Reddit_Story_Generator/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = Path(__file__).parent / "logs/runtime.log"

def run_video_pipeline():
    write_log(LOG_FILE, "Starting Reddit story video generation pipeline...")
    story = fetch_story(MAX_RETRIES, MIN_SCORE, MIN_LENGTH, SUBREDDITS)
    if not story:
        print("No story found.")
        return
    write_log(LOG_FILE, f"Fetched story from r/{story['subreddit']}: {story['url']}")

    # Format story with GPT
    ai_input = f"{REDDIT_AI_PROMPT}\nTitle: {story['title']}\n\n{story['body']}"
    formatted_story = format_story_with_gpt(ai_input)
    write_log(LOG_FILE, f"Formatted story with GPT.{formatted_story}")

    # Save TTS audio in OUTPUT_DIR
    safe_title = safe_filename(story['title'])
    audio_file_path = OUTPUT_DIR / f"{story['subreddit']}_{safe_title}.mp3"
    write_log(LOG_FILE, f"Generating TTS audio at {audio_file_path}...")
    
    # Generate TTS with chunking
    audio_path = generate_tts(
        text=formatted_story, 
        output_file=audio_file_path, 
        TTS_VOICES=TTS_VOICES, 
        TTS_CHARACTER_LIMIT=TTS_CHARACTER_LIMIT, 
        config_path=config_path
    )

    # Save final video in OUTPUT_DIR
    video_output_path = OUTPUT_DIR / f"{story['subreddit']}_{safe_title}.mp4"
    write_log(LOG_FILE, f"Creating video at {video_output_path}...")
    final_video = create_video(formatted_story, audio_path, video_output_path)

    # Generate YouTube metadata
    write_log(LOG_FILE, "Generating YouTube metadata...")
    yt_title, yt_desc, yt_tags = generate_youtube_metadata(
        original_title=story["title"],
        story_text=formatted_story,
        subreddit=story["subreddit"],
        url=story["url"]
    )
    write_log(LOG_FILE, f"YouTube Title: {yt_title}\nDescription: {yt_desc}\nTags: {yt_tags}")

    # Upload to YouTube
    write_log(LOG_FILE, "Uploading video to YouTube...")
    upload_video(
        file_path=str(final_video),
        title=yt_title,
        description=yt_desc,
        tags=yt_tags,
        category=24,
        privacy="public",
    )
    write_log(LOG_FILE, "Video uploaded successfully.")

if __name__ == "__main__":
    run_video_pipeline()