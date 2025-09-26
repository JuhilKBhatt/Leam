# ./config.py
from dotenv import load_dotenv
import os

load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "")
MIN_SCORE = os.getenv("MIN_SCORE", "")
MIN_LENGTH = os.getenv("MIN_LENGTH", "")
SUBREDDITS = os.getenv("SUBREDDITS", "").split(",") if os.getenv("SUBREDDITS") else []