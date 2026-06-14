# modules/youtube_commenter/commenter.py
import random
import json
from pathlib import Path
from core.api.google import (
    get_youtube_service,
    get_trending_video,
    get_top_comments,
    post_comment,
    reply_to_comment,
    get_transcript,
)
from core.utils.comment_validator import has_commented
from .comment_generator import generate_video_comment, generate_reply_comment

def load_settings():
    module_dir = Path(__file__).parent
    module_json = module_dir / "module.json"
    if not module_json.exists():
        return {}
    
    with open(module_json, "r") as f:
        data = json.load(f)
        return data.get("settings", {})

def make_comment():
    settings = load_settings()
    
    # Extract settings with fallbacks
    region = settings.get("YT_Region-stringME", "US").split(",")[0].strip()
    max_trending = int(settings.get("YT_Trending_Limit-integerNE", 10))
    replies_count = int(settings.get("YT_Replies_per_Video-integerNE", 5))
    video_prompt = settings.get("YT_Video_Comment_Prompt-stringLE", "")
    reply_prompt = settings.get("YT_Reply_Comment_Prompt-stringLE", "")

    print("Authenticating...")
    youtube = get_youtube_service()

    print(f"Fetching top {max_trending} trending videos in {region}...")
    trending_videos = get_trending_video(youtube, region=region, max_results=max_trending)

    if not trending_videos:
        print("No trending videos found.")
        return

    video = None
    for v in trending_videos:
        vid = v["id"]
        if not has_commented(vid):
            video = v
            break

    if not video:
        print("Already commented on all top trending videos. Skipping.")
        return

    video_id = video["id"]
    title = video["snippet"]["title"]
    print(f"Trending Video: {title} ({video_id})")

    # Get transcript
    print("Fetching transcript...")
    try:
        transcript = get_transcript(video_id)
    except Exception as e:
        transcript = "Transcript unavailable."
        print(f"No transcript available: {e}")

    # Generate and post main video comment
    video_comment = generate_video_comment(transcript, video_prompt)
    print("Posting main comment: " + video_comment)
    post_comment(youtube, video_id, video_comment)

    # Fetch top comments
    print("Fetching top comments...")
    # Using a slight variation around the requested replies count
    limit = max(1, random.randint(replies_count - 1, replies_count + 1))
    top_comments = get_top_comments(youtube, video_id, limit=limit)

    for c in top_comments:
        comment_id = c["id"]
        comment_text = c["snippet"]["topLevelComment"]["snippet"]["textDisplay"]

        reply = generate_reply_comment(comment_text, transcript, reply_prompt)
        print(f"Replying to: {comment_text} | with: {reply}")
        reply_to_comment(youtube, comment_id, reply)

    print("\nDone! Comments posted.")

if __name__ == "__main__":
    make_comment()
