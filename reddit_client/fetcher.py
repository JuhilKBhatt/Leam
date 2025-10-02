# reddit_client/fetcher.py

import os
import random
import logging
from dotenv import load_dotenv
import praw

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
SUBREDDITS = os.getenv("SUBREDDITS", "").split(",") if os.getenv("SUBREDDITS") else []
MIN_SCORE = int(os.getenv("MIN_SCORE"))
MIN_LENGTH = int(os.getenv("MIN_LENGTH"))

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

def fetch_story(limit: int = 50):
    """
    Fetch a random, high-quality text post from one of the configured subreddits.
    Filters by score and length. Returns a dict with title, body, score, and URL.
    """
    subreddit_name = random.choice(SUBREDDITS)
    subreddit = reddit.subreddit(subreddit_name)

    print(f"Fetching posts from r/{subreddit_name}...")

    # Use top or hot — you can change to `.top("week")` if you want
    posts = list(subreddit.hot(limit=limit))

    # Filter out non-text or low-quality posts
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
        raise ValueError("No valid posts found. Try lowering MIN_SCORE or MIN_LENGTH.")

    # Pick a random valid post
    story = random.choice(valid_posts)

    print(f"Selected post: \"{story.title}\" (Score: {story.score})")

    return {
        "title": story.title,
        "body": story.selftext,
        "score": story.score,
        "url": f"https://reddit.com{story.permalink}",
        "subreddit": subreddit_name
    }