# ./utilities/gpt_handler.py

import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in .env")

# Initialize the new Google GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-3.7-flash"

# Basic LLM Request Helper
def gpt_request(prompt: str) -> str:
    """Send a prompt to Gemini 3.7 Flash and return the output text."""
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
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

from pydantic import BaseModel
from google.genai import types
import time

class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float

def transcribe_audio_with_timestamps(audio_path: str):
    """
    Transcribes audio and returns word-level timestamps using Gemini 3.7 Flash's multimodal capabilities.
    Returns a list of dicts: [{'word': str, 'start': float, 'end': float}]
    """
    audio_file = None
    try:
        print(f"Uploading {audio_path} to Gemini for transcription...")
        audio_file = client.files.upload(file=audio_path)
        
        prompt = "Transcribe this audio file accurately. Return an array of words with their exact start and end times in seconds."
        
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=[prompt, audio_file],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=list[WordTimestamp],
                        temperature=0.0
                    )
                )
                break
            except Exception as e:
                print(f"Gemini API attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise e
                time.sleep(2)
        
        if audio_file:
            client.files.delete(name=audio_file.name)
            
        return json.loads(response.text)
        
    except Exception as e:
        print(f"Error transcribing audio with Gemini: {e}")
        if audio_file:
            try:
                client.files.delete(name=audio_file.name)
            except:
                pass
        return []