# Leam

Create venv: python3 -m venv venv

Run venv: source venv/bin/activate

Install Requirements: pip3 install -r requirements.txt

For Reddit: python -m leam_modules.Reddit_Story_Generator.reddit_app

For YouTube Comment: python -m comment_client.commenter


uvicorn app.main:app --reload
