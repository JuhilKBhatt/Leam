# utilities/youtube_uploader.py

import os
import time
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_FILE = "secrets/client_secrets.json"
TOKEN_PICKLE = "secrets/youtube_token.pickle"
UPLOAD_SPEED = int(os.getenv("UPLOAD_SPEED"))  # KB/s

# Throttled File Reader
class ThrottledFile:
    """Wraps a file and limits read speed (KB/sec)."""

    def __init__(self, file_path, max_kb_sec):
        self.f = open(file_path, "rb")
        self.max_bytes_sec = max_kb_sec * 1024
        self.last_time = time.time()

    def read(self, size=-1):
        """Read with speed limiting."""
        if size == -1:
            size = 256 * 1024  # 256 KB default chunks

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

    def seek(self, *args):
        return self.f.seek(*args)

    def tell(self):
        return self.f.tell()

    def close(self):
        return self.f.close()

# YouTube Authentication
def get_youtube_service():
    creds = None

    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=8080)

        with open(TOKEN_PICKLE, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)

# Upload Function
def upload_video(file_path, title, description, tags=None, category=None,
                 privacy="private", max_speed=UPLOAD_SPEED):

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

    # Apply throttling only if requested
    if max_speed:
        print(f"→ Limiting upload speed to {max_speed} KB/s")
        throttled_file = ThrottledFile(file_path, max_speed)
        media = MediaFileUpload(
            file_path,
            chunksize=1024 * 1024,
            resumable=True
        )
        media._fd = throttled_file  # Force throttled file object
    else:
        media = MediaFileUpload(file_path, chunksize=1024 * 1024, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    print("Starting upload...")

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    print("Upload complete!")
    print("Video ID:", response.get("id"))
    print("Link: https://youtube.com/watch?v=" + response.get("id"))

# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a video to YouTube")
    parser.add_argument("file", help="Path to video file")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--desc", default="", help="Video description")
    parser.add_argument("--tags", nargs="*", help="Tags list")
    parser.add_argument("--category", help="YouTube categoryId (e.g., 24)")
    parser.add_argument("--privacy", default="public",
                        choices=["private", "unlisted", "public"])
    parser.add_argument("--max-speed", type=int,
                        help="Max upload speed in KB/s (e.g. 1024 = 1MB/s)")

    args = parser.parse_args()

    upload_video(
        args.file,
        args.title,
        args.desc,
        tags=args.tags,
        category=args.category,
        privacy=args.privacy,
        max_speed=args.max_speed
    )