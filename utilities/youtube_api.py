# utilities/youtube_api.py
from googleapiclient.discovery import Resource
from youtube_transcript_api import YouTubeTranscriptApi
from utilities.comment_validator import record_comment

def get_trending_video(youtube: Resource, region="US"):
    """Returns the top trending video details."""
    req = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        regionCode=region,
        maxResults=1
    )
    res = req.execute()

    if not res["items"]:
        return None

    return res["items"][0]


def get_top_comments(youtube: Resource, video_id: str, limit=5):
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

    # Save comment history
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
    """Gets the video transcript (auto-generated allowed)."""

    transcript = YouTubeTranscriptApi.get_transcript(
        video_id, languages=["en"]
    )

    text = " ".join([entry["text"] for entry in transcript])
    return text