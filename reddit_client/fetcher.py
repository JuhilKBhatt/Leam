# reddit_client/fetcher.py

import os
import random
import logging
from dotenv import load_dotenv
import praw
import time

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
SUBREDDITS = os.getenv("SUBREDDITS", "").split(",") if os.getenv("SUBREDDITS") else []

MIN_SCORE = int(os.getenv("MIN_SCORE"))
MIN_LENGTH = int(os.getenv("MIN_LENGTH"))
MAX_RETRIES = int(os.getenv("MAX_FETCH_RETRIES"))

if not CLIENT_ID or not CLIENT_SECRET or not USER_AGENT:
    raise ValueError("Missing Reddit API credentials in .env")
if not SUBREDDITS:
    raise ValueError("No subreddits configured in .env")

# Logging setup
logging.basicConfig(
    filename="skipped_posts.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

# Connect to Reddit
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)

def try_fetch_once(limit: int = 50):
    """Fetch a single batch from a random subreddit. Returns None if no valid post."""
    subreddit_name = random.choice(SUBREDDITS)
    subreddit = reddit.subreddit(subreddit_name)

    print(f"Fetching posts from r/{subreddit_name}...")

    posts = list(subreddit.hot(limit=limit))

    valid_posts = []
    for post in posts:
        if post.stickied:
            continue
        if post.is_self and len(post.selftext) >= MIN_LENGTH and post.score >= MIN_SCORE:
            valid_posts.append(post)
        else:
            logging.info(
                f"Skipped: r/{subreddit_name} | {post.title[:60]}... | Score={post.score} | Length={len(post.selftext)}"
            )

    if not valid_posts:
        return None  # signal no valid post

    story = random.choice(valid_posts)

    print(f"Selected post: \"{story.title}\" (Score: {story.score})")

    return {
        "title": story.title,
        "body": story.selftext,
        "score": story.score,
        "url": f"https://reddit.com{story.permalink}",
        "subreddit": subreddit_name
    }

def fetch_story(limit: int = 50):
    """
    Fetch a valid text post.
    If none is found, retry across subreddits automatically.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\nAttempt {attempt}/{MAX_RETRIES}...")
        story = try_fetch_once(limit)

        if story:
            return story

        print("No valid posts found. Retrying...\n")
        time.sleep(1)  # short delay to avoid hammering the API

    raise RuntimeError(
        f"❌ No valid posts found after {MAX_RETRIES} attempts. "
        f"Try lowering MIN_SCORE or MIN_LENGTH in your .env"
    )