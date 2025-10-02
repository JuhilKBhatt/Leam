# ./utilities/tts_generator.py

import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def generate_tts(text: str, output_file: Path) -> Path:
    """
    Generate TTS audio using Groq's PlayAI model.
    Saves audio as a .wav or .mp3 file (based on output_file extension).
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Missing GROQ_API_KEY in .env")

    client = Groq(api_key=api_key)

    # Detect desired format from file extension
    ext = output_file.suffix.lower()
    if ext not in [".mp3", ".wav"]:
        ext = ".wav"
        output_file = output_file.with_suffix(".wav")

    response = client.audio.speech.create(
        model="playai-tts",
        voice="Aaliyah-PlayAI",      # Can change voice here
        response_format=ext.replace(".", ""),  # "mp3" or "wav"
        input=text
    )

    # Save to disk
    response.write_to_file(output_file)
    return output_file