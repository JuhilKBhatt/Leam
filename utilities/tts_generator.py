# ./utilities/tts_generator.py

from gtts import gTTS
from pathlib import Path

def generate_tts(text: str, output_file: Path) -> Path:
    """Convert formatted text to speech using Google TTS."""
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(str(output_file))
    return output_file
