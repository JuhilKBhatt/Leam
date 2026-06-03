import os
import time
import argparse
import pickle
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from youtube_transcript_api import YouTubeTranscriptApi
from core.utils.comment_validator import record_comment

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
CREDENTIALS_FILE = "secrets/client_secrets.json"
TOKEN_PICKLE = "secrets/youtube_token.pickle"

def get_youtube_service():
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Refreshing expired access token...")
                creds.refresh(Request())
            except RefreshError:
                print("❌ Token refresh failed (invalid grant). Deleting old token and re-authenticating.")
                os.remove(TOKEN_PICKLE)
                creds = None

        if not creds:
            print("🔐 Launching browser for YouTube authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=8080)

        with open(TOKEN_PICKLE, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)

def get_trending_video(youtube: Resource, chart: str = "mostPopular", region: str = "US", max_results: int = 10):
    """Returns the top trending video details."""
    req = youtube.videos().list(
        part="snippet,statistics",
        chart=chart,
        regionCode=region,
        maxResults=max_results
    )
    res = req.execute()
    return res.get("items", [])

def get_top_comments(youtube: Resource, video_id: str, limit: int = 5):
    """Returns top-level comments for a given video."""
    req = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        textFormat="plainText",
        maxResults=limit,
        order="relevance",
    )
    res = req.execute()
    return res.get("items", [])

def post_comment(youtube: Resource, video_id: str, text: str):
    """Posts a comment on the video."""
    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {"snippet": {"textOriginal": text}},
        }
    }
    res = youtube.commentThreads().insert(
        part="snippet",
        body=body
    ).execute()

    comment_id = res["id"]
    record_comment(video_id, comment_id)
    return res

def reply_to_comment(youtube: Resource, parent_id: str, text: str):
    """Replies to a comment."""
    body = {
        "snippet": {
            "parentId": parent_id,
            "textOriginal": text
        }
    }
    return youtube.comments().insert(
        part="snippet",
        body=body
    ).execute()

def get_transcript(video_id: str) -> str:
    """Gets the video transcript."""
    transcript = YouTubeTranscriptApi().fetch(video_id)
    text = " ".join([entry.text for entry in transcript])
    return text

class ThrottledFile:
    """Wraps a file and limits read speed (KB/sec)."""
    def __init__(self, file_path, max_kb_sec):
        self.f = open(file_path, "rb")
        self.max_bytes_sec = max_kb_sec * 1024
        self.last_time = time.time()

    def read(self, size=-1):
        if size == -1:
            size = 256 * 1024
        start_time = time.time()
        data = self.f.read(size)
        end_time = time.time()
        elapsed = end_time - self.last_time
        if elapsed > 0:
            rate = len(data) / elapsed
            if rate > self.max_bytes_sec:
                sleep_for = (len(data) / self.max_bytes_sec) - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)
        self.last_time = time.time()
        return data

    def seek(self, *args): return self.f.seek(*args)
    def tell(self): return self.f.tell()
    def close(self): return self.f.close()

def upload_video(file_path, title, description, tags=None, category=None, privacy="private", max_speed=None):
    youtube = get_youtube_service()
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
        },
        "status": {"privacyStatus": privacy},
    }
    if category:
        body["snippet"]["categoryId"] = str(category)

    if max_speed:
        print(f"→ Limiting upload speed to {max_speed} KB/s")
        throttled_file = ThrottledFile(file_path, max_speed)
        media = MediaFileUpload(file_path, chunksize=1024 * 1024, resumable=True)
        media._fd = throttled_file
    else:
        media = MediaFileUpload(file_path, chunksize=1024 * 1024, resumable=True)

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    print("Starting upload...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
    print("Upload complete! ID:", response.get("id"))
    return response.get("id")
