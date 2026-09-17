import os
import random
import logging
from dotenv import load_dotenv
from pathlib import Path
import time
from core.api.reddit import get_reddit_client, record_reddit_query, ensure_qpm_budget

# Load environment variables
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / "secrets" / ".env")

# Logging setup
LOG_PATH = "modules/reddit_story/logs/skipped_posts.log"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

# Connect to Reddit via core wrapper
reddit = get_reddit_client()

def try_fetch_once(MAX_RETRIES, MIN_SCORE, MIN_LENGTH, SUBREDDITS):
    """Fetch a single batch from a random subreddit. Returns None if no valid post."""
    ensure_qpm_budget("reddit_story", 1)
    subreddit_name = random.choice(SUBREDDITS)
    subreddit = reddit.subreddit(subreddit_name)

    print(f"Fetching posts from r/{subreddit_name}...")

    posts = list(subreddit.hot(limit=MAX_RETRIES))
    record_reddit_query("reddit_story", 1, reddit)

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

def fetch_story(MAX_RETRIES, MIN_SCORE, MIN_LENGTH, SUBREDDITS):
    """
    Fetch a valid text post.
    If none is found, retry across subreddits automatically.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\nAttempt {attempt}/{MAX_RETRIES}...")
        story = try_fetch_once(MAX_RETRIES, MIN_SCORE, MIN_LENGTH, SUBREDDITS)

        if story:
            return story

        print("No valid posts found. Retrying...\n")
        time.sleep(1)  # short delay to avoid hammering the API

    raise RuntimeError(
        f"❌ No valid posts found after {MAX_RETRIES} attempts. "
        f"Try lowering MIN_SCORE or MIN_LENGTH in your .env"
    )