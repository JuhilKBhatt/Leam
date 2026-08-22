import os
import requests
import base64
from pathlib import Path
from core.api.llm import gpt_request

LYRIA_API_KEY = os.getenv("GEMINI_API_KEY")
# Generic endpoint for Lyria API - adjust if using a different gateway
LYRIA_ENDPOINT = os.getenv("LYRIA_ENDPOINT", "https://generativelanguage.googleapis.com/v1beta/models/lyria-3-pro-preview:predict")

def generate_music_prompt(script: str, video_type: str) -> str:
    """
    Uses an LLM to generate a highly engaging, retention-optimized 
    music prompt for Google Lyria 3 Pro based on the script and video type.
    """
    prompt = f"""
You are an expert audio director and psychologist specializing in viewer retention for short-form video content.
Your task is to write a highly detailed music generation prompt for Google Lyria 3 Pro.

Video Type: {video_type}

Script:
{script}

Requirements for the music prompt:
1. Specify genre, instruments, and tempo.
2. Design the music to maintain viewer retention (e.g., start with a strong hook, build tension in the middle, and have a satisfying or looping end).
3. Ensure the tone matches the emotion of the script perfectly.
4. Keep the prompt strictly under 200 words.
5. Output ONLY the prompt itself, nothing else.
"""
    
    response = gpt_request(prompt)
    if not response:
        # Fallback generic prompt
        return f"Engaging background music for a {video_type} video, starting with a strong hook and building tension."
    
    return response.strip()

def generate_music_lyria(script: str, video_type: str, duration_sec: int, output_path: str | Path) -> str:
    """
    Generates music using Google Lyria 3 Pro based on the script and video type,
    and saves it to the output_path.
    
    Returns the path to the generated music file.
    """
    if not LYRIA_API_KEY:
        print("⚠️ LYRIA_API_KEY is missing from environment variables. Skipping music generation.")
        return ""
        
    print(f"🎵 Generating Lyria music prompt for {video_type} video...")
    music_prompt = generate_music_prompt(script, video_type)
    print(f"🎵 Music Prompt: {music_prompt}")
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": LYRIA_API_KEY
    }
    
    print(f"🎵 Requesting music generation from Lyria 3 Pro (Duration: {min(int(duration_sec), 60)}s)...")
    
    # Standard Gemini endpoint
    LYRIA_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/lyria-3-pro-preview:generateContent"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"Generate exactly {min(int(duration_sec), 60)} seconds of music: {music_prompt}"}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(LYRIA_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            audio_b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            audio_bytes = base64.b64decode(audio_b64)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            print(f"🎵 Music saved to {output_path}")
            return str(output_path)
        except (KeyError, IndexError):
            print("⚠️ Lyria API response did not contain expected audio data.")
            print("Response preview:", str(data)[:500])
            return ""
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to generate music with Lyria: {e}")
        if e.response is not None:
            print("API Response:", e.response.text[:500])
        return ""
