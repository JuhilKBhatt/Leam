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
MIN_SCORE = int(os.getenv("MIN_SCORE", "50"))
MIN_LENGTH = int(os.getenv("MIN_LENGTH", "0"))  # seconds
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