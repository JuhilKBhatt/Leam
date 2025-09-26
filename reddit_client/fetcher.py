# reddit_client/fetcher.py

import os
import math
from dotenv import load_dotenv
import praw

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
MIN_SCORE = int(os.getenv("MIN_SCORE", "50"))
MIN_LENGTH = int(os.getenv("MIN_LENGTH", "30"))
SUBREDDITS = os.getenv("SUBREDDITS", "").split(",") if os.getenv("SUBREDDITS") else []

if not CLIENT_ID or not CLIENT_SECRET or not USER_AGENT:
    raise ValueError("❌ Missing Reddit API credentials in .env")

if not SUBREDDITS:
    raise ValueError("❌ No subreddits configured. Please add them in .env or the web form.")

# Connect to Reddit API
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)

def estimate_read_time(text: str) -> int:
    """Estimate reading time in seconds based on ~200 words/minute."""
    words = len(text.split())
    minutes = words / 200
    return math.ceil(minutes * 60)

def fetch_top_stories(limit=10):
    """Fetch top stories from all configured subreddits."""
    results = []

    for sub in SUBREDDITS:
        print(f"📥 Fetching from r/{sub}...")
        subreddit = reddit.subreddit(sub.strip())

        for post in subreddit.top(time_filter="day", limit=limit):
            if post.stickied or post.over_18:
                continue  # Skip stickied and NSFW posts

            body_text = post.selftext if post.selftext else post.title
            read_time = estimate_read_time(body_text)

            if post.score >= MIN_SCORE and read_time >= MIN_LENGTH:
                results.append({
                    "title": post.title,
                    "url": post.url,
                    "score": post.score,
                    "subreddit": sub,
                    "length": read_time,
                    "text": post.selftext[:500] + ("..." if len(post.selftext) > 500 else "")
                })

    return results

if __name__ == "__main__":
    stories = fetch_top_stories(limit=20)

    if not stories:
        print("⚠️ No stories found matching your filters.")
    else:
        print(f"✅ Found {len(stories)} stories:\n")
        for i, s in enumerate(stories, 1):
            print(f"{i}. [{s['subreddit']}] {s['title']}")
            print(f"   🏆 Score: {s['score']} | ⏱️ Length: {s['length']}s")
            print(f"   🔗 URL: {s['url']}")
            print(f"   📝 Excerpt: {s['text']}\n")