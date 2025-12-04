# comment_client/commenter.py
from utilities.youtube_api import (
    get_trending_video,
    get_top_comments,
    post_comment,
    reply_to_comment,
    get_transcript,
)
from utilities.comment_validator import has_commented
from comment_client.comment_generator import generate_video_comment, generate_reply_comment
import os
import pickle
import random
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly"
]

CREDENTIALS_FILE = "secrets/client_secrets.json"
TOKEN_PICKLE = "secrets/youtube_token.pickle"

def get_youtube_service():
    """Returns an authenticated YouTube API client"""
    creds = None

    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=8080)

        with open(TOKEN_PICKLE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def make_comment(region="US", max_results=10):
    print("Authenticating...")
    youtube = get_youtube_service()

    print(f"Fetching top {max_results} trending videos in {region}...")
    trending_videos = get_trending_video(youtube, region=region, max_results=max_results)

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
        print("Transcript fetched: " + str(transcript))
    except Exception as e:
        transcript = "Transcript unavailable."
        print(f"No transcript available: {e}")

    # Generate and post main video comment
    video_comment = generate_video_comment(transcript)
    print("Posting main comment: "+ video_comment)
    #post_comment(youtube, video_id, video_comment)

    # Fetch top comments
    print("Fetching top comments...")
    top_comments = get_top_comments(youtube, video_id, limit=random.randint(2, 6))

    for c in top_comments:
        comment_id = c["id"]
        comment_text = c["snippet"]["topLevelComment"]["snippet"]["textDisplay"]

        reply = generate_reply_comment(comment_text)
        print(f"Replying to: {comment_text} | with: {reply}")
        #reply_to_comment(youtube, comment_id, reply)

    print("\nDone! Comments posted.")

if __name__ == "__main__":
    make_comment(region="US", max_results=10)