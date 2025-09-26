from flask import Flask, render_template, request, redirect, url_for
from dotenv import set_key, load_dotenv
import os

app = Flask(__name__)
ENV_FILE = ".env"

def get_env(key):
    return os.getenv(key, "")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Get form data
        reddit_client_id = request.form.get("reddit_client_id")
        reddit_client_secret = request.form.get("reddit_client_secret")
        reddit_user_agent = request.form.get("reddit_user_agent")
        min_score = request.form.get("min_score")
        min_length = request.form.get("min_length")
        subreddits = request.form.getlist("subreddit[]")

        # Update .env values
        set_key(ENV_FILE, "REDDIT_CLIENT_ID", reddit_client_id)
        set_key(ENV_FILE, "REDDIT_CLIENT_SECRET", reddit_client_secret)
        set_key(ENV_FILE, "REDDIT_USER_AGENT", reddit_user_agent)
        set_key(ENV_FILE, "MIN_SCORE", min_score)
        set_key(ENV_FILE, "MIN_LENGTH", min_length)
        set_key(ENV_FILE, "SUBREDDITS", ",".join(subreddits))

        return redirect(url_for("index"))

    # Re-load .env on every GET so new values appear
    load_dotenv(ENV_FILE, override=True)

    # Pre-fill values
    reddit_client_id = get_env("REDDIT_CLIENT_ID")
    reddit_client_secret = get_env("REDDIT_CLIENT_SECRET")
    reddit_user_agent = get_env("REDDIT_USER_AGENT")
    min_score = get_env("MIN_SCORE")
    min_length = get_env("MIN_LENGTH")
    subreddits = get_env("SUBREDDITS").split(",") if get_env("SUBREDDITS") else []

    # Mask if they exist
    masked_id = "****" if reddit_client_id else ""
    masked_secret = "****" if reddit_client_secret else ""
    masked_agent = "****" if reddit_user_agent else ""

    return render_template(
        "index.html",
        reddit_client_id=masked_id,
        reddit_client_secret_masked=masked_secret,
        reddit_user_agent_masked=masked_agent,
        min_score=min_score,
        min_length=min_length,
        subreddits=subreddits
    )

if __name__ == "__main__":
    app.run(debug=True)