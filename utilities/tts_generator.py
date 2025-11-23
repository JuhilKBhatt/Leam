# ./utilities/tts_generator.py

import os
from pathlib import Path
import pickle
from google.cloud import texttospeech
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
OAUTH_SECRETS = Path("secrets/client_secrets.json")
OAUTH_TOKEN = Path("secrets/tts_token.pickle")

def get_tts_client() -> texttospeech.TextToSpeechClient:
    """
    Returns a TTS client using OAuth credentials from client_secrets.json.
    Saves a pickle token for future use.
    """
    creds = None

    # Load saved token
    if OAUTH_TOKEN.exists():
        with open(OAUTH_TOKEN, "rb") as f:
            creds = pickle.load(f)

    # If token invalid or missing, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(OAUTH_SECRETS), SCOPES
            )
            creds = flow.run_local_server(port=8080)

        # Save token for next time
        with open(OAUTH_TOKEN, "wb") as f:
            pickle.dump(creds, f)

    return texttospeech.TextToSpeechClient(credentials=creds)


def generate_tts(text: str, output_file: Path) -> Path:
    """
    Generate TTS using Google's Chirp 3 models.
    Output format automatically determined by file extension.
    """
    client = get_tts_client()

    # Detect MP3 or WAV from file extension
    ext = output_file.suffix.lower()
    if ext not in [".mp3", ".wav"]:
        ext = ".mp3"
        output_file = output_file.with_suffix(".mp3")

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