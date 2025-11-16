# ./utilities/tts_generator.py

import os
from pathlib import Path
from google.cloud import texttospeech

def generate_tts(text: str, output_file: Path) -> Path:
    """
    Generate TTS using Google's Chirp 3 models.
    Output format automatically determined by file extension.
    """
    client = texttospeech.TextToSpeechClient()

    # Detect MP3 or WAV from file extension
    ext = output_file.suffix.lower()
    if ext not in [".mp3", ".wav"]:
        ext = ".mp3"
        output_file = output_file.with_suffix(".mp3")

    # Select voice (https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Chirp3-HD-Achernar",
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=(
            texttospeech.AudioEncoding.MP3 if ext == ".mp3"
            else texttospeech.AudioEncoding.LINEAR16
        )
    )

    synthesis_input = texttospeech.SynthesisInput(text=text)

    print("Generating voiceover using Google Chirp 3...")

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    # Ensure output folder exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write audio file
    with open(output_file, "wb") as f:
        f.write(response.audio_content)

    print(f"TTS generated → {output_file}")
    return output_file