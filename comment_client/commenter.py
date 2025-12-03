# comment_client/commenter.py
from utilities.youtube_api import (
    get_trending_video,
    get_top_comments,
    post_comment,
    reply_to_comment,
    get_transcript,
)
from comment_generator import generate_video_comment, generate_reply_comment
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

CREDENTIALS_FILE = "secrets/client_secret.json"
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


def make_comment():
    print("Authenticating...")
    youtube = get_youtube_service()

    print("Fetching trending video...")
    video = get_trending_video(youtube)

    if not video:
        print("No trending video found.")
        return

    video_id = video["id"]
    title = video["snippet"]["title"]
    print(f"Trending Video: {title} ({video_id})")

    # Get transcript
    print("Fetching transcript...")
    try:
        transcript = get_transcript(video_id)
    except:
        transcript = "Transcript unavailable."
        print("No transcript available.")

    # Generate and post main video comment
    video_comment = generate_video_comment(transcript)
    print("Posting main comment...")
    post_comment(youtube, video_id, video_comment)

    # Fetch top comments
    print("Fetching top comments...")
    top_comments = get_top_comments(youtube, video_id)

    for c in top_comments:
        comment_id = c["id"]
        comment_text = c["snippet"]["topLevelComment"]["snippet"]["textDisplay"]

        reply = generate_reply_comment(comment_text)
        print(f"Replying to: {comment_text}")
        reply_to_comment(youtube, comment_id, reply)

    print("\nDone! Comments posted.")

if __name__ == "__main__":
    make_comment()