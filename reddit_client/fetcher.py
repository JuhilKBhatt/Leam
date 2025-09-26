# reddit_client/fetcher.py
import praw
from config import REDDIT_USER_AGENT

def get_reddit_instance(client_id, client_secret):
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=REDDIT_USER_AGENT
    )

def fetch_posts(reddit, subreddits, min_score=0, min_length=50, limit=10):
    """
    Fetch posts from given subreddits with filters.
    """
    posts = []
    for sub_name in subreddits:
        subreddit = reddit.subreddit(sub_name)
        for post in subreddit.hot(limit=limit):
            if post.score >= min_score and len(post.selftext) >= min_length:
                posts.append({
                    'title': post.title,
                    'selftext': post.selftext,
                    'score': post.score,
                    'url': post.url
                })
    return posts