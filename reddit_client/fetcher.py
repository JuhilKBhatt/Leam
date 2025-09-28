# reddit_client/fetcher.py

import os
import logging
from dotenv import load_dotenv
import praw

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
SUBREDDITS = os.getenv("SUBREDDITS", "").split(",") if os.getenv("SUBREDDITS") else []

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

def fetch_random_story():
    """Fetch a random story from the configured subreddits."""
    for subreddit_name in SUBREDDITS:
        subreddit = reddit.subreddit(subreddit_name.strip())
        submissions = list(subreddit.hot(limit=50))
        if not submissions:
            logging.info(f"No submissions found in subreddit: {subreddit_name}")
            continue

        for submission in submissions:
            if submission.stickied or submission.over_18:
                logging.info(f"Skipped stickied or NSFW post: {submission.title} ({submission.id})")
                continue
            if submission.selftext and len(submission.selftext.split()) >= 100:
                return {
                    "title": submission.title,
                    "text": submission.selftext,
                    "subreddit": subreddit_name
                }
            else:
                logging.info(f"Skipped short or non-text post: {submission.title} ({submission.id})")

    logging.info("No suitable stories found in any subreddit.")
    return None