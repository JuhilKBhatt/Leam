# ./utilities/gpt_handler.py

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in .env")

genai.configure(api_key=GEMINI_API_KEY)

# Use Gemini 3.7 Flash for everything
gemini_model = genai.GenerativeModel("gemini-3.7-flash")

# Basic LLM Request Helper
def gpt_request(prompt: str) -> str:
    """Send a prompt to Gemini 3.7 Flash and return the output text."""
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini request failed: {e}")
        return ""

# Format Story
def format_story_with_gpt(ai_input: str) -> str:
    """Send story text to Gemini for conversational narration formatting."""
    prompt = f"""
    {ai_input}
    """
    try:
        return gpt_request(prompt)
    except Exception as e:
        print(f"Error formatting story with Gemini: {e}")
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
        response = gpt_request(prompt)

        title = extract_between(response, "TITLE:", "DESCRIPTION:")
        description = extract_between(response, "DESCRIPTION:", "TAGS:")
        tags_line = response.split("TAGS:")[-1].strip()

        tags = [t.strip() for t in tags_line.split(",") if t.strip()]

        if not title:
            title = original_title[:80]

        if not description:
            description = f"Story from r/{subreddit}\nOriginal post: {url}"

        if not tags:
            tags = ["reddit stories", "narration", "storytime"]

        return title, description, tags

    except Exception as e:
        print("⚠️ Gemini metadata generation failed:", e)
        return (
            original_title[:80],
            f"Story from r/{subreddit}\nOriginal: {url}",
            ["reddit", "storytime", "shorts"]
        )

def transcribe_audio_with_timestamps(audio_path: str):
    """
    Transcribes audio and returns word-level timestamps using Gemini 3.7 Flash's multimodal capabilities.
    Returns a list of dicts: [{'word': str, 'start': float, 'end': float}]
    """
    try:
        print(f"Uploading {audio_path} to Gemini for transcription...")
        audio_file = genai.upload_file(path=audio_path)
        
        prompt = (
            "Transcribe this audio file accurately. "
            "Return a valid JSON array of objects. "
            "Each object must have three keys: 'word' (the exact word spoken), 'start' (float, start time in seconds), and 'end' (float, end time in seconds). "
            "Output NOTHING but the raw JSON array. Do not include markdown blocks like ```json."
        )
        
        response = gemini_model.generate_content([prompt, audio_file])
        
        # Clean up the file from Google's servers immediately
        audio_file.delete()
        
        # Parse JSON
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return data
        
    except Exception as e:
        print(f"Error transcribing audio with Gemini: {e}")
        return []