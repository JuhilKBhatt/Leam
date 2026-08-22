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

# Fallback sequence of models
FALLBACK_MODELS = [
    "gemini-3.5-flash-lite"
]

# Basic LLM Request Helper
def gpt_request(prompt: str) -> str:
    """Send a prompt to Gemini, cascading through models if 503 is encountered."""
    for model_id in FALLBACK_MODELS:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            err_msg = str(e)
            if "503" in err_msg or "UNAVAILABLE" in err_msg:
                print(f"⚠️ {model_id} returned 503. Retrying with next model...")
                continue
            else:
                print(f"Gemini request failed on {model_id}: {e}")
                return ""
    
    print("❌ All Gemini models failed.")
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
    Transcribes audio using local faster-whisper for precise word-level timestamps.
    Groups words into 3-4 word chunks for better subtitle readability.
    """
    try:
        from faster_whisper import WhisperModel
        print(f"Loading local Whisper model (tiny.en) for transcription...")
        
        # tiny.en is extremely fast and accurate enough for clear TTS audio
        model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        
        print(f"Transcribing {audio_path}...")
        segments, info = model.transcribe(audio_path, word_timestamps=True)
        
        # Flatten words
        words = []
        for segment in segments:
            for word in segment.words:
                words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end
                })
        
        if not words:
            return []
            
        # Group into 3-4 word chunks to make reading easier
        chunks = []
        current_chunk = []
        current_start = None
        
        for w in words:
            if current_start is None:
                current_start = w["start"]
            
            current_chunk.append(w["word"])
            
            # Break chunk at 3 words OR if there's heavy punctuation
            if len(current_chunk) >= 3 or w["word"].endswith((".", "?", "!", ",")):
                chunks.append({
                    "word": " ".join(current_chunk),
                    "start": current_start,
                    "end": w["end"]
                })
                current_chunk = []
                current_start = None
                
        # Append any remaining words
        if current_chunk:
            chunks.append({
                "word": " ".join(current_chunk),
                "start": current_start,
                "end": words[-1]["end"]
            })
            
        return chunks
        
    except Exception as e:
        print(f"Error transcribing audio with Whisper: {e}")
        return []