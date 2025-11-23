# ./utilities/gpt_handler.py

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

# Basic GPT Request Helper
def gpt_request(prompt: str, model: str = "openai/gpt-oss-120b") -> str:
    """Send a prompt to GPT and return the output text."""
    try:
        response = client.responses.create(
            input=[{"role": "user", "content": prompt}],
            model=model,
        )
        return response.output_text
    except Exception as e:
        print(f"GPT request failed: {e}")
        return ""

# Format Story with GPT
def format_story_with_gpt(ai_input: str) -> str:
    """Send story text to GPT for conversational narration formatting."""
    prompt = f"""
    {ai_input}
    """
    try:
        return gpt_request(prompt)
    except Exception as e:
        print(f"Error formatting story with GPT: {e}")
        return ""

def extract_between(text: str, start_key: str, end_key: str) -> str:
    try:
        start = text.index(start_key) + len(start_key)
        end = text.index(end_key)
        return text[start:end].strip()
    except ValueError:
        return ""

def generate_youtube_metadata(original_title: str, story_text: str,
                              subreddit: str, url: str):
    """
    Produces SEO-friendly:
    - YouTube title
    - Description
    - Tags list
    """

    prompt = f"""
You are generating metadata for a YouTube video narrated from a Reddit story.

Original Reddit Title:
{original_title}

Subreddit: r/{subreddit}
Post URL: {url}

Story:
{story_text}

Respond in the EXACT format:

TITLE:
<Your YouTube title>

DESCRIPTION:
<2-3 paragraph YouTube description>

TAGS:
<tag1, tag2, tag3, ... up to 12 tags>
"""

    try:
        response = gpt_request(prompt, model="llama-3.1-70b-versatile")

        title = extract_between(response, "TITLE:", "DESCRIPTION:")
        description = extract_between(response, "DESCRIPTION:", "TAGS:")
        tags_line = response.split("TAGS:")[-1].strip()

        tags = [t.strip() for t in tags_line.split(",") if t.strip()]

        # Ensure safe defaults
        if not title:
            title = original_title[:80]

        if not description:
            description = f"Story from r/{subreddit}\nOriginal post: {url}"

        if not tags:
            tags = ["reddit stories", "narration", "storytime"]

        return title, description, tags

    except Exception as e:
        print("⚠️ GPT metadata generation failed:", e)
        return (
            original_title[:80],
            f"Story from r/{subreddit}\nOriginal: {url}",
            ["reddit", "storytime", "shorts"]
        )